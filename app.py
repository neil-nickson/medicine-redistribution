from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

from ml_models.model_runner import ml_models
from config import Config
from database import get_db, close_db, init_db

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()

@app.after_request
def add_cache_control(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

# ================= AUTH =================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated

# ================= PINCODE DISTANCE =================
import urllib.request
import json
import math

PINCODE_CACHE = {}

def get_coordinates(pincode):
    if pincode in PINCODE_CACHE:
        return PINCODE_CACHE[pincode]
        
    url = f"https://nominatim.openstreetmap.org/search?postalcode={pincode}&country=india&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'PharmaLoop/1.0 (local_dev)'})
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        if data and len(data) > 0:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            PINCODE_CACHE[pincode] = coords
            return coords
    except Exception as e:
        print(f"Distance API Error for {pincode}: {e}")
        
    return None, None

def calculate_distance(pin1, pin2):
    try:
        lat1, lon1 = get_coordinates(pin1)
        lat2, lon2 = get_coordinates(pin2)
        
        if lat1 is None or lat2 is None:
            # Fallback naive math
            return round(abs(int(pin1) - int(pin2)) / 10.0, 1)

        # Haversine formula
        R = 6371.0 # Earth radius in km
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 1)
    except:
        return 50.0

# ================= HTML ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/redistribution-view')
def redistribution_view():
    return render_template('redistribution.html')

# ================= REGISTER =================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    db = get_db()
    cursor = db.cursor()

    hashed_password = generate_password_hash(data['password'])

    cursor.execute("""
    INSERT INTO users (
        email, password, name,
        organization_type, organization_name,
        location, pincode, phone
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['email'],
        hashed_password,
        data['name'],
        data['organization_type'],
        data['organization_name'],
        data['location'],
        data['pincode'],
        data.get('phone', '')
    ))

    db.commit()
    return jsonify({'message': 'Registration successful'}), 201

# ================= LOGIN =================

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (data['email'],)
    ).fetchone()

    if user and check_password_hash(user['password'], data['password']):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'token': token, 'user': dict(user)})

    return jsonify({'error': 'Invalid credentials'}), 401

# ================= MEDICINES =================

@app.route('/api/medicines', methods=['POST'])
@token_required
def add_medicine(current_user_id):
    data = request.json
    db = get_db()
    cursor = db.cursor()

    user = db.execute("SELECT location FROM users WHERE id=?",
                      (current_user_id,)).fetchone()

    cursor.execute("""
    INSERT INTO medicines (
        user_id, medicine_name, batch_number, current_stock,
        avg_monthly_usage, days_to_expiry, expiry_date,
        hospital_type, location, price_per_unit
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        current_user_id,
        data['medicine_name'],
        data['batch_number'],
        data['current_stock'],
        data['avg_monthly_usage'],
        data['days_to_expiry'],
        data['expiry_date'],
        data.get('hospital_type', 0),
        user['location'],
        data.get('price_per_unit', 100)
    ))

    db.commit()
    med_id = cursor.lastrowid
    run_surplus_prediction_single(med_id)

    return jsonify({'message': 'Medicine added'}), 201

@app.route('/api/medicines', methods=['GET'])
@token_required
def get_medicines(current_user_id):
    db = get_db()

    meds = db.execute("""
    SELECT *
    FROM medicines
    WHERE user_id=?
    ORDER BY id DESC
    """, (current_user_id,)).fetchall()

    return jsonify([dict(m) for m in meds])


# ================= DEMAND =================

@app.route('/api/demand', methods=['POST'])
@token_required
def add_demand(current_user_id):
    data = request.json
    db = get_db()
    cursor = db.cursor()

    # ---------- Validate input ----------
    if not data.get('medicine_name') or not data.get('past_month_usage'):
        return jsonify({'error': 'Missing required fields'}), 400

    # ---------- Get user pincode ----------
    user = db.execute(
        "SELECT pincode FROM users WHERE id=?",
        (current_user_id,)
    ).fetchone()

    if not user or not user['pincode']:
        return jsonify({'error': 'User pincode not found'}), 400

    # ---------- Map urgency ----------
    urgency_map = {
        "low": 0,
        "medium": 1,
        "high": 2
    }

    urgency_level = urgency_map.get(
        data.get("urgency_level", "medium"),
        1
    )

    # ---------- Insert demand ----------
    cursor.execute("""
    INSERT INTO demand_records (
        user_id,
        medicine_name,
        past_month_usage,
        clinic_population,
        disease_index,
        season,
        urgency_level,
        pincode,
        predicted_demand
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        current_user_id,
        data['medicine_name'].strip(),
        int(data['past_month_usage']),
        1500,        # default population
        0.5,         # default disease index
        0,           # default season
        urgency_level,
        user['pincode'],
        0            # will be predicted by ML later
    ))

    db.commit()

    return jsonify({
        'message': 'Demand added successfully',
        'clinic_population': 1500
    }), 201




# ================= REDISTRIBUTION =================

@app.route('/api/redistribution-matches', methods=['GET'])
@token_required
def get_redistribution_matches(current_user_id):
    db = get_db()
    cursor = db.cursor()

    matches = cursor.execute("""
    SELECT rm.*, 
           u_donor.name as donor_name, u_donor.location as donor_location,
           u_recv.name as receiver_name, u_recv.location as receiver_location
    FROM redistribution_matches rm
    JOIN users u_donor ON rm.donor_id = u_donor.id
    JOIN users u_recv ON rm.receiver_id = u_recv.id
    WHERE rm.donor_id = ? OR rm.receiver_id = ?
    ORDER BY rm.created_at DESC
    """, (current_user_id, current_user_id)).fetchall()

    return jsonify([dict(m) for m in matches])


@app.route('/api/accept-offer', methods=['POST'])
@token_required
def accept_offer(current_user_id):
    data = request.json
    match_id = data.get('match_id')

    if not match_id:
        return jsonify({'error': 'Match ID required'}), 400

    db = get_db()
    cursor = db.cursor()

    match = cursor.execute("""
    SELECT rm.*, 
           u_donor.name as donor_name, u_donor.email as donor_email,
           u_recv.name as receiver_name, u_recv.location as receiver_location
    FROM redistribution_matches rm
    JOIN users u_donor ON rm.donor_id = u_donor.id
    JOIN users u_recv ON rm.receiver_id = u_recv.id
    WHERE rm.id = ?
    """, (match_id,)).fetchone()

    if not match:
        return jsonify({'error': 'Redistribution match not found'}), 404

    # Update match status to REQUESTED
    cursor.execute("""
    UPDATE redistribution_matches
    SET status = 'REQUESTED'
    WHERE id = ?
    """, (match_id,))

    # Insert pending transaction
    cursor.execute("""
    INSERT INTO transactions (
        match_id, donor_id, receiver_id,
        medicine_name, quantity, original_value,
        discount_applied, final_amount, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'REQUESTED')
    """, (
        match_id,
        match['donor_id'],
        match['receiver_id'],
        match['medicine_name'],
        match['quantity'],
        match['original_price'],
        match['discount_percent'],
        match['discounted_price']
    ))

    # Send Notification to Medicine Owner (Donor)
    notification_title = "🔔 New Redistribution Request!"
    notification_msg = f"'{match['receiver_name']}' ({match['receiver_location']}) has requested {match['quantity']} units of {match['medicine_name']}!"

    cursor.execute("""
    INSERT INTO notifications (user_id, match_id, sender_name, title, message)
    VALUES (?, ?, ?, ?, ?)
    """, (
        match['donor_id'],
        match_id,
        match['receiver_name'],
        notification_title,
        notification_msg
    ))

    db.commit()

    return jsonify({
        'message': f"Request sent to owner ({match['donor_name']})! They have been notified.",
        'status': 'REQUESTED'
    })

@app.route('/api/complete-transaction', methods=['POST'])
@token_required
def complete_transaction(current_user_id):
    data = request.json
    match_id = data.get('match_id')

    if not match_id:
        return jsonify({'error': 'Match ID required'}), 400

    db = get_db()
    cursor = db.cursor()

    # Get the match to ensure current_user_id is the donor
    match = cursor.execute("""
    SELECT rm.*, 
           u_donor.name as donor_name,
           u_recv.name as receiver_name
    FROM redistribution_matches rm
    JOIN users u_donor ON rm.donor_id = u_donor.id
    JOIN users u_recv ON rm.receiver_id = u_recv.id
    WHERE rm.id = ?
    """, (match_id,)).fetchone()

    if not match:
        return jsonify({'error': 'Redistribution match not found'}), 404

    if match['donor_id'] != current_user_id:
        return jsonify({'error': 'Only the donor can complete the transaction'}), 403
        
    if match['status'] != 'REQUESTED':
        return jsonify({'error': 'Match is not in REQUESTED status'}), 400

    # Update match status to COMPLETED
    cursor.execute("""
    UPDATE redistribution_matches
    SET status = 'COMPLETED'
    WHERE id = ?
    """, (match_id,))

    # Update transaction status
    cursor.execute("""
    UPDATE transactions
    SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
    WHERE match_id = ?
    """, (match_id,))
    
    # Deduct stock from donor's medicine
    cursor.execute("""
    UPDATE medicines
    SET current_stock = current_stock - ?
    WHERE id = ?
    """, (match['quantity'], match['medicine_id']))

    # Send Notification to Receiver
    notification_title = "✅ Request Approved!"
    notification_msg = f"'{match['donor_name']}' has approved your request for {match['quantity']} units of {match['medicine_name']}!"

    cursor.execute("""
    INSERT INTO notifications (user_id, match_id, sender_name, title, message)
    VALUES (?, ?, ?, ?, ?)
    """, (
        match['receiver_id'],
        match_id,
        match['donor_name'],
        notification_title,
        notification_msg
    ))

    db.commit()

    return jsonify({
        'message': f"Transaction completed! {match['quantity']} units deducted from inventory.",
        'status': 'COMPLETED'
    })
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    db = get_db()
    cursor = db.cursor()

    notifications = cursor.execute("""
    SELECT * FROM notifications
    WHERE user_id = ?
    ORDER BY created_at DESC
    """, (current_user_id,)).fetchall()

    return jsonify([dict(n) for n in notifications])


@app.route('/api/run-redistribution', methods=['POST'])
@token_required
def run_redistribution(current_user_id):
    db = get_db()
    cursor = db.cursor()

    # Clear old pending matches for the current user's demands
    cursor.execute("DELETE FROM redistribution_matches WHERE status='PENDING' AND receiver_id=?", (current_user_id,))

    # Run ML surplus prediction on all medicine stock
    all_meds = db.execute("SELECT id FROM medicines").fetchall()
    for med in all_meds:
        run_surplus_prediction_single(med['id'])

    # Predict demand for demand records
    all_demands = db.execute("SELECT * FROM demand_records").fetchall()
    for d in all_demands:
        if not d['predicted_demand'] or d['predicted_demand'] == 0:
            df = pd.DataFrame([{
                'past_month_usage': d['past_month_usage'],
                'clinic_population': d['clinic_population'],
                'disease_index': d['disease_index'],
                'season': d['season']
            }])
            pred = ml_models.predict_demand(df)[0]
            cursor.execute("UPDATE demand_records SET predicted_demand=? WHERE id=?", (float(pred), d['id']))
    db.commit()

    surplus = db.execute("""
    SELECT m.*, u.pincode as donor_pincode, u.id as donor_id
    FROM medicines m
    JOIN users u ON m.user_id=u.id
    WHERE m.status='REDISTRIBUTE'
    """).fetchall()

    demands = db.execute("""
    SELECT d.*, u.pincode as receiver_pincode, u.id as receiver_id
    FROM demand_records d
    JOIN users u ON d.user_id=u.id
    WHERE d.user_id = ?
    """, (current_user_id,)).fetchall()

    matches = 0

    for med in surplus:
        for demand in demands:

            if med['donor_id'] == demand['receiver_id']:
                continue

            med_name_clean = med['medicine_name'].replace('_', ' ').split()[0].lower()
            demand_name_clean = demand['medicine_name'].replace('_', ' ').split()[0].lower()

            if med_name_clean != demand_name_clean:
                continue

            distance = calculate_distance(
                med['donor_pincode'],
                demand['receiver_pincode']
            )

            score, decision = ml_models.calculate_redistribution_score(
                med['surplus_probability'],
                demand['predicted_demand'],
                med['days_to_expiry'],
                distance
            )

            if decision != "SEND":
                continue

            quantity = min(int(med['current_stock']), int(demand['predicted_demand'] or 50))
            if quantity <= 0:
                quantity = 10

            discount_pct = ml_models.calculate_discount(
                med['days_to_expiry'],
                med['surplus_probability'],
                distance
            )

            profitability = ml_models.calculate_profitability(
                quantity,
                med['price_per_unit'] or 100.0,
                discount_pct,
                distance,
                med['days_to_expiry']
            )

            cursor.execute("""
            INSERT INTO redistribution_matches (
                medicine_id, demand_id, donor_id, receiver_id,
                medicine_name, quantity, surplus_probability, predicted_demand,
                days_to_expiry, distance_km, redistribution_score, decision,
                discount_percent, original_price, discounted_price, transfer_cost, net_profit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                med['id'],
                demand['id'],
                med['donor_id'],
                demand['receiver_id'],
                med['medicine_name'],
                quantity,
                float(med['surplus_probability']),
                float(demand['predicted_demand']),
                med['days_to_expiry'],
                distance,
                score,
                "SEND",
                profitability['discount_percent'],
                profitability['original_value'],
                profitability['discounted_value'],
                profitability['transfer_cost'],
                profitability['net_profit']
            ))

            matches += 1

    db.commit()
    return jsonify({
        'message': 'AI Redistribution matching completed successfully.',
        'matches_found': matches
    })

# ================= ML FUNCTIONS =================

def run_surplus_prediction_single(med_id):
    db = get_db()
    med = db.execute("SELECT * FROM medicines WHERE id=?",
                     (med_id,)).fetchone()

    df = pd.DataFrame([{
        "current_stock": med['current_stock'],
        "avg_monthly_usage": med['avg_monthly_usage'],
        "days_to_expiry": med['days_to_expiry'],
        "hospital_type": med['hospital_type']
    }])

    prob = ml_models.predict_surplus(df)[0]
    # Lowered threshold from 0.6 to 0.45 so more mock medicines get matched
    status = "REDISTRIBUTE" if prob >= 0.45 else "SAFE"

    db.execute("""
    UPDATE medicines
    SET surplus_probability=?, status=?
    WHERE id=?
    """, (float(prob), status, med_id))

    db.commit()

# ================= RUN =================

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False, port=5001)
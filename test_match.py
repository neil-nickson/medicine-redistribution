import sqlite3
from app import ml_models, calculate_distance
db = sqlite3.connect('pharmaloop.db')
db.row_factory = sqlite3.Row

surplus = db.execute("SELECT m.*, u.pincode as donor_pincode, u.id as donor_id FROM medicines m JOIN users u ON m.user_id=u.id WHERE m.status='REDISTRIBUTE'").fetchall()
demands = db.execute("SELECT d.*, u.pincode as receiver_pincode, u.id as receiver_id FROM demand_records d JOIN users u ON d.user_id=u.id").fetchall()

for med in surplus:
    for demand in demands:
        if med['donor_id'] == demand['receiver_id']: continue
        med_name_clean = med['medicine_name'].replace('_', ' ').split()[0].lower()
        demand_name_clean = demand['medicine_name'].replace('_', ' ').split()[0].lower()
        if med_name_clean != demand_name_clean: continue
        
        distance = calculate_distance(med['donor_pincode'], demand['receiver_pincode'])
        score, decision = ml_models.calculate_redistribution_score(
            med['surplus_probability'] or 0.6,
            demand['predicted_demand'] or 50,
            med['days_to_expiry'] or 30,
            distance
        )
        print(f"Match: {med['medicine_name']}, Score: {score}, Decision: {decision}, Dist: {distance}, SurplusProb: {med['surplus_probability']}, Demand: {demand['predicted_demand']}")

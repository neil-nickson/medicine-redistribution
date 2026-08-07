import os
import sqlite3
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import init_db
from config import Config

# Delete existing database
if os.path.exists(Config.DATABASE):
    os.remove(Config.DATABASE)
    print("Deleted old database.")

# Initialize new database
init_db()

db = sqlite3.connect(Config.DATABASE)
cursor = db.cursor()

# 1. Create 5 Users
users_data = [
    ("City Hospital", "Hospital", "contact@cityhospital.com", "password123", "Central Bangalore", "560001", "9876543210"),
    ("Care Pharmacy", "Pharmacy", "info@carepharmacy.com", "password123", "Indiranagar", "560038", "9876543211"),
    ("Health Plus Clinic", "Clinic", "hello@healthplus.com", "password123", "Koramangala", "560034", "9876543212"),
    ("Metro Medicals", "Medical Shop", "sales@metromedicals.com", "password123", "Jayanagar", "560011", "9876543213"),
    ("Lifeline Hospital", "Hospital", "admin@lifeline.com", "password123", "Whitefield", "560066", "9876543214")
]

user_ids = []
for name, org_type, email, pwd, loc, pin, phone in users_data:
    hashed_pwd = generate_password_hash(pwd)
    cursor.execute("""
    INSERT INTO users (email, password, name, organization_type, organization_name, location, pincode, phone)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (email, hashed_pwd, name, org_type, name, loc, pin, phone))
    user_ids.append(cursor.lastrowid)

print(f"Created {len(user_ids)} users.")

# 2. Create 25 Medicines (Distribute among users)
medicine_names = [
    "Paracetamol 500mg", "Amoxicillin 250mg", "Ibuprofen 400mg", "Omeprazole 20mg", 
    "Metformin 500mg", "Atorvastatin 10mg", "Amlodipine 5mg", "Losartan 50mg", 
    "Azithromycin 500mg", "Pantoprazole 40mg", "Cetirizine 10mg", "Levothyroxine 50mcg",
    "Vitamin D3 60K", "Aspirin 75mg", "Clopidogrel 75mg", "Rosuvastatin 10mg",
    "Ciprofloxacin 500mg", "Dolo 650mg", "Montelukast 10mg", "Telmisartan 40mg",
    "Gliclazide 80mg", "Cefixime 200mg", "Dexamethasone 0.5mg", "Fluconazole 150mg", "Ondansetron 4mg"
]

for i in range(25):
    user_id = random.choice(user_ids)
    med_name = medicine_names[i]
    batch = f"B{random.randint(1000, 9999)}"
    stock = random.randint(50, 1000)
    usage = random.randint(10, 500)
    
    # Mix of urgent expiry and safe expiry
    if random.random() < 0.3:
        days_to_expiry = random.randint(5, 45) # Urgent
    else:
        days_to_expiry = random.randint(90, 365) # Safe
        
    expiry_date = (datetime.now() + timedelta(days=days_to_expiry)).strftime("%Y-%m-%d")
    price = round(random.uniform(5.0, 150.0), 2)
    
    # Calculate mock surplus probability
    surplus_prob = min(0.99, max(0.01, (stock - usage) / max(stock, 1) if stock > usage else 0.1))
    
    status = "SAFE"
    if days_to_expiry < 30 and stock > usage:
        status = "CRITICAL"
    elif days_to_expiry < 90 and stock > (usage * 2):
        status = "REDISTRIBUTE"
        
    cursor.execute("""
    INSERT INTO medicines (user_id, medicine_name, batch_number, current_stock, avg_monthly_usage, 
                          days_to_expiry, expiry_date, surplus_probability, status, location, price_per_unit)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, med_name, batch, stock, usage, days_to_expiry, expiry_date, surplus_prob, status, users_data[user_id-1][4], price))

print("Created 25 medicines.")

# 3. Create some demand records for different users so matches can be found
for i in range(10):
    user_id = random.choice(user_ids)
    # Pick a medicine that hopefully belongs to someone else
    med_name = random.choice(medicine_names)
    past_usage = random.randint(50, 300)
    urgency = random.choice([0, 1, 2])
    pin = users_data[user_id-1][5]
    
    cursor.execute("""
    INSERT INTO demand_records (user_id, medicine_name, past_month_usage, urgency_level, pincode, predicted_demand)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, med_name, past_usage, urgency, pin, past_usage * 1.1))

print("Created 10 demand records.")

db.commit()
db.close()
print("Database seeded successfully!")

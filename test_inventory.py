import requests
import json

base_url = "http://127.0.0.1:5001/api"

# 1. Register User A
requests.post(f"{base_url}/register", json={
    "email": "userA@test.com", "password": "password", "name": "User A", 
    "organization_type": "Hospital", "organization_name": "Org A", 
    "location": "Loc A", "pincode": "111111"
})

# 2. Login User A
resp = requests.post(f"{base_url}/login", json={"email": "userA@test.com", "password": "password"})
token_A = resp.json()['token']

# 3. Add Medicine as User A
requests.post(f"{base_url}/medicines", headers={"Authorization": f"Bearer {token_A}"}, json={
    "medicine_name": "dolo", "batch_number": "b1", "current_stock": 100, 
    "avg_monthly_usage": 10, "days_to_expiry": 30, "expiry_date": "2024-01-01", 
    "price_per_unit": 10
})

# 4. Get Medicines for User A
resp = requests.get(f"{base_url}/medicines", headers={"Authorization": f"Bearer {token_A}"})
print("User A Medicines:", len(resp.json()), resp.json())

# 5. Register User B
requests.post(f"{base_url}/register", json={
    "email": "userB@test.com", "password": "password", "name": "User B", 
    "organization_type": "Hospital", "organization_name": "Org B", 
    "location": "Loc B", "pincode": "222222"
})

# 6. Login User B
resp = requests.post(f"{base_url}/login", json={"email": "userB@test.com", "password": "password"})
token_B = resp.json()['token']

# 7. Get Medicines for User B
resp = requests.get(f"{base_url}/medicines", headers={"Authorization": f"Bearer {token_B}"})
print("User B Medicines:", len(resp.json()), resp.json())


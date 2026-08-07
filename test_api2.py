import sqlite3
from app import app
import json

db = sqlite3.connect('pharmaloop.db')
cursor = db.cursor()
cursor.execute("SELECT id FROM users LIMIT 1")
user_id = cursor.fetchone()[0]
db.close()

with app.test_client() as c:
    token_resp = c.post('/api/login', json={'email': 'srh@gmail.com', 'password': 'password123'})
    token = token_resp.get_json()['token']
    
    resp = c.post('/api/run-redistribution', headers={'Authorization': f'Bearer {token}'})
    print("API RESPONSE:", resp.get_json())

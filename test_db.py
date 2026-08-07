import sqlite3
db = sqlite3.connect('pharmaloop.db')
db.row_factory = sqlite3.Row
cursor = db.cursor()
match_id = 26
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
    print("Match not found")
else:
    print("Match found:", dict(match))

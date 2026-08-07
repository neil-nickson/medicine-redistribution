curl -s -X POST http://127.0.0.1:5001/api/register -H "Content-Type: application/json" -d '{"email":"ua@t.com","password":"p","name":"A","organization_type":"H","organization_name":"O","location":"L","pincode":"111111"}'
echo ""
TOKEN_A=$(curl -s -X POST http://127.0.0.1:5001/api/login -H "Content-Type: application/json" -d '{"email":"ua@t.com","password":"p"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4)
curl -s -X POST http://127.0.0.1:5001/api/medicines -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN_A" -d '{"medicine_name":"dolo","batch_number":"b1","current_stock":100,"avg_monthly_usage":10,"days_to_expiry":30,"expiry_date":"2024-01-01","price_per_unit":10}'
echo ""
echo "User A meds:"
curl -s -X GET http://127.0.0.1:5001/api/medicines -H "Authorization: Bearer $TOKEN_A"
echo ""

curl -s -X POST http://127.0.0.1:5001/api/register -H "Content-Type: application/json" -d '{"email":"ub@t.com","password":"p","name":"B","organization_type":"H","organization_name":"O","location":"L","pincode":"222222"}'
echo ""
TOKEN_B=$(curl -s -X POST http://127.0.0.1:5001/api/login -H "Content-Type: application/json" -d '{"email":"ub@t.com","password":"p"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4)
echo "User B meds:"
curl -s -X GET http://127.0.0.1:5001/api/medicines -H "Authorization: Bearer $TOKEN_B"
echo ""

TOKEN=$(curl -s -X POST http://127.0.0.1:5001/api/login -H "Content-Type: application/json" -d '{"email":"srh@gmail.com","password":"password123"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4)
echo "TOKEN: $TOKEN"
curl -s -X POST http://127.0.0.1:5001/api/run-redistribution -H "Authorization: Bearer $TOKEN"

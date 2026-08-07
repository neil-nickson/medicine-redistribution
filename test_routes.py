import urllib.request

req = urllib.request.Request('http://127.0.0.1:5001/api/redistribution-matches')
try:
    print("Testing /api/redistribution-matches")
    urllib.request.urlopen(req)
except Exception as e:
    print(e.code)

req2 = urllib.request.Request('http://127.0.0.1:5001/api/accept-offer', method='POST')
try:
    print("Testing /api/accept-offer")
    urllib.request.urlopen(req2, data=b'{"match_id": 26}')
except Exception as e:
    print(e.code)
    print(e.read())

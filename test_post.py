import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('http://127.0.0.1:5001/api/accept-offer', method='POST')
req.add_header('Content-Type', 'application/json')
# We need a valid token to bypass @token_required. But let's see if we get a 401 or 404.
try:
    urllib.request.urlopen(req, data=b'{"match_id": 26}')
except Exception as e:
    print(e.code)
    print(e.read())

import urllib.request
import json
import math
import time

def get_coordinates(pincode):
    url = f"https://nominatim.openstreetmap.org/search?postalcode={pincode}&country=india&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'PharmaLoop/1.0 (test)'})
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Error fetching {pincode}: {e}")
    
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

print("Testing Nominatim API...")
lat1, lon1 = get_coordinates(600019)
print(f"600019 (Chennai): Lat {lat1}, Lon {lon1}")

time.sleep(1) # Be nice to the API

lat2, lon2 = get_coordinates(604303)
print(f"604303 (Tindivanam area): Lat {lat2}, Lon {lon2}")

if lat1 and lat2:
    dist = haversine(lat1, lon1, lat2, lon2)
    print(f"Distance: {dist:.2f} km")

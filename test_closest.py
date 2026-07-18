import json
import math
import urllib.request

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

gtfs = json.loads(urllib.request.urlopen("http://mindmetroapi.midhunapi.me/gtfs-data").read())
stations = gtfs["stations"]

userLat = 10.0717594
userLon = 76.3640662

closest = None
minDist = float('inf')

for name, data in stations.items():
    dist = haversine(userLat, userLon, data["lat"], data["lon"])
    if dist < minDist:
        minDist = dist
        closest = name

print("Closest station:", closest)

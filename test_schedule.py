import json
with open('/home/midhun/Coading/MindMetro/kmrl.json') as f:
    gtfs = json.load(f)
schedule = gtfs['schedule']
for station_id, times in list(schedule.items())[:1]:
    print(f"Station {station_id}: {len(times)} trains")
    print(f"First train: {times[0]}")
    print(f"Last train: {times[-1]}")

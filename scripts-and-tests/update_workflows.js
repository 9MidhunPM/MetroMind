const fs = require('fs');

const file = '/home/midhun/Coading/MindMetro/mindmetro_workflows.json';
let data = JSON.parse(fs.readFileSync(file, 'utf8'));

const processQueryCode = `const inputJson = $input.item ? $input.item.json : $json;

// ORIGIN INPUT
let originLat = null;
let originLon = null;

if (inputJson.latitude !== undefined && inputJson.latitude !== null && 
    inputJson.longitude !== undefined && inputJson.longitude !== null) {
  originLat = parseFloat(inputJson.latitude);
  originLon = parseFloat(inputJson.longitude);
} else if (inputJson.originLat !== undefined && inputJson.originLat !== null && 
           inputJson.originLon !== undefined && inputJson.originLon !== null) {
  originLat = parseFloat(inputJson.originLat);
  originLon = parseFloat(inputJson.originLon);
} else {
  return [{ json: { error: "no_origin" } }];
}

// DESTINATION INPUT
const destLat = parseFloat(inputJson.destinationLat);
const destLon = parseFloat(inputJson.destinationLon);

// GTFS Data
let gtfs;
try { gtfs = $('Load GTFS').first().json; } catch (e) { gtfs = inputJson.gtfs || inputJson; }

const stations = gtfs.stations || [];
const line = gtfs.line || [];
const schedule = gtfs.schedule || [];
const fares = gtfs.fares || {};

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) * Math.sin(dLon/2)**2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

function findClosestStation(lat, lon) {
  let closest = null;
  let minDist = Infinity;
  for (const station of stations) {
    const dist = haversine(lat, lon, station.lat, station.lon);
    if (dist < minDist) {
      minDist = dist;
      closest = station;
    }
  }
  return closest;
}

const entryStation = findClosestStation(originLat, originLon);
const exitStation = findClosestStation(destLat, destLon);

// 1. TRAVEL TIME: ORIGIN -> ENTRY
const distToEntry = haversine(originLat, originLon, entryStation.lat, entryStation.lon);
const toEntryWalk = Math.max(1, Math.round((distToEntry / 5) * 60));
const toEntryVehicle = Math.max(1, Math.round((distToEntry / 20) * 60));

// 3. TRAVEL TIME: EXIT -> DESTINATION
const distFromExit = haversine(exitStation.lat, exitStation.lon, destLat, destLon);
const fromExitWalk = Math.max(1, Math.round((distFromExit / 5) * 60));
const fromExitVehicle = Math.max(1, Math.round((distFromExit / 20) * 60));

// Stop Count for Fare & Fallback
let stopCount = 0;
const entryIndex = line.indexOf(entryStation.name);
const exitIndex = line.indexOf(exitStation.name);
if (entryIndex !== -1 && exitIndex !== -1) {
  stopCount = Math.abs(entryIndex - exitIndex);
}

// 2. METRO RIDE TIME
const now = new Date();
const utcNow = now.getTime() + (now.getTimezoneOffset() * 60000);
const istNow = new Date(utcNow + (330 * 60000));
const currH = istNow.getHours();
const currM = istNow.getMinutes();
const currS = istNow.getSeconds();
const currentTimeStr = \`\${String(currH).padStart(2,'0')}:\${String(currM).padStart(2,'0')}:\${String(currS).padStart(2,'0')}\`;

const entrySchedules = schedule.filter(s => s.stop_id === entryStation.stop_id && s.departure_time >= currentTimeStr);
entrySchedules.sort((a, b) => a.departure_time.localeCompare(b.departure_time));

const nextTrain = entrySchedules.length > 0 ? entrySchedules[0] : null;
let metroMinutes = 0;
let scheduleUsed = false;
let nextDepartureTime = "N/A";

const parseTime = (t) => {
  const parts = t.split(':').map(Number);
  return parts[0] * 60 + parts[1] + (parts[2] || 0) / 60;
};

if (nextTrain) {
  nextDepartureTime = nextTrain.departure_time;
  // If schedule data has trip_id, try to match it. Otherwise fallback.
  let exitSchedule = null;
  if (nextTrain.trip_id) {
    exitSchedule = schedule.find(s => s.trip_id === nextTrain.trip_id && s.stop_id === exitStation.stop_id);
  }
  
  if (exitSchedule) {
    metroMinutes = Math.max(1, Math.round(Math.abs(parseTime(exitSchedule.departure_time) - parseTime(nextTrain.departure_time))));
    scheduleUsed = true;
  } else {
    metroMinutes = Math.max(1, Math.round(stopCount * 2.5));
    scheduleUsed = false;
  }
} else {
  metroMinutes = Math.max(1, Math.round(stopCount * 2.5));
  scheduleUsed = false;
}

// 4. TOTAL TIME
const totalWalk = toEntryWalk + metroMinutes + fromExitWalk;
const totalVehicle = toEntryVehicle + metroMinutes + fromExitVehicle;

// Fare
const fare = fares[stopCount] || 0;

// 5. OUTPUT
return [{
  json: {
    ...inputJson,
    entryStation: entryStation.name,
    exitStation: exitStation.name,
    fare: fare,
    toEntryWalk,
    toEntryVehicle,
    metroMinutes,
    fromExitWalk,
    fromExitVehicle,
    totalWalk,
    totalVehicle,
    scheduleUsed,
    nextDepartureTime
  }
}];`;

const formatReplyCode = `const q = $input.item ? $input.item.json : $json;

if (q.error === "no_origin") {
  return [{
    json: {
      replyMessage: "📍 Where are you starting from? Share your live location or type a place name \\n(e.g. 'from Kakkanad' or 'from Aluva station')"
    }
  }];
}

let reply = \`📍 \${q.entryStation} → \${q.exitStation}
💰 ₹\${q.fare}

🗺 Getting there:
~\${q.toEntryWalk} min walk or ~\${q.toEntryVehicle} min by vehicle to \${q.entryStation}

🚇 Metro ride: ~\${q.metroMinutes} min
Next train: \${q.nextDepartureTime}

🏁 From \${q.exitStation} to destination:
~\${q.fromExitWalk} min walk or ~\${q.fromExitVehicle} min by vehicle

⏱ Total estimate:
~\${q.totalWalk} min if walking both ends
~\${q.totalVehicle} min if taking a vehicle both ends\`;

if (q.scheduleUsed === false) {
  reply += \`\\n\\n⚠️ Train time is an estimate (schedule unavailable)\`;
}

return [{
  json: {
    replyMessage: reply
  }
}];`;

let updatedCount = 0;

for (const workflow of data) {
  if (workflow.nodes) {
    for (const node of workflow.nodes) {
      if (node.name === 'Process Query' && node.type === 'n8n-nodes-base.code') {
        node.parameters.jsCode = processQueryCode;
        updatedCount++;
      }
      if (node.name === 'Format Reply' && node.type === 'n8n-nodes-base.code') {
        node.parameters.jsCode = formatReplyCode;
        updatedCount++;
      }
    }
  }
}

if (updatedCount > 0) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
  console.log(\`Successfully updated \${updatedCount} nodes.\`);
} else {
  console.log('Nodes not found.');
}

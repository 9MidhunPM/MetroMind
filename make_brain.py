import json
import sys

# Read the valid JSON file returned by n8n_get_workflow
with open('/home/midhun/.gemini/antigravity-ide/brain/65234df3-872d-450b-9fe9-6bc28eac468c/.system_generated/steps/387/output.txt', 'r') as f:
    data = json.load(f)

wf_data = data['data']
nodes = wf_data['nodes']
connections = wf_data['connections']

brain_nodes_names = [
    "Text Message?",
    "MetroMind AI Agent",
    "Simple Memory — WhatsApp user",
    "Station Knowledge",
    "Text Parser",
    "Current Date & Time",
    "Calculator",
    "Weather Tool (stub)",
    "Book Ticket",
    "NVIDIA Nemotron Chat Model",
    "Plan Trip",
    "Format Agent Reply",
    "Unsupported Media Reply",
    "Twilio WhatsApp Send Message"
]

new_nodes = []
new_nodes.append({
    "name": "Execute Workflow Trigger",
    "type": "n8n-nodes-base.executeWorkflowTrigger",
    "position": [880, 656],
    "typeVersion": 1,
    "parameters": {}
})

for n in nodes:
    if n['name'] in brain_nodes_names:
        n_copy = dict(n)
        if 'typeVersion' not in n_copy:
            n_copy['typeVersion'] = 1
        new_nodes.append(n_copy)

new_connections = {}
new_connections["Execute Workflow Trigger"] = {
    "main": [
        [
            {"node": "Text Message?", "type": "main", "index": 0}
        ]
    ]
}

for src, targets in connections.items():
    if src in brain_nodes_names:
        new_connections[src] = targets

args = {
    "name": "Agent: WhatsApp Brain",
    "nodes": new_nodes,
    "connections": new_connections
}

with open('brain_args.json', 'w') as f:
    json.dump(args, f, indent=2)

print("Generated brain_args.json")

# MetroMind 🚇

MetroMind is an intelligent WhatsApp AI Assistant for the Kochi Metro (KMRL). It leverages large language models and the n8n automation framework to provide users with route planning, ticket booking, commute reminders, and personalised tourist itineraries seamlessly via WhatsApp.

## 📂 Project Structure

This repository is organized into three main components:

### 1. `fastapi-server/`
Contains the Python FastAPI backend which serves as the core data engine and scraper for the agent.
- **`api.py`**: The main FastAPI application serving GTFS data (schedules, fares, stations).
- **`booking.py`**: The Selenium-based scraper used to automate ticket booking on the KMRL portal.
- **`payment_extractor.py`**: A utility to extract payment and transaction details.
- **`kmrl.json`**: The static GTFS/schedule data for Kochi Metro.
- Includes `Dockerfile` and `requirements.txt` for easy deployment.

### 2. `n8n-workflows/`
Contains the exported JSON representations of all the n8n workflows and tools that power the MetroMind AI.
- **`workflow_whatsapp_agent.json`**: The main webhook entry point (Twilio Sandbox) that handles inbound messages and routes them to the AI.
- **`workflow_whatsapp_brain.json`**: The core LangChain-based AI Agent that makes decisions, manages memory, and calls tools.
- **Tools**:
  - `workflow_trip_planner.json`: Handles route calculations and station lookups.
  - `workflow_book_ticket.json`: Interfaces with the FastAPI server to book tickets.
  - `n8n-workflow-kochi-metro-booking.json`: Alternative booking flows.
- *Note: Commute Manager and Tourist Itinerary workflows were built directly via MCP and can be exported here as well.*

### 3. `scripts-and-tests/`
Contains utility scripts used during development for testing routing logic and managing n8n workflows.
- Python and JavaScript test scripts (`test_closest.py`, `test_schedule.py`, `test_closest.js`).
- Scripts for dynamically updating and patching workflows (`update_workflows.js`, `make_brain.py`).

## 🚀 Deployment

1. **Backend**: Run the FastAPI server in a Docker container using the provided `Dockerfile`.
2. **n8n**: Import the workflows from the `n8n-workflows/` directory into your n8n instance. Make sure to set up your Twilio, OpenWeather, and Discord credentials within n8n.
3. **Twilio**: Configure your Twilio WhatsApp Sandbox webhook to point to the `MetroMind — WhatsApp Agent` trigger URL.

---
_Built with ❤️ for Kochi_

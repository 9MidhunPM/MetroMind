# MetroMind 🚇

**MetroMind** is an intelligent, agentic WhatsApp AI Assistant designed exclusively for the **Kochi Metro (KMRL)**. It transforms how commuters interact with the metro system by moving beyond simple chatbots and utilizing a robust **LangChain AI Agent** architecture powered by n8n and Python.

Users can plan complex trips, share live GPS locations, book real tickets, save recurring commute alerts, and even ask for personalized tourist itineraries—all through a natural WhatsApp conversation.

---

## ✨ Key Features

- 🗺️ **Intelligent Route Planning**: Calculates the fastest route, travel times, fares, and the exact next train departure times using static GTFS data. Users can share their live WhatsApp location to instantly find the closest station.
- 🎫 **Live Ticket Booking**: Automates the KMRL ticket booking portal via a Selenium-powered Python backend. It securely negotiates the booking flow and returns a direct payment link to the user on WhatsApp.
- ⏰ **Smart Commute Reminders**: Users can ask the agent to "save my commute" (e.g., *Aluva to MG Road every weekday at 9:00 AM*). A scheduled engine continuously checks these profiles and sends a proactive push notification to the user's WhatsApp 15 minutes before departure, complete with live weather and train times.
- 🌴 **Tourist Mode**: Generates highly personalized day-trip itineraries. Whether a user has a "half-day for shopping" or a "full-day for history", MetroMind calculates travel times between key Kochi attractions and builds a seamless travel schedule with Google Maps integration.
- 🧠 **Agentic AI Brain**: Powered by advanced LLMs (like OpenRouter GPT-4 / NVIDIA Nemotron). The agent maintains conversational memory and autonomously decides which internal "Tools" to call based on the user's intent.

---

## 📂 Project Architecture & Structure

The repository is divided into three core components:

### 1. `fastapi-server/`
The backend data engine and web-automation service.
- **`api.py`**: A FastAPI application that serves the Kochi Metro GTFS data to the n8n workflows.
- **`booking.py`**: A headless Selenium script that programmatically navigates the official KMRL ticketing portal to reserve tickets on behalf of the user.
- **`payment_extractor.py`**: Helper script to securely extract transaction IDs and payment links from the KMRL portal.
- **`kmrl.json`**: The comprehensive dataset containing station coordinates, dynamic fare matrices, and the entire train schedule.
- Includes a `Dockerfile` and `requirements.txt` for immediate deployment.

### 2. `n8n-workflows/`
The orchestration layer. These JSON files can be imported directly into an n8n instance to instantly recreate the AI Agent.
- **`workflow_whatsapp_agent_v2.json`**: The primary webhook entry point for Twilio. It normalizes incoming phone numbers, extracts GPS coordinates, and passes the context to the Brain.
- **`workflow_whatsapp_brain_v2.json`**: The core LangChain AI Agent. It uses `Simple Memory` to remember conversation history and intelligently routes requests to the appropriate sub-workflow tools.
- **Agent Tools:**
  - `workflow_trip_planner_v2.json`: Handles distance calculations, Haversine formulas, and time math for route planning.
  - `workflow_book_ticket_v2.json`: Interfaces with the Python FastAPI server to execute the Selenium booking script.
  - `workflow_commute_manager_v2.json`: Saves and deletes user commute profiles in the global n8n static data state.
  - `workflow_tourist_itinerary_v2.json`: Dynamically filters a database of Kochi attractions to build timed itineraries.
- **`workflow_commute_reminder_v2.json`**: A standalone CRON-triggered workflow that runs every minute. It checks the global state for active commute profiles, calculates triggers, fetches live OpenWeather data, and pushes alerts via Twilio.

### 3. `scripts-and-tests/`
Utility scripts used for development, local testing, and patching workflows programmatically.
- `test_closest.py` / `test_closest.js`: Unit tests for the Haversine distance logic.
- `update_workflows.js`: Script used to patch n8n workflow nodes dynamically.

---

## 🚀 Deployment Guide

### Step 1: Backend Setup
1. Navigate to the `fastapi-server` directory.
2. Build and run the Docker container to launch the FastAPI endpoints and the Selenium environment.
   ```bash
   docker build -t metromind-api .
   docker run -d -p 8000:8000 metromind-api
   ```

### Step 2: n8n Workflow Import
1. Open your n8n instance.
2. Import the workflows from the `n8n-workflows/` directory. **Start with the Tool workflows**, then import the Brain, and finally the Agent.
3. Configure your **Credentials** in n8n:
   - **Twilio API**: For sending and receiving WhatsApp messages.
   - **OpenWeather API**: (`httpQueryAuth` credential with `appid`) used for fetching live weather data for commutes.
   - **LLM Provider**: (e.g., NVIDIA Nemotron or OpenAI) attached to the Chat Model nodes in the Brain and Trip Planner.

### Step 3: Twilio Configuration
1. In your Twilio Console, navigate to your WhatsApp Sandbox or registered number.
2. Set the "When a message comes in" webhook URL to the Production URL of your `MetroMind — WhatsApp Agent V2` workflow.

---
_Built with ❤️ for Kochi_

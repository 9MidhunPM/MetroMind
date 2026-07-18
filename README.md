# MetroMind 🚇

**MetroMind** is an intelligent, agentic WhatsApp AI Assistant designed exclusively for the **Kochi Metro (KMRL)**. It transforms how commuters interact with the metro system by moving beyond simple chatbots and utilizing a robust **LangChain AI Agent** architecture powered by n8n and Python.

Users can plan complex trips, share live GPS locations, book real tickets, save recurring commute alerts, and even ask for personalized tourist itineraries—all through a natural WhatsApp conversation.

---

## ✨ Key Features

### 🧠 Agentic AI Brain
Powered by advanced LLMs (like OpenRouter GPT-4 / NVIDIA Nemotron). The agent maintains conversational memory and autonomously decides which internal "Tools" to call based on the user's intent. It has complete awareness of its capabilities and seamlessly routes requests.
<br>
![Agent Purpose Demo](assets/agent_purpose_demo.png)

### 🗺️ Intelligent Route Planning
Calculates the fastest route, travel times, fares, and the exact next train departure times using static GTFS data. Users can share their live WhatsApp location to instantly find the closest station.
<br>
![Trip Planner Demo](assets/trip_planner_demo.png)

### 🎫 Live Ticket Booking & Seamless Payments
Automates the KMRL ticket booking portal via a Selenium-powered Python backend. It securely negotiates the booking flow and returns a direct payment link to the user on WhatsApp. Users can securely pay using Google Pay or their preferred UPI app directly from their phone.
<br>
![Booking Demo](assets/booking_demo.png)
<br>
<img src="assets/payment_gateway_demo.jpg" width="45%" style="display:inline-block; margin-right:5%;" alt="Payment Gateway UI">
<img src="assets/gpay_upi_demo.jpg" width="45%" style="display:inline-block;" alt="Google Pay UPI Flow">

### ⏰ Smart Commute Reminders
Users can ask the agent to "save my commute" (e.g., *Aluva to MG Road every weekday at 9:00 AM*). A scheduled engine continuously checks these profiles and sends a proactive push notification to the user's WhatsApp 15 minutes before departure, complete with live weather and train times.
<br>
![Commute Demo](assets/commute_demo.png)

### 🌴 Tourist Mode
Generates highly personalized day-trip itineraries. Whether a user has a "half-day for shopping" or a "full-day for history", MetroMind calculates travel times between key Kochi attractions and builds a seamless travel schedule with Google Maps integration.
<br>
![Tourist Demo](assets/tourist_demo.png)
<br>
![Tourist Maps Route](assets/tourist_maps_demo.png)

---

## 📂 Project Architecture & Structure

The repository is divided into three core components:

### 1. `fastapi-server/`
The backend data engine and web-automation service.
- **`api.py`**: A FastAPI application that serves the Kochi Metro GTFS data to the n8n workflows.
- **`booking.py`**: A headless Selenium script that programmatically navigates the official KMRL ticketing portal to reserve tickets on behalf of the user.
- **`payment_extractor.py`**: Helper script to securely extract transaction IDs and payment links from the KMRL portal.
- **`kmrl.json`**: The comprehensive dataset containing station coordinates, dynamic fare matrices, and the entire train schedule.

### 2. `n8n-workflows/`
The orchestration layer. These JSON files can be imported directly into an n8n instance to instantly recreate the AI Agent.

#### WhatsApp Agent (Webhook Entry)
The primary webhook entry point for Twilio. It normalizes incoming phone numbers, extracts GPS coordinates, and passes the context to the Brain.
![WhatsApp Agent](assets/whatsapp_agent.png)

#### AI Brain (LangChain)
The core LangChain AI Agent. It uses `Simple Memory` to remember conversation history and intelligently routes requests to the appropriate sub-workflow tools.
![Brain Agent](assets/brain_agent.png)

#### Tool: Trip Planner
Handles distance calculations, Haversine formulas, and time math for route planning.
![Trip Planner](assets/trip_planner.png)

#### Tool: Book Ticket
Interfaces with the Python FastAPI server to execute the Selenium booking script.
![Book Ticket](assets/book_ticket.png)

#### Tool: Commute Manager
Saves and deletes user commute profiles in the global n8n static data state.
![Commute Manager](assets/commute_manager.png)

*Additional workflows include the CRON-triggered Commute Reminder and the personalized Tourist Itinerary generator.*

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

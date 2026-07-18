from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import traceback
import logging

from booking import book_ticket

app = FastAPI(title="MindMetro Booking API")
logger = logging.getLogger(__name__)

class BookingRequest(BaseModel):
    url: str
    origin: str
    destination: str
    passengers: int = 1

@app.post("/book")
async def create_booking(request: BookingRequest):
    try:
        logger.info(f"Received booking request: {request.origin} -> {request.destination} (Passengers: {request.passengers})")
        
        # Call the Playwright automation
        result = await book_ticket(
            url=request.url,
            origin=request.origin,
            destination=request.destination,
            passengers=request.passengers
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result)
            
    except Exception as e:
        logger.error(f"Error processing booking request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

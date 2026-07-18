from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from urllib.parse import quote, unquote
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
            # If the payment_url is a UPI deeplink, wrap it in our /pay redirect
            payment_url = result.get("payment_url", "")
            if payment_url and any(payment_url.lower().startswith(s) for s in ("upi://", "tez://", "phonepe://", "paytmmp://", "intent://")):
                result["payment_url"] = f"https://mindmetroapi.midhunapi.me/pay?url={quote(payment_url, safe='')}"
            return result
        else:
            raise HTTPException(status_code=500, detail=result)
            
    except Exception as e:
        logger.error(f"Error processing booking request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})


@app.get("/pay", response_class=HTMLResponse)
async def pay_redirect(url: str = Query(..., description="The UPI deeplink to redirect to")):
    """
    Wraps a UPI deeplink (upi://, tez://, etc.) in an HTTPS page.
    WhatsApp auto-hyperlinks https:// URLs, so users tap this link,
    the page opens in their browser, and immediately redirects to
    the UPI app (Google Pay, PhonePe, etc.).
    """
    deeplink = unquote(url)
    
    # Basic safety: only allow known payment URI schemes
    allowed_schemes = ("upi://", "tez://", "phonepe://", "paytmmp://", "intent://")
    if not any(deeplink.lower().startswith(s) for s in allowed_schemes):
        raise HTTPException(status_code=400, detail="Invalid payment URL scheme")
    
    # Serve a minimal HTML page that auto-redirects to the deeplink
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MindMetro — Pay with Google Pay</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            background: rgba(255,255,255,0.08);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 20px;
            padding: 40px 32px;
            text-align: center;
            max-width: 380px;
            width: 90%;
        }}
        .logo {{ font-size: 48px; margin-bottom: 16px; }}
        h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 8px; }}
        p {{ font-size: 14px; color: rgba(255,255,255,0.7); margin-bottom: 28px; }}
        .pay-btn {{
            display: inline-block;
            background: linear-gradient(135deg, #4285F4, #34A853);
            color: #fff;
            font-size: 18px;
            font-weight: 600;
            padding: 16px 40px;
            border-radius: 12px;
            text-decoration: none;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            box-shadow: 0 4px 20px rgba(66,133,244,0.4);
        }}
        .pay-btn:active {{ transform: scale(0.97); }}
        .footer {{ margin-top: 24px; font-size: 12px; color: rgba(255,255,255,0.4); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">🚇</div>
        <h1>Kochi Metro Ticket</h1>
        <p>Redirecting you to Google Pay...</p>
        <a href="{deeplink}" class="pay-btn">💳 Pay using Google Pay</a>
        <p class="footer">Powered by MindMetro</p>
    </div>
    <script>
        // Auto-redirect after a brief delay so the page renders first
        setTimeout(function() {{
            window.location.href = "{deeplink}";
        }}, 1500);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

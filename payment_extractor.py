import asyncio
import base64
import io
import logging
import re
import time
from pathlib import Path
from playwright.async_api import Page, Response

# Attempt to import pyzbar and OpenCV for QR decoding
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    from PIL import Image
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False
    Image = None
    pyzbar_decode = None

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

logger = logging.getLogger(__name__)

UPI_KEYWORDS = [
    "upi://", "upi:", "pay?", "payee", "vpa", "pa=", "pn=",
    "tn=", "tr=", "mc=", "googlepay", "phonepe", "tez", "gpay",
    "intent", "qr", "deep_link", "deeplink", "payment_link", "payment_url"
]

def _search_text_for_upi(text: str) -> str:
    """Helper to extract a valid UPI URI from text."""
    if not text:
        return None
    # Match standard upi:// and intent prefixes like tez://, phonepe://, paytmmp://
    match = re.search(r'(upi://pay\?[^\s\'">]+|tez://upi/pay\?[^\s\'">]+|phonepe://pay\?[^\s\'">]+|paytmmp://pay\?[^\s\'">]+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

async def _strategy_1_network(page: Page, timeout: int = 5) -> dict:
    """
    Strategy 1: Intercept all network traffic.
    Listens for a period of time to catch any XHR/Fetch polling or delayed intent URL fetches.
    Saves relevant network logs.
    """
    logger.info("STRATEGY 1 (Network): START")
    start_time = time.time()
    
    log_dir = Path("logs/network")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    found_uri = None
    captured_logs = []
    
    async def handle_response(response: Response):
        nonlocal found_uri
        if found_uri:
            return
            
        try:
            url = response.url
            headers = response.headers
            
            # Check URL for keywords
            if any(k in url.lower() for k in UPI_KEYWORDS):
                uri = _search_text_for_upi(url)
                if uri: found_uri = uri
                
            # Check headers
            for k, v in headers.items():
                if any(kw in v.lower() for kw in UPI_KEYWORDS):
                    uri = _search_text_for_upi(v)
                    if uri: found_uri = uri
            
            content_type = headers.get("content-type", "").lower()
            if "image" in content_type or "video" in content_type or "font" in content_type or "css" in content_type:
                return
                
            body = await response.body()
            
            # Keep raw body if it seems relevant or if it's Razorpay specific
            if "razorpay" in url or any(k in url.lower() for k in UPI_KEYWORDS):
                safe_url = re.sub(r'[^a-zA-Z0-9]', '_', url.split("?")[0])[-50:]
                filepath = log_dir / f"resp_{int(time.time()*1000)}_{safe_url}.txt"
                filepath.write_bytes(body)
                captured_logs.append(str(filepath))
            
            body_text = body.decode('utf-8', errors='ignore')
            
            # Search in body text
            uri = _search_text_for_upi(body_text)
            if uri:
                found_uri = uri
                return
                
            # Check for Base64 encoded payloads in the text
            b64_strings = re.findall(r'(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?', body_text)
            for b64 in b64_strings:
                try:
                    decoded = base64.b64decode(b64).decode('utf-8')
                    uri = _search_text_for_upi(decoded)
                    if uri:
                        found_uri = uri
                        return
                except Exception:
                    pass

        except Exception as e:
            # Body might be unavailable (e.g., aborted request or redirect)
            pass

    page.context.on("response", handle_response)
    
    # Wait to capture any delayed or polling network traffic
    try:
        for _ in range(timeout * 2): # Check every 0.5s
            if found_uri:
                break
            await asyncio.sleep(0.5)
    finally:
        page.context.remove_listener("response", handle_response)
        
    time_taken = time.time() - start_time
    if found_uri:
        logger.info(f"STRATEGY 1 (Network): SUCCESS - Time taken: {time_taken:.2f}s")
        return {"success": True, "method": "network", "upi_uri": found_uri, "payment_url": found_uri, "raw_data": captured_logs}
    
    logger.info(f"STRATEGY 1 (Network): FAILURE - Time taken: {time_taken:.2f}s")
    return {"success": False, "raw_data": captured_logs}

async def _strategy_2_dom(page: Page) -> dict:
    """
    Strategy 2: Inspect the DOM.
    Recursively searches href, data-*, aria-label, onclick, scripts, and window globals.
    """
    logger.info("STRATEGY 2 (DOM): START")
    start_time = time.time()
    
    try:
        for frame in page.frames:
            # We inject JS to search the DOM synchronously to avoid massive serialization overhead
            script = """
            () => {
                const searchRegex = /(upi:\\/\\/pay\\?[^\\s\\'">]+|tez:\\/\\/upi\\/pay\\?[^\\s\\'">]+|phonepe:\\/\\/pay\\?[^\\s\\'">]+|paytmmp:\\/\\/pay\\?[^\\s\\'">]+)/i;
                
                try {
                    // Check elements
                    const els = document.querySelectorAll('*');
                    for (const el of els) {
                        if (el.href && el.href.match(searchRegex)) return el.href.match(searchRegex)[0];
                        if (el.onclick && el.onclick.toString().match(searchRegex)) return el.onclick.toString().match(searchRegex)[0];
                        
                        let ariaLabel = el.getAttribute('aria-label');
                        if (ariaLabel && ariaLabel.match(searchRegex)) return ariaLabel.match(searchRegex)[0];
                        
                        for (const attr of el.attributes) {
                            if (attr.name.startsWith('data-') && attr.value.match(searchRegex)) {
                                return attr.value.match(searchRegex)[0];
                            }
                        }
                    }
                    
                    // Check scripts
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        if (script.innerText && script.innerText.match(searchRegex)) {
                            return script.innerText.match(searchRegex)[0];
                        }
                    }
                    
                    // Check window globals (shallow search)
                    for (const key of Object.keys(window)) {
                        try {
                            if (typeof window[key] === 'string' && window[key].match(searchRegex)) {
                                return window[key].match(searchRegex)[0];
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
                
                return null;
            }
            """
            result = await frame.evaluate(script)
            if result:
                time_taken = time.time() - start_time
                logger.info(f"STRATEGY 2 (DOM): SUCCESS - Time taken: {time_taken:.2f}s")
                return {"success": True, "method": "dom", "upi_uri": result, "payment_url": result, "raw_data": None}
    except Exception as e:
        logger.warning(f"STRATEGY 2 (DOM): Error during extraction: {e}")
        
    time_taken = time.time() - start_time
    logger.info(f"STRATEGY 2 (DOM): FAILURE - Time taken: {time_taken:.2f}s")
    return {"success": False}

async def _strategy_3_qr(page: Page) -> dict:
    """
    Strategy 3: Detect and decode QR code visually using pyzbar and OpenCV.
    """
    logger.info("STRATEGY 3 (QR): START")
    start_time = time.time()
    
    if not HAS_PYZBAR and not HAS_CV2:
        logger.warning("STRATEGY 3 (QR): pyzbar and cv2 are not installed. Skipping strategy.")
        return {"success": False}
        
    try:
        for frame in page.frames:
            # Find elements that might be the QR code
            locators = await frame.locator("canvas, svg, img").all()
            
            for el in locators:
                # Filter out elements that are not visible or too small
                if not await el.is_visible():
                    continue
                    
                box = await el.bounding_box()
                if not box or box['width'] < 100 or box['height'] < 100:
                    continue 
                    
                # Take element screenshot
                screenshot_bytes = await el.screenshot()
                
                # Try pyzbar
                if HAS_PYZBAR:
                    try:
                        img = Image.open(io.BytesIO(screenshot_bytes))
                        decoded_objects = pyzbar_decode(img)
                        for obj in decoded_objects:
                            data = obj.data.decode('utf-8')
                            uri = _search_text_for_upi(data)
                            if uri:
                                time_taken = time.time() - start_time
                                logger.info(f"STRATEGY 3 (QR): SUCCESS via pyzbar - Time taken: {time_taken:.2f}s")
                                return {"success": True, "method": "qr", "upi_uri": uri, "payment_url": uri, "raw_data": None}
                    except Exception as e:
                        logger.debug(f"pyzbar decode failed: {e}")
                
                # Fallback to OpenCV
                if HAS_CV2:
                    try:
                        nparr = np.frombuffer(screenshot_bytes, np.uint8)
                        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        detector = cv2.QRCodeDetector()
                        data, bbox, _ = detector.detectAndDecode(cv_img)
                        
                        if data:
                            uri = _search_text_for_upi(data)
                            if uri:
                                time_taken = time.time() - start_time
                                logger.info(f"STRATEGY 3 (QR): SUCCESS via OpenCV - Time taken: {time_taken:.2f}s")
                                return {"success": True, "method": "qr", "upi_uri": uri, "payment_url": uri, "raw_data": None}
                    except Exception as e:
                        logger.debug(f"OpenCV decode failed: {e}")
                        
    except Exception as e:
        logger.warning(f"STRATEGY 3 (QR): Error during QR detection: {e}")

    time_taken = time.time() - start_time
    logger.info(f"STRATEGY 3 (QR): FAILURE - Time taken: {time_taken:.2f}s")
    return {"success": False}

async def _strategy_4_fallback(page: Page, network_logs: list) -> dict:
    """
    Strategy 4: Save everything for debugging if all strategies fail.
    """
    logger.info("STRATEGY 4 (Fallback): START")
    start_time = time.time()
    
    log_dir = Path("logs/debug")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    
    png_path = log_dir / f"fallback_{timestamp}.png"
    html_path = log_dir / f"fallback_{timestamp}.html"
    
    try:
        await page.screenshot(path=str(png_path), full_page=True)
        
        html_content = await page.content()
        html_path.write_text(html_content, encoding='utf-8')
        
    except Exception as e:
        logger.error(f"STRATEGY 4 (Fallback): Failed to save debug info: {e}")
        
    time_taken = time.time() - start_time
    logger.info(f"STRATEGY 4 (Fallback): COMPLETED - Time taken: {time_taken:.2f}s")
    
    return {
        "success": False,
        "reason": "All extraction strategies failed.",
        "screenshots": str(png_path),
        "html_log": str(html_path),
        "network_log": network_logs,
        "trace": "Trace should be stopped in booking.py"
    }

async def extract_payment(page: Page) -> dict:
    """
    Entrypoint for payment extraction. 
    Attempts Network, DOM, and QR code strategies in order.
    Returns immediately when one succeeds.
    """
    logger.info("Starting Payment Extraction...")
    
    # Strategy 1
    network_result = await _strategy_1_network(page)
    if network_result["success"]:
        return network_result
        
    # Strategy 2
    dom_result = await _strategy_2_dom(page)
    if dom_result["success"]:
        return dom_result
        
    # Strategy 3
    qr_result = await _strategy_3_qr(page)
    if qr_result["success"]:
        return qr_result
        
    # Strategy 4
    return await _strategy_4_fallback(page, network_result.get("raw_data", []))

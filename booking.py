import asyncio
import json
import logging
import re
import sys
import traceback
import os
import time
from pathlib import Path

# Step 9: Enable PWDEBUG for Playwright Inspector only if explicitly requested
if os.getenv("PWDEBUG") in ("1", "true"):
    os.environ["PWDEBUG"] = "1"
else:
    os.environ.pop("PWDEBUG", None)

from playwright.async_api import async_playwright, Page, expect
from payment_extractor import extract_payment


# Add colors for differentiable console output
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[92m",    # Green
        logging.WARNING: "\033[93m", # Yellow
        logging.ERROR: "\033[91m",   # Red
        logging.DEBUG: "\033[94m"    # Blue
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(ColorFormatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

async def inspect_page(page: Page, step_name: str = "error"):
    """
    Helper function to dump interactive elements on the page in case of a failure,
    saving the output to stderr and dumping the HTML.
    """
    logger.info(f"--- Inspecting page state for '{step_name}' ---")
    
    # Save HTML
    html_content = await page.content()
    html_path = f"screenshots/{step_name}_page.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"Saved page HTML to {html_path}")

    # Print interactable elements to help debugging
    try:
        elements = await page.evaluate(r"""
            () => {
                const els = document.querySelectorAll('button, input, select, a, [role="button"], [role="combobox"], [role="option"], [tabindex]');
                return Array.from(els).map(e => {
                    return {
                        tag: e.tagName.toLowerCase(),
                        id: e.id,
                        className: e.className,
                        text: e.innerText?.trim().substring(0, 50),
                        placeholder: e.getAttribute('placeholder'),
                        ariaLabel: e.getAttribute('aria-label'),
                        role: e.getAttribute('role'),
                        type: e.getAttribute('type'),
                        name: e.getAttribute('name'),
                        value: e.value
                    };
                });
            }
        """)
        logger.info("Found interactive elements:")
        for el in elements:
            # Filter out completely empty/useless elements for cleaner logs
            if any([el.get('text'), el.get('placeholder'), el.get('ariaLabel'), el.get('id'), el.get('name'), el.get('value')]):
                logger.info(f"Tag: {el.get('tag')} | Role: {el.get('role')} | Text: {el.get('text')} | Aria-Label: {el.get('ariaLabel')} | Placeholder: {el.get('placeholder')} | ID: {el.get('id')} | Name: {el.get('name')} | Value: {el.get('value')}")
    except Exception as e:
        logger.error(f"Failed to extract elements during inspect: {e}")
    logger.info("-------------------------------------------")

async def book_ticket(url: str, origin: str, destination: str, passengers: int) -> dict:
    """
    Automates the KMRL ticket booking flow.
    Returns a dictionary intended to be converted to JSON.
    """
    logger.info(f"Starting booking automation for: {origin} -> {destination} ({passengers} passengers)")
    
    # Ensure directories exist
    Path("screenshots").mkdir(exist_ok=True)
    Path("traces").mkdir(exist_ok=True)
    Path("videos").mkdir(exist_ok=True)

    result = {
        "success": False,
        "error": "Unknown error occurred"
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            args=["--disable-blink-features=AutomationControlled"]
        )
        # Set a mobile User-Agent so Razorpay serves mobile deep links instead of just QR codes
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            is_mobile=True,
            record_video_dir="videos/",
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 412, "height": 915} # Mobile viewport to ensure responsive UI works
        )
        
        # Enable tracing
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        page = await context.new_page()

        # Capture console and network for debugging
        page.on("console", lambda msg: logger.debug(f"BROWSER CONSOLE: {msg.type}: {msg.text}"))
        page.on("requestfailed", lambda req: logger.warning(f"REQUEST FAILED: {req.url} - {req.failure}"))

        step_counter = 1
        total_steps = 7

        try:
            # Step 1: Open booking URL
            logger.info(f"[{step_counter}/{total_steps}] Opening booking URL")
            step_counter += 1
            await page.goto(url, wait_until="networkidle")
            await page.screenshot(path="screenshots/01_page_loaded.png")

            # Step 2: Select Origin
            logger.info(f"[{step_counter}/{total_steps}] Selecting Origin Station: {origin}")
            step_counter += 1
            
            try:
                # The KMRL site uses Angular Material (`<mat-select>`).
                # Click the first combobox, wait for the panel, and click the specific mat-option.
                comboboxes = page.locator("mat-select[role='combobox']")
                await comboboxes.nth(0).wait_for(state="visible", timeout=15000)
                await comboboxes.nth(0).click()
                
                # Wait for the option list and click the correct origin
                option = page.locator("mat-option[role='option']").filter(has_text=origin).first
                await option.wait_for(state="visible", timeout=15000)
                await option.click()
            except Exception as e:
                logger.warning(f"Material origin selector failed: {e}")
                raise Exception("Could not locate Origin station input.")
            
            await page.screenshot(path="screenshots/02_origin_selected.png")

            # Step 3: Select Destination
            logger.info(f"[{step_counter}/{total_steps}] Selecting Destination Station: {destination}")
            step_counter += 1
            
            try:
                comboboxes = page.locator("mat-select[role='combobox']")
                await comboboxes.nth(1).wait_for(state="visible", timeout=15000)
                await comboboxes.nth(1).click()
                
                # Wait for the option list and click the correct destination
                option = page.locator("mat-option[role='option']").filter(has_text=destination).first
                await option.wait_for(state="visible", timeout=15000)
                await option.click()
            except Exception as e:
                logger.warning(f"Material destination selector failed: {e}")
                raise Exception("Could not locate Destination station input.")
            
            await page.screenshot(path="screenshots/03_destination_selected.png")

            # Step 4: Select Passengers
            logger.info(f"[{step_counter}/{total_steps}] Selecting {passengers} passengers")
            step_counter += 1
            
            try:
                passenger_select = page.locator("select#passengerCount").first
                if await passenger_select.is_visible(timeout=15000):
                    await passenger_select.select_option(str(passengers))
                else:
                    logger.warning("Passenger select element not found.")
            except Exception as e:
                logger.warning(f"Could not set passengers, continuing anyway: {e}")
            
            await page.screenshot(path="screenshots/04_passengers_selected.png")

            # Step 5: Click Get Fare
            logger.info(f"[{step_counter}/{total_steps}] Proceeding to Get Fare")
            step_counter += 1
            
            get_fare_button = page.get_by_role("button", name="Get Fare").or_(
                page.get_by_role("button", name="Continue")
            ).first
            
            await get_fare_button.wait_for(state="visible", timeout=15000)
            await get_fare_button.click()
            await page.screenshot(path="screenshots/05_get_fare_clicked.png")

            # Try to extract fare
            fare = "Unknown"
            try:
                # Find all elements with 'Rs', pick the one that looks like a price
                fare = await page.evaluate(r"""
                    () => {
                        const els = Array.from(document.querySelectorAll('*')).filter(e => e.innerText && e.innerText.match(/Rs\.?\s*\d+/i));
                        if (els.length > 0) {
                            // return the most deeply nested one containing the price
                            return els[els.length - 1].innerText.match(/Rs\.?\s*\d+/i)[0];
                        }
                        return "Unknown";
                    }
                """)
            except Exception as e:
                logger.warning(f"Could not extract fare: {e}")

            # Step 5.5: Click Book Ticket
            logger.info(f"[{step_counter}/{total_steps}] Clicking Book Ticket")
            step_counter += 1
            
            book_ticket_button = page.get_by_role("button", name="Book Ticket").or_(
                page.get_by_role("button", name="Proceed")
            ).or_(
                page.get_by_role("button", name="Pay")
            ).first
            
            await book_ticket_button.wait_for(state="visible", timeout=15000)
            await book_ticket_button.click()
            await page.screenshot(path="screenshots/06_book_ticket_clicked.png")

            # Step 6: Payment Screen State Transition Handler
            logger.info(f"[{step_counter}/{total_steps}] Handling Payment Stage Transitions...")
            step_counter += 1
            
            payment_url = url
            
            try:
                # Find and click Continue
                frame_loc = page.frame_locator("iframe[src*='checkout'], iframe[name*='razorpay']").first
                logger.info("Looking for 'Continue' button...")
                
                continue_btn = frame_loc.locator("button[data-testid='bottom-cta-button']:visible").or_(
                    frame_loc.locator("button:visible").filter(has_text=re.compile(r"^Continue.*?Pay|^Continue$", re.IGNORECASE))
                )
                await continue_btn.first.wait_for(state="visible", timeout=10000)
                await continue_btn.first.click()
                logger.info("SUCCESS: locator.click() on Continue button.")
                
                logger.info("Setting up advanced interceptors for Deeplinks...")
                found_urls = []
                def check_url(url_str):
                    if not url_str: return
                    url_lower = url_str.lower()
                    if url_lower.startswith(("upi://", "tez://", "phonepe://", "paytmmp://", "intent://")):
                        if url_str not in found_urls:
                            found_urls.append(url_str)
                            logger.info(f"CAPTURED DEEPLINK REDIRECT: {url_str}")
                            
                def handle_request(req): check_url(req.url)
                def handle_requestfailed(req): check_url(req.url)
                def handle_framenavigated(frame): check_url(frame.url)
                def handle_console(msg):
                    if "upi://" in msg.text or "tez://" in msg.text or "intent://" in msg.text:
                        logger.info(f"Console Deeplink found: {msg.text}")
                        match = re.search(r'(upi://[^\s\'">]+|tez://[^\s\'">]+|phonepe://[^\s\'">]+|paytmmp://[^\s\'">]+|intent://[^\s\'">]+)', msg.text, re.IGNORECASE)
                        if match: check_url(match.group(1))
                        

                def handle_new_page(new_page):
                    logger.info("NEW TAB DETECTED! Waiting for load...")
                    async def process_new_page(p):
                        try:
                            # Wait a bit for the page to navigate from about:blank
                            await p.wait_for_timeout(2000)
                            url_str = p.url
                            logger.info(f"New Tab URL after 2s: {url_str}")
                            
                            # If it's a valid redirect URL, save it
                            if url_str and "about:blank" not in url_str:
                                if url_str not in found_urls:
                                    found_urls.append(url_str)
                            
                            # Dump the HTML to see the "Should I allow redirects" screen
                            html = await p.content()
                            Path("logs/debug").mkdir(exist_ok=True)
                            Path(f"logs/debug/new_tab_{int(time.time())}.html").write_text(html, encoding='utf-8')
                            
                            # Search the raw HTML for any embedded deeplink
                            match = re.search(r'(upi://[^\s\'">]+|tez://[^\s\'">]+|intent://[^\s\'">]+|phonepe://[^\s\'">]+|paytmmp://[^\s\'">]+)', html, re.IGNORECASE)
                            if match:
                                logger.info(f"Extracted Deeplink from New Tab HTML: {match.group(1)}")
                                if match.group(1) not in found_urls:
                                    found_urls.append(match.group(1))
                        except Exception as e:
                            logger.debug(f"Error processing new page: {e}")

                    asyncio.create_task(process_new_page(new_page))

                async def handle_response(response):
                    try:
                        # Only check textual responses
                        if response.request.resource_type in ["document", "xhr", "fetch", "script"]:
                            text = await response.text()
                            match = re.search(r'(upi://[^\s\'">]+|tez://[^\s\'">]+|phonepe://[^\s\'">]+|paytmmp://[^\s\'">]+|intent://[^\s\'">]+)', text, re.IGNORECASE)
                            if match:
                                check_url(match.group(1))
                    except Exception:
                        pass
                
                async def capture_deeplink_binding(source, url):
                    check_url(url)
                    
                await context.expose_binding("captureDeeplink", capture_deeplink_binding)
                await context.add_init_script("""
                    const originalAssign = window.location.assign;
                    window.location.assign = function(url) {
                        if (url && (url.includes('://'))) window.captureDeeplink(url);
                        return originalAssign.apply(this, arguments);
                    };
                    const originalReplace = window.location.replace;
                    window.location.replace = function(url) {
                        if (url && (url.includes('://'))) window.captureDeeplink(url);
                        return originalReplace.apply(this, arguments);
                    };
                """)

                context.on("request", handle_request)
                context.on("requestfailed", handle_requestfailed)
                context.on("response", handle_response)
                page.on("framenavigated", handle_framenavigated)
                page.on("console", handle_console)
                context.on("page", handle_new_page)

                
                logger.info("Looking for 'Google Pay' option...")
                gpay_btn = frame_loc.locator("button:visible, div[role='button']:visible").filter(has_text=re.compile(r"Google Pay|GPay", re.IGNORECASE))
                
                try:
                    await frame_loc.locator("body").evaluate("""() => {
                        window._originalOpen = window.open;
                        window.open = function(url, name, specs) {
                            if (url && (url.includes('upi://') || url.includes('tez://') || url.includes('intent://'))) {
                                console.log('INTERCEPT_OPEN:' + url);
                                return null;
                            }
                            return window._originalOpen.apply(this, arguments);
                        };
                        window.addEventListener('click', function(e) {
                            let target = e.target.closest('a');
                            if (target && target.href && (target.href.includes('upi://') || target.href.includes('tez://') || target.href.includes('intent://'))) {
                                console.log('INTERCEPT_CLICK:' + target.href);
                                e.preventDefault();
                            }
                        }, true);
                    }""")
                    logger.info("Injected window.open and click interceptors into iframe.")
                except Exception as e:
                    logger.debug(f"Failed to inject interceptors: {e}")

                try:
                    await gpay_btn.first.wait_for(state="visible", timeout=5000)
                    await gpay_btn.first.click()
                    logger.info("Clicked 'Google Pay' option.")
                except Exception as e:
                    logger.warning(f"Could not click Google Pay specifically: {e}")

                await page.wait_for_timeout(1000)
                
                logger.info("Looking for 'Pay Now' / 'Continue & Pay' button...")
                pay_now_btn = frame_loc.locator("button:visible, div[role='button']:visible").filter(has_text=re.compile(r"Pay Now|Continue.*?Pay|Pay \u20b9", re.IGNORECASE))
                
                try:
                    await pay_now_btn.first.wait_for(state="visible", timeout=5000)
                    await pay_now_btn.first.click()
                    logger.info("Clicked 'Pay Now' button.")
                except Exception as e:
                    logger.warning(f"Could not find 'Pay Now' button: {e}")
                
                logger.info("Waiting up to 15 seconds for Deeplink redirect...")
                start_wait = time.time()
                while time.time() - start_wait < 15:
                    if found_urls:
                        break
                    await page.wait_for_timeout(500)
                    
                context.remove_listener("request", handle_request)
                context.remove_listener("requestfailed", handle_requestfailed)
                context.remove_listener("response", handle_response)
                page.remove_listener("framenavigated", handle_framenavigated)
                page.remove_listener("console", handle_console)
                
                if found_urls:
                    payment_url = found_urls[0]
                    logger.info("Successfully extracted UPI Deeplink!")
                else:
                    logger.warning("Failed to capture deeplink redirect. Attempting fallback extraction...")
                    extractor_result = await extract_payment(page)
                    if extractor_result.get("success"):
                        payment_url = extractor_result.get("payment_url")
                    else:
                        payment_url = "Failed to extract deeplink or QR."
                        
            except Exception as e:
                logger.warning(f"Error during state transition monitoring: {e}")
                if page.url != url:
                    payment_url = page.url
                await page.screenshot(path="screenshots/08_payment_error_fallback.png")


            # Step 7: Success
            logger.info(f"[{step_counter}/{total_steps}] Success! Final payment URL/Link extracted.")
            
            result = {
                "success": True,
                "payment_url": payment_url,
                "fare": fare,
                "origin": origin,
                "destination": destination,
                "passengers": passengers
            }

        except Exception as e:
            logger.error(f"Automation failed: {e}")
            logger.error(traceback.format_exc())
            await inspect_page(page, "failure")
            await page.screenshot(path="screenshots/error_screenshot.png")
            result["error"] = str(e)
        finally:
            logger.info("Saving traces and closing browser...")
            await context.tracing.stop(path="traces/trace.zip")
            await browser.close()
            
        return result

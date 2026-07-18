# Kochi Metro Playwright Automation

This project automates the ticket booking process for the Kochi Metro (KMRL) booking portal using Python and Playwright. It is designed to be robust, return structured JSON for easy integration with backend systems (like FastAPI), and capture rich debugging data including screenshots, traces, and videos.

## Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

## Usage

Run the CLI tool using `main.py`:

```bash
python main.py \
    --url "https://prutech.org/KMRL/#/manage/ticket/XXXXXXXXXXXX" \
    --origin "Edapally" \
    --destination "Aluva" \
    --passengers 2
```

## Output

The script outputs only JSON to stdout.

**Success Response:**
```json
{
    "success": true,
    "payment_url": "...",
    "fare": "...",
    "origin": "Edapally",
    "destination": "Aluva",
    "passengers": 2
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "Detailed error message"
}
```

## Debugging Artifacts

- **Screenshots:** Stored in the `screenshots/` directory for major steps and upon any failure.
- **Videos:** Stored in the `videos/` directory for each browser context session.
- **Traces:** Stored in the `traces/` directory (e.g., `trace.zip`). Open traces using `playwright show-trace traces/trace.zip`.
- **Page HTML:** If a failure occurs, the HTML state is saved in `screenshots/error_page.html`.

# Playwright Title Reader

Streamlit frontend that launches a local Chromium instance via Playwright to read and display the `<title>` of any URL you provide.

## Setup

1. (Optional) Create and activate a virtual environment.
2. `python -m pip install --upgrade pip`
3. `pip install -r requirements.txt`
4. `python -m playwright install` *(or scope to a specific browser like `python -m playwright install chromium`).*
5. When deploying on Debian/Ubuntu, install the runtime dependencies listed in `packages.txt` with `xargs sudo apt-get install -y $(cat packages.txt)`.

## Running the app

```
streamlit run app.py
```

The UI launches Chromium locally, so ensure step 4 completes before clicking "Dapatkan Title."

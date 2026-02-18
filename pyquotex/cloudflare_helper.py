# cloudflare_helper.py
import json
import asyncio
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
COOKIES_FILE = "cookies.json"

async def get_cloudflare_cookies(url="https://qxbroker.com"):
    """Obtiene cookies  de Cloudflare usando Playwright headless"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        await page.goto(url, timeout=60000)

        # Esperar a que se resuelva el challenge
        await page.wait_for_load_state("networkidle")

        cookies = await context.cookies()
        await browser.close()

        # Guardar cookies en archivo
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)

        return cookies

def load_cookies_from_file():
    """Carga cookies desde cookies.json"""
    try:
        with open(COOKIES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

async def refresh_cookies_periodically(set_session_callback, interval=3600):
    """
    Renueva cookies cada cierto tiempo y las inyecta en la sesión.
    - set_session_callback: función que recibe (user_agent, cookies_json)
    - interval: tiempo en segundos entre renovaciones
    """
    while True:
        try:
            cookies = await get_cloudflare_cookies()
            cookies_json = json.dumps(cookies)
            set_session_callback(USER_AGENT, cookies_json)
            print("Cookies renovadas correctamente.")
        except Exception as e:
            print(f"Error renovando cookies: {e}")
        await asyncio.sleep(interval)
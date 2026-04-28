import os
import json
import asyncio
import sys
from playwright.async_api import async_playwright

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

async def run_backup(target_url=None):
    config = load_config()
    if not config:
        print("🚀 PRVO POKRETANJE: Podešavanje...")
        default_exe = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        default_user_data = os.path.join(os.environ['LOCALAPPDATA'], r"BraveSoftware\Brave-Browser\User Data")
        browser_path = input(f"Putanja do brave.exe [{default_exe}]: ") or default_exe
        user_data = input(f"Putanja do User Data mape [{default_user_data}]: ") or default_user_data
        config = {"browser_path": browser_path, "user_data": user_data}
        save_config(config)

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=config["user_data"],
                executable_path=config["browser_path"],
                headless=False,
                args=["--remote-debugging-port=9222"]
            )
            page = await context.new_page()
            url = target_url if target_url else "https://gemini.google.com/app"
            print(f"🌐 Otvaram: {url}")
            await page.goto(url)

            # Čekaj da se chat učita (user-query je znak da je chat tu)
            await page.wait_for_selector('user-query', timeout=60000)

            if os.path.exists("js_engine.js"):
                with open("js_engine.js", "r", encoding="utf-8") as f:
                    js_code = f.read()
                print("💉 Ubrizgavam JS motor...")
                page.on("console", lambda msg: print(f"🔍 JS LOG: {msg.text}"))
                await page.evaluate(js_code)
                print("⏳ Čekam završetak (cca 60 sekundi)...")
                await asyncio.sleep(60) 
            else:
                print("❌ GREŠKA: js_engine.js nedostaje!")

            await context.close()
        except Exception as e:
            print(f"❌ Greška: {e}\n(Provjerite je li Brave ZATVOREN!)")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_backup(url))

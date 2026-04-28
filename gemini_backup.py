#!/usr/bin/env python3
"""
Gemini Chat Backup Tool - Ultimate Version
Univerzalni backup alat za Gemini chatove koristeći Playwright
"""

import os
import sys
import json
import asyncio
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    print("Instaliram Playwright...")
    os.system("pip install playwright")
    os.system("playwright install chromium")
    from playwright.async_api import async_playwright, BrowserContext, Page


class Colors:
    """ANSI color codes za terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class GeminiBackupTool:
    """Glavna klasa za backup Gemini chatova"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent / "config.json"
        self.backup_dir = Path(__file__).parent / "backups"
        self.js_engine_path = Path(__file__).parent / "js_engine.js"
        self.config = self.load_config()
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    def load_config(self) -> dict:
        """Učitaj ili kreiraj konfiguraciju"""
        default_config = {
            "browsers": {
                "chrome": {
                    "name": "Google Chrome",
                    "executable": self._find_browser("chrome"),
                    "user_data": self._find_user_data("chrome"),
                    "profile": "Default"
                },
                "brave": {
                    "name": "Brave Browser",
                    "executable": self._find_browser("brave"),
                    "user_data": self._find_user_data("brave"),
                    "profile": "Default"
                },
                "edge": {
                    "name": "Microsoft Edge",
                    "executable": self._find_browser("edge"),
                    "user_data": self._find_user_data("edge"),
                    "profile": "Default"
                },
                "opera": {
                    "name": "Opera Browser",
                    "executable": self._find_browser("opera"),
                    "user_data": self._find_user_data("opera"),
                    "profile": "Default"
                }
            },
            "active_browser": None,
            "custom_browsers": [],
            "settings": {
                "wait_time_slow": 1000,
                "wait_time_fast": 400,
                "max_retries": 3,
                "max_messages": 10000,
                "export_format": ["markdown", "json"]
            },
            "gemini_url": "https://gemini.google.com/app"
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Kreiraj default konfiguraciju
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        return default_config
    
    def save_config(self):
        """Spremi konfiguraciju"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _find_browser(self, browser_name: str) -> str:
        """Automatski pronađi browser executable"""
        paths = {
            "chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe"
            ],
            "brave": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Users\{}\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
            ],
            "edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ],
            "opera": [
                r"C:\Users\{}\AppData\Local\Programs\Opera\opera.exe",
                r"C:\Program Files\Opera\opera.exe"
            ]
        }
        
        username = os.environ.get('USERNAME', '')
        
        if browser_name in paths:
            for path in paths[browser_name]:
                path = path.format(username) if '{}' in path else path
                expanded = os.path.expandvars(path)
                if Path(expanded).exists():
                    return expanded
        
        return ""
    
    def _find_user_data(self, browser_name: str) -> str:
        """Automatski pronađi User Data direktorij"""
        paths = {
            "chrome": r"C:\Users\{}\AppData\Local\Google\Chrome\User Data",
            "brave": r"C:\Users\{}\AppData\Local\BraveSoftware\Brave-Browser\User Data",
            "edge": r"C:\Users\{}\AppData\Local\Microsoft\Edge\User Data",
            "opera": r"C:\Users\{}\AppData\Roaming\Opera Software\Opera Stable"
        }
        
        username = os.environ.get('USERNAME', '')
        
        if browser_name in paths:
            path = paths[browser_name].format(username)
            expanded = os.path.expandvars(path)
            if Path(expanded).exists():
                return expanded
        
        return ""
    
    def detect_installed_browsers(self) -> List[str]:
        """Detektiraj instalirane preglednike"""
        installed = []
        for browser_name, browser_data in self.config["browsers"].items():
            if browser_data.get("executable") and Path(browser_data["executable"]).exists():
                installed.append(browser_name)
        
        # Provjeri custom browsere
        for custom in self.config.get("custom_browsers", []):
            if custom.get("executable") and Path(custom["executable"]).exists():
                installed.append(custom["name"].lower().replace(" ", "_"))
        
        return installed
    
    async def interactive_setup(self):
        """Interaktivni setup za prvo pokretanje"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}🚀 Gemini Chat Backup Tool - Prvo pokretanje{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        # Detektiraj instalirane browsere
        installed = self.detect_installed_browsers()
        
        if installed:
            print(f"{Colors.GREEN}✅ Pronađeni preglednici:{Colors.ENDC}")
            for i, browser in enumerate(installed, 1):
                print(f"  [{i}] {browser.title()}")
            print(f"  [0] Ručno dodavanje preglednika")
            
            while True:
                try:
                    choice = input(f"\n{Colors.CYAN}Odaberite preglednik (0-{len(installed)}): {Colors.ENDC}")
                    if choice == '0':
                        break
                    choice = int(choice)
                    if 1 <= choice <= len(installed):
                        self.config["active_browser"] = installed[choice - 1]
                        self.save_config()
                        print(f"{Colors.GREEN}✅ Odabran: {installed[choice - 1].title()}{Colors.ENDC}")
                        return
                except ValueError:
                    pass
                print(f"{Colors.RED}❌ Nevažeći odabir{Colors.ENDC}")
        
        # Ručno dodavanje
        print(f"\n{Colors.YELLOW}📁 Ručno dodavanje preglednika{Colors.ENDC}")
        print("Unesite putanju do .exe datoteke preglednika:")
        
        # Koristi Tkinter za file dialog ako je dostupan
        try:
            root = tk.Tk()
            root.withdraw()
            exe_path = filedialog.askopenfilename(
                title="Odaberite .exe datoteku preglednika",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            root.destroy()
        except:
            exe_path = input("Putanja do .exe: ").strip().strip('"')
        
        if not exe_path:
            print(f"{Colors.RED}❌ Nije odabrana putanja{Colors.ENDC}")
            sys.exit(1)
        
        print("Unesite putanju do User Data mape (Profile direktorij):")
        user_data = input("User Data: ").strip().strip('"')
        
        if not user_data:
            # Pokušaj automatski detektirati
            browser_dir = Path(exe_path).parent.parent.parent
            potential_user_data = browser_dir / "User Data"
            if potential_user_data.exists():
                user_data = str(potential_user_data)
            else:
                user_data = input("Ručno unesite User Data putanju: ").strip().strip('"')
        
        custom_name = input("Naziv preglednika (npr. 'Opera Portable'): ").strip() or "Custom Browser"
        custom_key = custom_name.lower().replace(" ", "_")
        
        self.config["custom_browsers"].append({
            "name": custom_name,
            "executable": exe_path,
            "user_data": user_data,
            "profile": "Default"
        })
        self.config["active_browser"] = custom_key
        self.save_config()
        
        print(f"{Colors.GREEN}✅ Konfiguracija spremljena!{Colors.ENDC}")
    
    def get_browser_config(self) -> dict:
        """Dohvati konfiguraciju aktivnog browsera"""
        active = self.config.get("active_browser")
        
        if not active:
            raise ValueError("Nije odabran preglednik. Pokrenite setup.")
        
        # Provjeri standardne browsere
        if active in self.config["browsers"]:
            return self.config["browsers"][active]
        
        # Provjeri custom browsere
        for custom in self.config.get("custom_browsers", []):
            if custom["name"].lower().replace(" ", "_") == active:
                return custom
        
        raise ValueError(f"Browser '{active}' nije pronađen u konfiguraciji")
    
    async def launch_browser(self, headless: bool = False):
        """Pokreni browser s persistent context (ulogirani profil)"""
        browser_config = self.get_browser_config()
        
        executable_path = browser_config["executable"]
        user_data_dir = browser_config["user_data"]
        profile = browser_config.get("profile", "Default")
        
        if not Path(executable_path).exists():
            raise FileNotFoundError(f"Browser .exe nije pronađen: {executable_path}")
        
        if not Path(user_data_dir).exists():
            raise FileNotFoundError(f"User Data direktorij nije pronađen: {user_data_dir}")
        
        print(f"{Colors.CYAN}🚀 Pokrećem browser...{Colors.ENDC}")
        print(f"   Izvršna datoteka: {executable_path}")
        print(f"   User Data: {user_data_dir}")
        print(f"   Profil: {profile}")
        
        self.playwright = await async_playwright().start()
        
        # Koristi launch_persistent_context za očuvanje login sesije
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel=None if "custom" in str(type(browser_config)) else None,
            executable_path=executable_path,
            headless=headless,
            args=[
                f'--profile-directory={profile}',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--start-maximized'
            ],
            viewport=None,  # Koristi maximized prozor
            ignore_default_args=['--enable-automation']
        )
        
        self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
        
        # Učitaj JS engine
        await self.inject_js_engine()
        
        print(f"{Colors.GREEN}✅ Browser pokrenut{Colors.ENDC}")
    
    async def inject_js_engine(self):
        """Ubrizgaj JavaScript motor u stranicu"""
        if not self.js_engine_path.exists():
            raise FileNotFoundError(f"JS engine nije pronađen: {self.js_engine_path}")
        
        with open(self.js_engine_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        
        await self.page.evaluate(js_code)
        print(f"{Colors.GREEN}✅ JS engine ubrizgan{Colors.ENDC}")
    
    async def navigate_to_gemini(self):
        """Navigiraj na Gemini"""
        gemini_url = self.config.get("gemini_url", "https://gemini.google.com/app")
        print(f"{Colors.CYAN}🧭 Navigiram na Gemini...{Colors.ENDC}")
        
        await self.page.goto(gemini_url, wait_until='networkidle', timeout=30000)
        
        # Čekaj da se stranica učita
        try:
            await self.page.wait_for_selector('user-query, [data-message-role], .user-query', timeout=15000)
            print(f"{Colors.GREEN}✅ Gemini učitan{Colors.ENDC}")
        except:
            print(f"{Colors.YELLOW}⚠️  Nije pronađen chat sadržaj. Provjerite jeste li ulogirani.{Colors.ENDC}")
            
            # Pokušaj čekati login
            input(f"{Colors.CYAN}Pritisnite Enter nakon što se ulogirate...{Colors.ENDC}")
            await self.page.wait_for_selector('user-query, [data-message-role]', timeout=30000)
    
    async def backup_current_chat(self, chat_url: Optional[str] = None) -> Dict[str, Any]:
        """Backup trenutnog chata"""
        if chat_url:
            print(f"\n{Colors.CYAN}📄 Otvaram chat: {chat_url}{Colors.ENDC}")
            await self.page.goto(chat_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await self.inject_js_engine()
        
        print(f"{Colors.CYAN}📜 Pokrećem backup...{Colors.ENDC}")
        
        # Pokreni backup preko JS engine-a
        result = await self.page.evaluate("""
            async () => {
                if (typeof GeminiBackup === 'undefined') {
                    throw new Error('JS Engine not loaded');
                }
                return await GeminiBackup.performBackup();
            }
        """)
        
        if result and result.get('markdown'):
            # Spremi backup
            chat_title = await self.page.evaluate("GeminiBackup.getChatTitle()")
            backup_files = self.save_backup(result, chat_title)
            
            print(f"{Colors.GREEN}✅ Backup završen!{Colors.ENDC}")
            print(f"   Naslov: {chat_title}")
            print(f"   Poruka: {result.get('totalMessages', 0)}")
            
            if 'markdown_path' in backup_files:
                print(f"   Markdown: {backup_files['markdown_path']}")
            if 'json_path' in backup_files:
                print(f"   JSON: {backup_files['json_path']}")
            
            return result
        else:
            print(f"{Colors.RED}❌ Backup nije uspio - nema rezultata{Colors.ENDC}")
            return {}
    
    def save_backup(self, result: dict, chat_title: str) -> dict:
        """Spremi backup na disk"""
        # Sanitiziraj naziv datoteke
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', chat_title)[:100]
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename_base = f"{date_str}_{safe_title}"
        
        # Kreiraj direktorij za današnji datum
        date_dir = self.backup_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        backup_files = {}
        
        # Spremi Markdown
        if 'markdown' in result:
            md_path = date_dir / f"{filename_base}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(result['markdown'])
            backup_files['markdown_path'] = str(md_path)
        
        # Spremi JSON
        if 'json' in result:
            json_path = date_dir / f"{filename_base}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result['json'], f, indent=2, ensure_ascii=False)
            backup_files['json_path'] = str(json_path)
        
        return backup_files
    
    async def auto_sidebar_backup(self):
        """Automatski backup svih chatova iz sidebar-a"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}📚 AUTO-SIDEBAR BACKUP{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        # Dohvati sve chat linkove
        chat_links = await self.page.evaluate("GeminiBackup.getSidebarChats()")
        
        if not chat_links:
            print(f"{Colors.RED}❌ Nije pronađen nijedan chat u sidebaru{Colors.ENDC}")
            return
        
        print(f"{Colors.GREEN}✅ Pronađeno {len(chat_links)} chatova:{Colors.ENDC}")
        for i, chat in enumerate(chat_links, 1):
            print(f"  [{i}] {chat.get('title', 'Nepoznato')}")
        
        print(f"\n{Colors.CYAN}Započinjem backup...{Colors.ENDC}")
        
        success_count = 0
        fail_count = 0
        
        for i, chat in enumerate(chat_links, 1):
            print(f"\n{Colors.YELLOW}[{i}/{len(chat_links)}] {chat.get('title', 'Nepoznato')}{Colors.ENDC}")
            
            try:
                url = chat.get('url')
                if url:
                    # Ako je relativni URL, dodaj bazu
                    if not url.startswith('http'):
                        url = f"https://gemini.google.com{url}"
                    
                    await self.backup_current_chat(url)
                    success_count += 1
                    
                    # Kratka pauza između chatova
                    await asyncio.sleep(1)
                else:
                    print(f"{Colors.RED}❌ Nevažeći URL{Colors.ENDC}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"{Colors.RED}❌ Greška: {e}{Colors.ENDC}")
                fail_count += 1
        
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}📊 Rezultati:{Colors.ENDC}")
        print(f"   ✅ Uspješno: {success_count}")
        print(f"   ❌ Neuspješno: {fail_count}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    async def process_links_file(self, file_path: str):
        """Procesiraj .txt datoteku s linkovima"""
        if not Path(file_path).exists():
            print(f"{Colors.RED}❌ Datoteka nije pronađena: {file_path}{Colors.ENDC}")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not links:
            print(f"{Colors.RED}❌ Nema linkova u datoteci{Colors.ENDC}")
            return
        
        print(f"{Colors.GREEN}✅ Učitano {len(links)} linkova{Colors.ENDC}")
        
        for i, link in enumerate(links, 1):
            print(f"\n{Colors.YELLOW}[{i}/{len(links)}] {link}{Colors.ENDC}")
            
            try:
                await self.backup_current_chat(link)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"{Colors.RED}❌ Greška: {e}{Colors.ENDC}")
    
    async def interactive_menu(self):
        """Interaktivni meni"""
        while True:
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}🤖 Gemini Chat Backup Tool{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"  [1] 📝 Unesi linkove ručno")
            print(f"  [2] 📚 Auto-Sidebar Backup (svi chatovi)")
            print(f"  [3] 📄 Backup trenutnog chata")
            print(f"  [4] ⚙️  Postavke")
            print(f"  [5] 🚪 Izlaz")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
            
            choice = input(f"{Colors.CYAN}Odaberite opciju: {Colors.ENDC}").strip()
            
            if choice == '1':
                links_input = input(f"{Colors.CYAN}Unesite linkove (odvojene zarezom): {Colors.ENDC}")
                links = [l.strip() for l in links_input.split(',') if l.strip()]
                
                for i, link in enumerate(links, 1):
                    print(f"\n{Colors.YELLOW}[{i}/{len(links)}]{Colors.ENDC}")
                    try:
                        await self.backup_current_chat(link)
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"{Colors.RED}❌ Greška: {e}{Colors.ENDC}")
            
            elif choice == '2':
                await self.auto_sidebar_backup()
            
            elif choice == '3':
                await self.backup_current_chat()
            
            elif choice == '4':
                await self.settings_menu()
            
            elif choice == '5':
                print(f"{Colors.GREEN}👋 Doviđenja!{Colors.ENDC}")
                break
            
            else:
                print(f"{Colors.RED}❌ Nevažeća opcija{Colors.ENDC}")
    
    async def settings_menu(self):
        """Izbornik postavki"""
        print(f"\n{Colors.HEADER}⚙️  Postavke{Colors.ENDC}")
        print(f"  [1] Promijeni preglednik")
        print(f"  [2] Pokaži trenutnu konfiguraciju")
        print(f"  [3] Natrag")
        
        choice = input(f"{Colors.CYAN}Odaberite: {Colors.ENDC}").strip()
        
        if choice == '1':
            self.config["active_browser"] = None
            self.save_config()
            await self.interactive_setup()
        elif choice == '2':
            print(json.dumps(self.config, indent=2, ensure_ascii=False))
    
    async def cleanup(self):
        """Počisti resurse"""
        if self.browser_context:
            await self.browser_context.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        print(f"{Colors.GREEN}✅ Resursi oslobođeni{Colors.ENDC}")


async def main():
    """Glavna funkcija"""
    tool = GeminiBackupTool()
    
    # Provjeri argumente komandne linije
    if len(sys.argv) > 1:
        # Drag & Drop mod - primljen file path
        file_path = sys.argv[1]
        
        if not tool.config.get("active_browser"):
            await tool.interactive_setup()
        
        await tool.launch_browser(headless=False)
        await tool.navigate_to_gemini()
        await tool.process_links_file(file_path)
        await tool.cleanup()
    
    else:
        # Interaktivni mod
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}🚀 Gemini Chat Backup Tool v2.0{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        # Provjeri konfiguraciju
        if not tool.config.get("active_browser"):
            await tool.interactive_setup()
        
        try:
            await tool.launch_browser(headless=False)
            await tool.navigate_to_gemini()
            await tool.interactive_menu()
        except Exception as e:
            print(f"{Colors.RED}❌ Fatalna greška: {e}{Colors.ENDC}")
        finally:
            await tool.cleanup()
        
        input(f"\n{Colors.CYAN}Pritisnite Enter za izlaz...{Colors.ENDC}")


if __name__ == "__main__":
    asyncio.run(main())
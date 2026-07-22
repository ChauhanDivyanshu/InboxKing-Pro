"""
InboxKing PRO - AUTO LOGIN VERSION
Handles 400 accounts automatically
"""
import asyncio
import random
import time
import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from io import StringIO
from playwright.async_api import async_playwright
from colorama import init, Fore, Style

init(autoreset=True)

BASE_DIR = Path(__file__).parent
PROFILES_DIR = BASE_DIR / "profiles"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
PROFILES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============ SETTINGS ============
DAILY_LIMIT_PER_ACCOUNT = 30
DELAY_MIN = 90
DELAY_MAX = 240
BREAK_AFTER_EMAILS = 8
BREAK_MIN_MINUTES = 5
BREAK_MAX_MINUTES = 15
LOGIN_WAIT_TIMEOUT = 60  # Wait 60 sec for CAPTCHA/2FA

# ============ CONTENT ============
SUBJECTS = [
    "Quick question, {name}",
    "{name}, thoughts?",
    "Regarding {company}",
    "For {name} at {company}",
    "{company} - quick note",
    "Reaching out about {company}",
    "Hey {name}, quick question",
    "Noticed {company}",
    "Wanted to connect, {name}",
    "{name}, saw {company}",
    "Thought about {company}",
    "{name}, hope this finds you well",
    "Small suggestion for {company}",
    "Quick thought on {company}",
]

GREETINGS = ["Hi {name},", "Hello {name},", "Hey {name},", "Hi there {name},", "{name},"]

OPENERS = [
    "Hope you are doing well.",
    "Hope your week is going great.",
    "Hope this email finds you well.",
    "Trust you are having a good week.",
    "Hope things are going smoothly at {company}.",
]

CONTEXT_LINES = [
    "I was researching businesses in your industry and came across {company}.",
    "I came across {company} while exploring companies in your space.",
    "Was browsing through some websites earlier and {company} caught my eye.",
    "Recently discovered {company} online and wanted to reach out.",
    "Came across {company} while looking at businesses in your niche.",
]

VALUE_PROPS = [
    "Had a quick thought about your online presence that might be worth exploring.",
    "Noticed a few things that could be improved with some quick fixes.",
    "Wanted to share an observation that might help your growth.",
    "Had some ideas that could add value to what you are doing.",
    "Saw some opportunities that might interest you.",
]

CTAS = [
    "Would you be open to a brief chat this week?",
    "Do you have 10 minutes this week to discuss?",
    "Would love to share more if you are interested.",
    "Happy to send over some details if it helps.",
    "Let me know if you would like to hear more.",
]

SIGNOFFS = ["Best,", "Regards,", "Thanks,", "Cheers,", "Best regards,", "Take care,"]
PS_LINES = ["", "\n\nP.S. If not relevant, no worries at all.", "\n\nP.S. Feel free to ignore.", ""]


class Logger:
    @staticmethod
    def info(msg): print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")
    @staticmethod
    def success(msg): print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")
    @staticmethod
    def warning(msg): print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")
    @staticmethod
    def error(msg): print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")
    @staticmethod
    def sent(msg): print(f"{Fore.GREEN}[SENT]{Style.RESET_ALL} {msg}")
    @staticmethod
    def action(msg): print(f"{Fore.MAGENTA}[ACTION]{Style.RESET_ALL} {msg}")


class ContentGenerator:
    @staticmethod
    def generate_subject(name, company):
        return random.choice(SUBJECTS).format(name=name, company=company)
    
    @staticmethod
    def generate_body(name, company):
        greeting = random.choice(GREETINGS).format(name=name)
        opener = random.choice(OPENERS).format(company=company)
        context = random.choice(CONTEXT_LINES).format(company=company)
        value = random.choice(VALUE_PROPS)
        cta = random.choice(CTAS)
        signoff = random.choice(SIGNOFFS)
        ps = random.choice(PS_LINES)
        return f"{greeting}\n\n{opener}\n\n{context} {value}\n\n{cta}\n\n{signoff}\nTeam{ps}"


class HumanBehavior:
    @staticmethod
    async def delay(min_sec=1, max_sec=3):
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    async def type_slow(page, text):
        for char in text:
            await page.keyboard.type(char)
            if char in '.,!?': await asyncio.sleep(random.uniform(0.12, 0.30))
            elif char == ' ': await asyncio.sleep(random.uniform(0.05, 0.15))
            else: await asyncio.sleep(random.uniform(0.03, 0.10))
    
    @staticmethod
    async def random_mouse(page):
        try:
            for _ in range(random.randint(2, 4)):
                await page.mouse.move(random.randint(200, 1200), random.randint(200, 600), steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except: pass


def load_csv(filepath):
    """Load CSV with multiple encoding fallbacks"""
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except: continue
    return None


class AccountManager:
    
    def __init__(self):
        self.accounts_file = DATA_DIR / "accounts.csv"
        self.accounts = self.load_accounts()
    
    def load_accounts(self):
        if not self.accounts_file.exists():
            Logger.error(f"File not found: {self.accounts_file}")
            sys.exit(1)
        
        content = load_csv(self.accounts_file)
        if not content:
            Logger.error("Cannot read accounts.csv")
            sys.exit(1)
        
        accounts = []
        reader = csv.DictReader(StringIO(content))
        
        for row in reader:
            cleaned = {k.strip().lower().lstrip('\ufeff'): v for k, v in row.items() if k}
            email = cleaned.get('email', '').strip()
            status = cleaned.get('status', 'active').strip().lower()
            
            if email and '@' in email and status == 'active':
                accounts.append({
                    'email': email,
                    'password': cleaned.get('password', '').strip(),
                    'daily_sent': int(cleaned.get('daily_sent', '0') or '0'),
                    'warmup_score': int(cleaned.get('warmup_score', '50') or '50'),
                    'login_failed': False,
                })
        
        Logger.success(f"Loaded {len(accounts)} accounts")
        return accounts
    
    def get_next_account(self):
        available = [a for a in self.accounts 
                    if a['daily_sent'] < DAILY_LIMIT_PER_ACCOUNT 
                    and not a['login_failed']]
        if not available: return None
        available.sort(key=lambda x: x['daily_sent'])
        return available[0]
    
    def mark_login_failed(self, email):
        for acc in self.accounts:
            if acc['email'] == email:
                acc['login_failed'] = True
                break
    
    def update_sent(self, email):
        for acc in self.accounts:
            if acc['email'] == email:
                acc['daily_sent'] += 1
                break
        self.save_accounts()
    
    def save_accounts(self):
        with open(self.accounts_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['email', 'password', 'status', 'daily_sent', 'warmup_score', 'last_used'])
            writer.writeheader()
            for acc in self.accounts:
                writer.writerow({
                    'email': acc['email'],
                    'password': acc['password'],
                    'status': 'active',
                    'daily_sent': acc['daily_sent'],
                    'warmup_score': acc['warmup_score'],
                    'last_used': datetime.now().isoformat(),
                })


class GmailAutomation:
    
    def __init__(self, account):
        self.account = account
        self.email = account['email']
        self.password = account['password']
        self.profile_path = PROFILES_DIR / self.email.replace('@', '_at_')
        self.profile_path.mkdir(exist_ok=True)
        self.behavior = HumanBehavior()
        self.browser = None
        self.page = None
        self.playwright = None
    
    async def launch(self):
        try:
            self.playwright = await async_playwright().start()
            
            viewports = [{'width': 1366, 'height': 768}, {'width': 1440, 'height': 900}, {'width': 1920, 'height': 1080}]
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            ]
            
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_path),
                headless=False,
                viewport=random.choice(viewports),
                user_agent=random.choice(user_agents),
                locale='en-US',
                timezone_id='America/New_York',
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            await self.browser.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                window.chrome = { runtime: {} };
            """)
            
            self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
            return True
        except Exception as e:
            Logger.error(f"Launch error: {e}")
            return False
    
    async def is_logged_in(self):
        """Check if we're on Gmail inbox"""
        try:
            url = self.page.url
            if 'mail.google.com/mail' in url and 'signin' not in url and 'accounts.google.com' not in url:
                # Verify Compose button is present
                try:
                    await self.page.wait_for_selector('div[gh="cm"]', timeout=5000)
                    return True
                except:
                    return False
            return False
        except:
            return False
    
    async def auto_login(self):
        """Automatically login using email + password"""
        try:
            Logger.info(f"Auto-login: {self.email}")
            
            # Go to Gmail
            await self.page.goto('https://mail.google.com', wait_until='domcontentloaded', timeout=45000)
            await self.behavior.delay(3, 5)
            
            # Check if already logged in
            if await self.is_logged_in():
                Logger.success("Already logged in (session saved)")
                return True
            
            # Wait for either sign-in page or inbox
            await asyncio.sleep(3)
            current_url = self.page.url
            
            # If not on sign-in page, navigate there
            if 'accounts.google.com' not in current_url and 'signin' not in current_url:
                await self.page.goto('https://accounts.google.com/signin/v2/identifier?service=mail', 
                                     wait_until='domcontentloaded', timeout=30000)
                await self.behavior.delay(2, 4)
            
            # Step 1: Enter email
            Logger.info("Entering email...")
            try:
                email_input = await self.page.wait_for_selector('input[type="email"]', timeout=15000)
                await email_input.click()
                await self.behavior.delay(0.5, 1)
                await self.behavior.type_slow(self.page, self.email)
                await self.behavior.delay(1, 2)
                
                # Click Next
                next_btn = await self.page.wait_for_selector('#identifierNext button, button:has-text("Next")', timeout=5000)
                await next_btn.click()
                await self.behavior.delay(3, 5)
            except Exception as e:
                Logger.warning(f"Email input step: {e}")
            
            # Step 2: Enter password
            Logger.info("Entering password...")
            try:
                pwd_input = await self.page.wait_for_selector('input[type="password"]', timeout=15000)
                await pwd_input.click()
                await self.behavior.delay(0.5, 1.5)
                await self.behavior.type_slow(self.page, self.password)
                await self.behavior.delay(1, 2)
                
                # Click Next
                pwd_next = await self.page.wait_for_selector('#passwordNext button, button:has-text("Next")', timeout=5000)
                await pwd_next.click()
                await self.behavior.delay(5, 8)
            except Exception as e:
                Logger.warning(f"Password step: {e}")
            
            # Step 3: Handle challenges (2FA, CAPTCHA, phone verify)
            await asyncio.sleep(5)
            
            for attempt in range(6):  # Wait up to 60 seconds total
                if await self.is_logged_in():
                    Logger.success(f"Login successful!")
                    return True
                
                current_url = self.page.url
                
                # Check for common challenges
                if 'challenge' in current_url or 'signin/v2/challenge' in current_url:
                    Logger.warning("=" * 70)
                    Logger.action(f"CHALLENGE DETECTED for {self.email}")
                    Logger.action("Complete verification in browser (2FA/CAPTCHA/Phone)")
                    Logger.action(f"You have {LOGIN_WAIT_TIMEOUT} seconds...")
                    Logger.warning("=" * 70)
                    
                    # Wait up to 60 seconds for user to solve
                    for _ in range(LOGIN_WAIT_TIMEOUT):
                        await asyncio.sleep(1)
                        if await self.is_logged_in():
                            Logger.success("Challenge solved! Logged in")
                            return True
                    
                    Logger.error("Challenge timeout")
                    return False
                
                await asyncio.sleep(10)
            
            # Final check
            if await self.is_logged_in():
                Logger.success("Login successful!")
                return True
            
            Logger.error(f"Login failed: {self.email}")
            return False
            
        except Exception as e:
            Logger.error(f"Auto-login error: {e}")
            return False
    
    async def send_email(self, recipient_email, subject, body):
        try:
            await self.page.click('div[gh="cm"]', timeout=15000)
            await self.behavior.delay(2, 4)
            
            to_selectors = ['input[peoplekit-id="BbVjBd"]', 'textarea[name="to"]', 'input[aria-label="To recipients"]']
            to_element = None
            for sel in to_selectors:
                try:
                    to_element = await self.page.wait_for_selector(sel, timeout=3000)
                    if to_element: break
                except: continue
            
            if not to_element: raise Exception("TO field not found")
            
            await to_element.click()
            await self.behavior.delay(0.5, 1.2)
            await self.behavior.type_slow(self.page, recipient_email)
            await self.behavior.delay(1, 2)
            await self.page.keyboard.press('Tab')
            await self.behavior.delay(1, 2)
            
            await self.page.click('input[name="subjectbox"]')
            await self.behavior.delay(0.3, 0.8)
            await self.behavior.type_slow(self.page, subject)
            await self.behavior.delay(1, 2)
            
            await self.page.click('div[aria-label="Message Body"]')
            await self.behavior.delay(0.5, 1.2)
            
            for line in body.split('\n'):
                if line.strip():
                    await self.behavior.type_slow(self.page, line)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await self.behavior.delay(2, 4)
            await self.behavior.random_mouse(self.page)
            await self.page.keyboard.press('Control+Enter')
            await self.behavior.delay(4, 7)
            
            return {'success': True}
        except Exception as e:
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(1)
                await self.page.keyboard.press('Escape')
            except: pass
            return {'success': False, 'error': str(e)}
    
    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass


class CampaignManager:
    
    def __init__(self):
        self.account_mgr = AccountManager()
        self.recipients = self.load_recipients()
        self.results = {'sent': 0, 'failed': 0, 'login_failed': 0, 'total': 0}
    
    def load_recipients(self):
        recipients_file = DATA_DIR / "recipients.csv"
        if not recipients_file.exists():
            Logger.error("recipients.csv not found")
            sys.exit(1)
        
        content = load_csv(recipients_file)
        if not content:
            Logger.error("Cannot read recipients.csv")
            sys.exit(1)
        
        recipients = []
        reader = csv.DictReader(StringIO(content))
        
        for row in reader:
            cleaned = {k.strip().lower().lstrip('\ufeff'): v for k, v in row.items() if k}
            email = cleaned.get('email', '').strip()
            if email and '@' in email:
                recipients.append({
                    'email': email,
                    'first_name': cleaned.get('first_name', 'there').strip() or 'there',
                    'company': cleaned.get('company', 'your business').strip() or 'your business',
                })
        
        Logger.success(f"Loaded {len(recipients)} recipients")
        return recipients
    
    async def run(self):
        max_sendable = len(self.account_mgr.accounts) * DAILY_LIMIT_PER_ACCOUNT
        self.results['total'] = min(len(self.recipients), max_sendable)
        
        Logger.info(f"Accounts: {len(self.account_mgr.accounts)}")
        Logger.info(f"Recipients: {len(self.recipients)}")
        Logger.info(f"Target: {self.results['total']}")
        
        recipient_index = 0
        
        while recipient_index < len(self.recipients):
            account = self.account_mgr.get_next_account()
            if not account:
                Logger.warning("No more active accounts")
                break
            
            print("\n" + "="*70)
            Logger.info(f"Account: {account['email']}")
            Logger.info(f"Sent: {account['daily_sent']}/{DAILY_LIMIT_PER_ACCOUNT}")
            print("="*70)
            
            remaining = DAILY_LIMIT_PER_ACCOUNT - account['daily_sent']
            batch_size = min(remaining, random.randint(5, 10), len(self.recipients) - recipient_index)
            batch = self.recipients[recipient_index:recipient_index + batch_size]
            
            if not batch: break
            
            automation = GmailAutomation(account)
            
            if not await automation.launch():
                await automation.close()
                self.account_mgr.mark_login_failed(account['email'])
                self.results['login_failed'] += 1
                continue
            
            # AUTO LOGIN
            if not await automation.auto_login():
                Logger.error(f"Skipping account: {account['email']}")
                await automation.close()
                self.account_mgr.mark_login_failed(account['email'])
                self.results['login_failed'] += 1
                continue
            
            # Send emails
            for i, recipient in enumerate(batch):
                num = recipient_index + i + 1
                Logger.info(f"\n[{num}/{self.results['total']}] To: {recipient['email']}")
                
                subject = ContentGenerator.generate_subject(recipient['first_name'], recipient['company'])
                body = ContentGenerator.generate_body(recipient['first_name'], recipient['company'])
                
                Logger.info(f"Subject: {subject}")
                
                result = await automation.send_email(recipient['email'], subject, body)
                
                if result['success']:
                    Logger.sent(recipient['email'])
                    self.results['sent'] += 1
                    self.account_mgr.update_sent(account['email'])
                    account['daily_sent'] += 1
                else:
                    Logger.error(f"Send failed: {result.get('error', 'Unknown')[:100]}")
                    self.results['failed'] += 1
                
                if i < len(batch) - 1:
                    delay = random.uniform(DELAY_MIN, DELAY_MAX)
                    mins, secs = divmod(int(delay), 60)
                    Logger.info(f"Wait: {mins}m {secs}s")
                    await asyncio.sleep(delay)
            
            recipient_index += len(batch)
            await automation.close()
            
            if recipient_index < len(self.recipients):
                bt = random.uniform(BREAK_MIN_MINUTES * 60, BREAK_MAX_MINUTES * 60)
                Logger.warning(f"\nBREAK: {int(bt/60)} min\n")
                await asyncio.sleep(bt)
        
        log_file = LOGS_DIR / f"campaign_{int(time.time())}.json"
        with open(log_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\n" + "="*70)
        print("                CAMPAIGN COMPLETE")
        print("="*70)
        Logger.success(f"Sent: {self.results['sent']}")
        Logger.error(f"Send failures: {self.results['failed']}")
        Logger.warning(f"Login failures: {self.results['login_failed']}")
        if self.results['total']:
            Logger.info(f"Success rate: {(self.results['sent']/self.results['total'])*100:.1f}%")


async def main():
    print("\n" + "="*70)
    print("     InboxKing PRO - AUTO LOGIN VERSION")
    print("     Handles multiple Gmail accounts automatically")
    print("="*70)
    
    if not (DATA_DIR / "accounts.csv").exists():
        Logger.error("data/accounts.csv missing!")
        return
    
    if not (DATA_DIR / "recipients.csv").exists():
        Logger.error("data/recipients.csv missing!")
        return
    
    manager = CampaignManager()
    
    if not manager.account_mgr.accounts:
        Logger.error("No active accounts")
        return
    
    if not manager.recipients:
        Logger.error("No recipients")
        return
    
    print(f"\nAccounts: {len(manager.account_mgr.accounts)}")
    print(f"Recipients: {len(manager.recipients)}")
    print(f"Daily limit: {DAILY_LIMIT_PER_ACCOUNT} per account")
    print(f"Delay: {DELAY_MIN}-{DELAY_MAX} sec between emails")
    print(f"\nNote: Auto-login will try to sign in automatically.")
    print(f"      If CAPTCHA/2FA appears, you have {LOGIN_WAIT_TIMEOUT} seconds to solve.")
    
    confirm = input(f"\n>>> Start campaign? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    await manager.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")

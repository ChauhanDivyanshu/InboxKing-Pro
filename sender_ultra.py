"""
InboxKing PRO - ULTRA FAST VERSION
- Higher daily limits
- Faster delays
- More parallel accounts
- Better error handling
"""
import smtplib
import ssl
import random
import time
import json
import csv
import sys
import threading
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid, formatdate
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style

init(autoreset=True)

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR.mkdir(exist_ok=True)

# ============ ULTRA FAST SETTINGS ============
DAILY_LIMIT_PER_ACCOUNT = 15   # Increased from 30
DELAY_MIN = 10                  # Reduced from 25
DELAY_MAX = 25                  # Reduced from 60
PARALLEL_ACCOUNTS = 3          # Increased from 5
BATCH_SIZE_MIN = 5              # Increased
BATCH_SIZE_MAX = 15             # Increased
BREAK_MIN_SECONDS = 30          # Reduced from 2 min
BREAK_MAX_SECONDS = 90          # Reduced from 5 min

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587


# ============ CONTENT ============
SUBJECT_TEMPLATES = [
    "Quick question about {company}",
    "{name}, thought you might find this useful",
    "For {name} at {company}",
    "{company} - noticed something",
    "{name}, quick thought",
    "Something about {company}",
    "{name}, brief question",
    "Regarding {company}'s online presence",
    "{name}, hope this reaches you",
    "Wanted to reach out, {name}",
    "Hey {name}",
    "{name}, hope you are well",
    "Hi {name}, quick note",
    "Small observation about {company}",
    "{name}, mind if I share something?",
    "Idea for {company}",
    "{name}, saw {company} online",
    "{company} - question for you",
    "{name}, checking in",
    "About {company}",
]

GREETINGS = ["Hi {name},", "Hello {name},", "Hey {name},", "Hi there {name},", "{name},", "Hey there {name},", "Dear {name},"]

OPENING_LINES = [
    "Hope you are doing well.",
    "Hope your week is going smoothly.",
    "Hope this finds you at a good time.",
    "Hope things are going great at {company}.",
    "Hope you are having a productive week.",
    "Trust everything is going well on your end.",
    "Hope business is treating you well.",
    "Hope you are having a good day.",
]

CONTEXT_LINES = [
    "I came across {company} while researching businesses in your space.",
    "I was exploring companies like yours and {company} stood out.",
    "Recently discovered {company} online and wanted to reach out.",
    "Came across your business while looking into similar companies.",
    "Was browsing through businesses in your industry and noticed {company}.",
    "Ive been looking at companies like {company} and had a quick thought.",
    "Found {company} while doing some research and wanted to connect.",
    "Been exploring the industry lately and came across {company}.",
]

OBSERVATION_LINES = [
    "Noticed something about your online visibility that might be worth a look.",
    "Had a small observation about how {company} appears online.",
    "Saw a few things about your web presence that caught my attention.",
    "Wanted to share an observation about your online presence.",
    "Had a quick thought about how your business shows up online.",
    "Noticed a few opportunities regarding your online visibility.",
    "Saw something interesting about {company}s digital footprint.",
    "Had a suggestion regarding your online presence.",
]

BENEFIT_LINES = [
    "Nothing urgent, just thought you might find it useful.",
    "Its a small thing, but could make a real difference.",
    "Quick fix that most businesses miss.",
    "Something simple that often gets overlooked.",
    "A minor tweak that could add real value.",
    "Small improvement that could have a big impact.",
    "Just a friendly heads up.",
    "Thought it might be worth exploring.",
]

CTA_LINES = [
    "Would you be open to a brief 10-minute chat this week?",
    "Do you have a few minutes this week to discuss?",
    "Happy to share more details if you are interested.",
    "Let me know if you would like to hear more.",
    "Would love to share what I found - open to a quick call?",
    "Want me to send over what I noticed?",
    "Feel free to reply if you would like more details.",
    "Interested in a brief conversation about this?",
]

SIGNOFFS = ["Best,", "Regards,", "Thanks,", "Cheers,", "Best regards,", "Take care,", "Kind regards,", "All the best,", "Warm regards,"]

PS_LINES = [
    "",
    "\n\nP.S. If this isnt relevant, feel free to ignore.",
    "\n\nP.S. No pressure - just wanted to reach out.",
    "\n\nP.S. Happy to chat whenever works for you.",
    "",
    "",
    "\n\nP.S. Not selling anything, just genuinely reaching out.",
]

SENDER_NAMES = ["Smriti", "Rahul", "Priya", "Amit", "Neha", "Vikash", "Anjali", "Rohit", "Kavya", "Arjun", "Sneha", "Karan", "Divya", "Manish", "Pooja"]


class Logger:
    _lock = threading.Lock()
    
    @staticmethod
    def _log(msg, color):
        with Logger._lock:
            print(f"{color}{msg}{Style.RESET_ALL}")
    
    @staticmethod
    def info(msg): Logger._log(f"[INFO] {msg}", Fore.CYAN)
    @staticmethod
    def success(msg): Logger._log(f"[SUCCESS] {msg}", Fore.GREEN)
    @staticmethod
    def warning(msg): Logger._log(f"[WARN] {msg}", Fore.YELLOW)
    @staticmethod
    def error(msg): Logger._log(f"[ERROR] {msg}", Fore.RED)
    @staticmethod
    def sent(acc, to, num, total): Logger._log(f"[SENT {num}/{total}] {acc[:25]:25s} -> {to}", Fore.GREEN)
    @staticmethod
    def account(msg): Logger._log(f"[ACCOUNT] {msg}", Fore.MAGENTA)


class ContentSpinner:
    @staticmethod
    def spin_subject(name, company):
        template = random.choice(SUBJECT_TEMPLATES)
        subject = template.format(name=name, company=company)
        variation = random.random()
        if variation < 0.15: subject += "?"
        elif variation < 0.20: subject += "."
        return subject
    
    @staticmethod
    def spin_body(name, company, sender_name):
        greeting = random.choice(GREETINGS).format(name=name)
        opening = random.choice(OPENING_LINES).format(company=company)
        context = random.choice(CONTEXT_LINES).format(company=company)
        observation = random.choice(OBSERVATION_LINES).format(company=company)
        benefit = random.choice(BENEFIT_LINES)
        cta = random.choice(CTA_LINES)
        signoff = random.choice(SIGNOFFS)
        ps = random.choice(PS_LINES)
        
        structure = random.choice([1, 2, 3, 4])
        
        if structure == 1:
            body = f"{greeting}\n\n{opening}\n\n{context}\n\n{observation} {benefit}\n\n{cta}\n\n{signoff}\n{sender_name}{ps}"
        elif structure == 2:
            body = f"{greeting}\n\n{context} {observation}\n\n{benefit}\n\n{cta}\n\n{signoff}\n{sender_name}{ps}"
        elif structure == 3:
            body = f"{greeting}\n\n{opening} {context}\n\n{observation}\n\n{cta}\n\n{signoff}\n{sender_name}{ps}"
        else:
            body = f"{greeting}\n\n{context}\n\n{observation}\n\n{benefit} {cta}\n\n{signoff}\n{sender_name}{ps}"
        
        return body


def load_csv(filepath):
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except: continue
    return None


class SMTPSender:
    def __init__(self, email, app_password):
        self.email = email
        self.password = app_password
        self.server = None
    
    def connect(self, retries=2):
        for attempt in range(retries):
            try:
                context = ssl.create_default_context()
                self.server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
                self.server.ehlo()
                self.server.starttls(context=context)
                self.server.ehlo()
                self.server.login(self.email, self.password)
                return True
            except smtplib.SMTPAuthenticationError:
                Logger.error(f"Auth failed: {self.email}")
                return False
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                Logger.error(f"Connect error {self.email}: {str(e)[:60]}")
                return False
        return False
    
    def send(self, to_email, subject, body, sender_name):
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((sender_name, self.email))
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.email
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain=self.email.split('@')[1])
            msg['X-Mailer'] = 'Gmail'
            msg['MIME-Version'] = '1.0'
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            html_body = body.replace('\n\n', '</p><p>').replace('\n', '<br>')
            html = f"""<html><head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, sans-serif; font-size: 14px; color: #202124; line-height: 1.5;">
<p>{html_body}</p></body></html>"""
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            self.server.send_message(msg)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def disconnect(self):
        try:
            if self.server: self.server.quit()
        except: pass


class AccountManager:
    def __init__(self):
        self.accounts_file = DATA_DIR / "accounts.csv"
        self.accounts = self.load_accounts()
        self.lock = threading.Lock()
    
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
                    'password': cleaned.get('password', '').strip().replace(' ', ''),
                    'daily_sent': int(cleaned.get('daily_sent', '0') or '0'),
                    'warmup_score': int(cleaned.get('warmup_score', '50') or '50'),
                    'auth_failed': False,
                    'sender_name': random.choice(SENDER_NAMES),
                })
        
        Logger.success(f"Loaded {len(accounts)} accounts")
        return accounts
    
    def get_available_accounts(self, count):
        with self.lock:
            available = [a for a in self.accounts 
                        if a['daily_sent'] < DAILY_LIMIT_PER_ACCOUNT 
                        and not a['auth_failed']]
            available.sort(key=lambda x: x['daily_sent'])
            return available[:count]
    
    def mark_auth_failed(self, email):
        with self.lock:
            for acc in self.accounts:
                if acc['email'] == email:
                    acc['auth_failed'] = True
                    break
    
    def update_sent(self, email):
        with self.lock:
            for acc in self.accounts:
                if acc['email'] == email:
                    acc['daily_sent'] += 1
                    break
    
    def get_total_capacity(self):
        return sum(DAILY_LIMIT_PER_ACCOUNT - a['daily_sent'] 
                   for a in self.accounts if not a['auth_failed'])
    
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


class CampaignManager:
    def __init__(self):
        self.account_mgr = AccountManager()
        self.recipients = self.load_recipients()
        self.results = {'sent': 0, 'failed': 0, 'auth_failed': 0, 'total': 0}
        self.results_lock = threading.Lock()
        self.stop_flag = threading.Event()
    
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
    
    def update_result(self, key):
        with self.results_lock:
            self.results[key] += 1
    
    def worker(self, account, batch):
        Logger.account(f"START: {account['email']} ({len(batch)} emails)")
        
        sender = SMTPSender(account['email'], account['password'])
        
        if not sender.connect():
            self.account_mgr.mark_auth_failed(account['email'])
            self.update_result('auth_failed')
            return
        
        sender_name = account['sender_name']
        
        for i, recipient in enumerate(batch):
            if self.stop_flag.is_set():
                break
            
            # Check if daily limit hit
            if account['daily_sent'] >= DAILY_LIMIT_PER_ACCOUNT:
                Logger.warning(f"Daily limit reached: {account['email']}")
                break
            
            subject = ContentSpinner.spin_subject(recipient['first_name'], recipient['company'])
            body = ContentSpinner.spin_body(recipient['first_name'], recipient['company'], sender_name)
            
            result = sender.send(recipient['email'], subject, body, sender_name)
            
            if result['success']:
                self.account_mgr.update_sent(account['email'])
                account['daily_sent'] += 1
                self.update_result('sent')
                Logger.sent(account['email'], recipient['email'], self.results['sent'], self.results['total'])
            else:
                self.update_result('failed')
                Logger.error(f"Failed {recipient['email']}: {result.get('error', '')[:50]}")
            
            if i < len(batch) - 1:
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                time.sleep(delay)
        
        sender.disconnect()
        Logger.account(f"DONE: {account['email']} ({account['daily_sent']}/{DAILY_LIMIT_PER_ACCOUNT})")
    
    def run(self):
        # Calculate real capacity
        total_capacity = self.account_mgr.get_total_capacity()
        self.results['total'] = min(len(self.recipients), total_capacity)
        
        Logger.info(f"Accounts: {len(self.account_mgr.accounts)}")
        Logger.info(f"Recipients: {len(self.recipients)}")
        Logger.info(f"Total capacity: {total_capacity}")
        Logger.info(f"Will send: {self.results['total']}")
        Logger.info(f"Parallel accounts: {PARALLEL_ACCOUNTS}")
        print()
        
        if self.results['total'] == 0:
            Logger.error("No capacity! All accounts hit daily limit.")
            Logger.warning("Reset accounts: python -c \"import csv;...\"")
            return
        
        if len(self.recipients) > total_capacity:
            Logger.warning(f"Only {total_capacity} of {len(self.recipients)} will be sent (limited by accounts)")
            Logger.warning(f"Add more accounts or increase DAILY_LIMIT_PER_ACCOUNT")
        
        recipient_index = 0
        round_num = 1
        start_time = time.time()
        
        while recipient_index < len(self.recipients) and not self.stop_flag.is_set():
            print("\n" + "="*70)
            Logger.info(f"ROUND {round_num}")
            print("="*70)
            
            active_accounts = self.account_mgr.get_available_accounts(PARALLEL_ACCOUNTS)
            
            if not active_accounts:
                Logger.warning("All accounts hit daily limit")
                break
            
            # Distribute recipients across accounts
            batches = []
            for account in active_accounts:
                if recipient_index >= len(self.recipients):
                    break
                
                remaining_capacity = DAILY_LIMIT_PER_ACCOUNT - account['daily_sent']
                batch_size = min(
                    remaining_capacity,
                    random.randint(BATCH_SIZE_MIN, BATCH_SIZE_MAX),
                    len(self.recipients) - recipient_index
                )
                
                if batch_size > 0:
                    batch = self.recipients[recipient_index:recipient_index + batch_size]
                    batches.append((account, batch))
                    recipient_index += batch_size
            
            if not batches:
                break
            
            Logger.info(f"Running {len(batches)} accounts in PARALLEL...")
            
            with ThreadPoolExecutor(max_workers=len(batches)) as executor:
                futures = [executor.submit(self.worker, acc, batch) for acc, batch in batches]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        Logger.error(f"Worker error: {e}")
            
            self.account_mgr.save_accounts()
            
            elapsed = time.time() - start_time
            rate = self.results['sent'] / max(elapsed / 60, 0.1)
            Logger.info(f">>> Progress: {self.results['sent']}/{self.results['total']} | Rate: {rate:.1f} mails/min")
            
            round_num += 1
            
            if recipient_index < len(self.recipients):
                bt = random.uniform(BREAK_MIN_SECONDS, BREAK_MAX_SECONDS)
                Logger.warning(f"Short break: {int(bt)}s before next round...")
                time.sleep(bt)
        
        self.account_mgr.save_accounts()
        
        elapsed = time.time() - start_time
        log_file = LOGS_DIR / f"campaign_{int(time.time())}.json"
        with open(log_file, 'w') as f:
            json.dump({
                **self.results,
                'duration_seconds': elapsed,
                'duration_minutes': elapsed / 60,
                'rate_per_min': self.results['sent'] / max(elapsed / 60, 0.1)
            }, f, indent=2)
        
        print("\n" + "="*70)
        print("                    CAMPAIGN COMPLETE")
        print("="*70)
        Logger.success(f"Total sent: {self.results['sent']}")
        Logger.error(f"Send failures: {self.results['failed']}")
        Logger.warning(f"Auth failures: {self.results['auth_failed']}")
        Logger.info(f"Duration: {elapsed/60:.1f} min")
        Logger.info(f"Rate: {self.results['sent'] / max(elapsed / 60, 0.1):.1f} mails/min")
        if self.results['total']:
            Logger.info(f"Success rate: {(self.results['sent']/self.results['total'])*100:.1f}%")


def main():
    print("\n" + "="*70)
    print("     InboxKing PRO - ULTRA FAST VERSION")
    print(f"     {PARALLEL_ACCOUNTS} accounts parallel | {DAILY_LIMIT_PER_ACCOUNT} mails/account/day")
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
    
    total_capacity = manager.account_mgr.get_total_capacity()
    actual = min(len(manager.recipients), total_capacity)
    est_speed = PARALLEL_ACCOUNTS * (60 / ((DELAY_MIN + DELAY_MAX) / 2))
    est_time = actual / est_speed
    
    print(f"\nReady to send:")
    print(f"  Accounts: {len(manager.account_mgr.accounts)}")
    print(f"  Recipients: {len(manager.recipients)}")
    print(f"  Capacity: {total_capacity} emails")
    print(f"  Will send: {actual}")
    print(f"  Est. speed: ~{int(est_speed)} mails/min")
    print(f"  Est. time: ~{int(est_time)} minutes")
    
    if len(manager.recipients) > total_capacity:
        Logger.warning(f"\n>>> ONLY {total_capacity} of {len(manager.recipients)} can be sent!")
        Logger.warning(f">>> Add more accounts to send all {len(manager.recipients)} recipients")
    
    confirm = input(f"\n>>> Start? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    try:
        manager.run()
    except KeyboardInterrupt:
        Logger.warning("Stopping...")
        manager.stop_flag.set()
        manager.account_mgr.save_accounts()


if __name__ == "__main__":
    main()

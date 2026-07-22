"""
InboxKing SMTP Sender - REAL WORKING VERSION
Uses Gmail SMTP + App Passwords
Handles 400+ accounts easily
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
from io import StringIO
from colorama import init, Fore, Style

init(autoreset=True)

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR.mkdir(exist_ok=True)

# ============ SETTINGS ============
DAILY_LIMIT_PER_ACCOUNT = 50
DELAY_MIN = 30  # SMTP is faster, can reduce delay
DELAY_MAX = 90
BREAK_AFTER_EMAILS = 10
BREAK_MIN_MINUTES = 3
BREAK_MAX_MINUTES = 8

# SMTP settings
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587

# ============ CONTENT VARIATIONS ============
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
    "{name}, brief message",
]

GREETINGS = ["Hi {name},", "Hello {name},", "Hey {name},", "Hi there {name},", "{name},"]

OPENERS = [
    "Hope you are doing well.",
    "Hope your week is going great.",
    "Hope this email finds you well.",
    "Trust you are having a good week.",
    "Hope things are going smoothly at {company}.",
    "Hope you are having a productive week.",
]

CONTEXT_LINES = [
    "I was researching businesses in your industry and came across {company}.",
    "I came across {company} while exploring companies in your space.",
    "Was browsing through some websites earlier and {company} caught my eye.",
    "Recently discovered {company} online and wanted to reach out.",
    "Came across {company} while looking at businesses in your niche.",
    "Been exploring companies like {company} recently.",
]

VALUE_PROPS = [
    "Had a quick thought about your online presence that might be worth exploring.",
    "Noticed a few things that could be improved with some quick fixes.",
    "Wanted to share an observation that might help your growth.",
    "Had some ideas that could add value to what you are doing.",
    "Saw some opportunities that might interest you.",
    "Had a small suggestion that could make a difference.",
]

CTAS = [
    "Would you be open to a brief chat this week?",
    "Do you have 10 minutes this week to discuss?",
    "Would love to share more if you are interested.",
    "Happy to send over some details if it helps.",
    "Let me know if you would like to hear more.",
    "Open to a quick call to explore this?",
]

SIGNOFFS = ["Best,", "Regards,", "Thanks,", "Cheers,", "Best regards,", "Take care,"]
PS_LINES = ["", "\n\nP.S. If not relevant, no worries at all.", "\n\nP.S. Feel free to ignore if not applicable.", ""]


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
        
        # Multiple structures for variation
        structure = random.choice([1, 2, 3])
        
        if structure == 1:
            body = f"{greeting}\n\n{opener}\n\n{context} {value}\n\n{cta}\n\n{signoff}\nTeam{ps}"
        elif structure == 2:
            body = f"{greeting}\n\n{context}\n\n{value}\n\n{cta}\n\n{signoff}\nTeam{ps}"
        else:
            body = f"{greeting}\n\n{opener} {context}\n\n{value} {cta}\n\n{signoff}\nTeam{ps}"
        
        return body


def load_csv(filepath):
    """Load CSV with multiple encoding fallbacks"""
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
        self.password = app_password  # This is the 16-digit APP password
        self.server = None
    
    def connect(self):
        """Establish SMTP connection"""
        try:
            context = ssl.create_default_context()
            self.server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            self.server.ehlo()
            self.server.starttls(context=context)
            self.server.ehlo()
            self.server.login(self.email, self.password)
            return True
        except smtplib.SMTPAuthenticationError as e:
            Logger.error(f"Auth failed for {self.email}: Check app password")
            return False
        except Exception as e:
            Logger.error(f"Connection error for {self.email}: {e}")
            return False
    
    def send(self, to_email, subject, body, from_name="Team"):
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{from_name} <{self.email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.email
            
            # Plain text version
            msg.attach(MIMEText(body, 'plain'))
            
            # HTML version (Gmail prefers HTML)
            html_body = body.replace('\n', '<br>')
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                {html_body}
            </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))
            
            self.server.send_message(msg)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def disconnect(self):
        try:
            if self.server:
                self.server.quit()
        except: pass


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
                    'auth_failed': False,
                })
        
        Logger.success(f"Loaded {len(accounts)} accounts")
        return accounts
    
    def get_next_account(self):
        available = [a for a in self.accounts 
                    if a['daily_sent'] < DAILY_LIMIT_PER_ACCOUNT 
                    and not a['auth_failed']]
        if not available: return None
        available.sort(key=lambda x: x['daily_sent'])
        return available[0]
    
    def mark_auth_failed(self, email):
        for acc in self.accounts:
            if acc['email'] == email:
                acc['auth_failed'] = True
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


class CampaignManager:
    
    def __init__(self):
        self.account_mgr = AccountManager()
        self.recipients = self.load_recipients()
        self.results = {'sent': 0, 'failed': 0, 'auth_failed': 0, 'total': 0}
    
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
    
    def run(self):
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
            
            # Connect SMTP
            sender = SMTPSender(account['email'], account['password'])
            
            Logger.info("Connecting to Gmail SMTP...")
            if not sender.connect():
                Logger.error(f"SMTP auth failed. Skipping: {account['email']}")
                self.account_mgr.mark_auth_failed(account['email'])
                self.results['auth_failed'] += 1
                continue
            
            Logger.success("Connected to Gmail SMTP")
            
            # Calculate batch
            remaining = DAILY_LIMIT_PER_ACCOUNT - account['daily_sent']
            batch_size = min(remaining, random.randint(5, 10), len(self.recipients) - recipient_index)
            batch = self.recipients[recipient_index:recipient_index + batch_size]
            
            if not batch: 
                sender.disconnect()
                break
            
            # Send batch
            for i, recipient in enumerate(batch):
                num = recipient_index + i + 1
                Logger.info(f"\n[{num}/{self.results['total']}] To: {recipient['email']}")
                
                subject = ContentGenerator.generate_subject(recipient['first_name'], recipient['company'])
                body = ContentGenerator.generate_body(recipient['first_name'], recipient['company'])
                
                Logger.info(f"Subject: {subject}")
                
                result = sender.send(recipient['email'], subject, body)
                
                if result['success']:
                    Logger.sent(recipient['email'])
                    self.results['sent'] += 1
                    self.account_mgr.update_sent(account['email'])
                    account['daily_sent'] += 1
                else:
                    Logger.error(f"Send failed: {result.get('error', 'Unknown')[:100]}")
                    self.results['failed'] += 1
                
                # Delay between emails
                if i < len(batch) - 1:
                    delay = random.uniform(DELAY_MIN, DELAY_MAX)
                    mins, secs = divmod(int(delay), 60)
                    Logger.info(f"Wait: {mins}m {secs}s")
                    time.sleep(delay)
            
            recipient_index += len(batch)
            sender.disconnect()
            
            # Break before next account
            if recipient_index < len(self.recipients):
                bt = random.uniform(BREAK_MIN_MINUTES * 60, BREAK_MAX_MINUTES * 60)
                Logger.warning(f"\nBreak: {int(bt/60)} min before next account\n")
                time.sleep(bt)
        
        # Save log
        log_file = LOGS_DIR / f"campaign_{int(time.time())}.json"
        with open(log_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\n" + "="*70)
        print("                CAMPAIGN COMPLETE")
        print("="*70)
        Logger.success(f"Sent: {self.results['sent']}")
        Logger.error(f"Send failures: {self.results['failed']}")
        Logger.warning(f"Auth failures: {self.results['auth_failed']}")
        if self.results['total']:
            Logger.info(f"Success rate: {(self.results['sent']/self.results['total'])*100:.1f}%")


def main():
    print("\n" + "="*70)
    print("     InboxKing SMTP - Real Working Version")
    print("     Uses Gmail SMTP + App Passwords")
    print("     Handles 400+ accounts easily")
    print("="*70)
    print("\nIMPORTANT:")
    print("  1. Enable 2FA on each Gmail account")
    print("  2. Generate App Password (16 digits)")
    print("  3. Use App Password (NOT regular password) in accounts.csv")
    print("  4. Get App Password from: https://myaccount.google.com/apppasswords")
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
    
    print(f"\nReady to send:")
    print(f"  Accounts: {len(manager.account_mgr.accounts)}")
    print(f"  Recipients: {len(manager.recipients)}")
    print(f"  Daily limit per account: {DAILY_LIMIT_PER_ACCOUNT}")
    
    confirm = input(f"\n>>> Start campaign? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    manager.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")

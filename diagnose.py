"""
InboxKing Diagnostic Tool
Diagnoses WHY emails going to spam
"""
import smtplib
import ssl
import csv
import sys
import socket
import urllib.request
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid, formatdate
from io import StringIO
from colorama import init, Fore, Style

init(autoreset=True)

DATA_DIR = Path(__file__).parent / "data"


def load_csv(filepath):
    encodings = ['utf-8-sig', 'utf-8', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except: continue
    return None


def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode()
    except:
        return "Unknown"


def check_ip_blacklist(ip):
    """Check if IP is on major blacklists"""
    blacklists = [
        'zen.spamhaus.org',
        'bl.spamcop.net',
        'b.barracudacentral.org',
    ]
    
    listed_on = []
    reversed_ip = '.'.join(reversed(ip.split('.')))
    
    for bl in blacklists:
        try:
            socket.gethostbyname(f'{reversed_ip}.{bl}')
            listed_on.append(bl)
        except socket.gaierror:
            pass
        except:
            pass
    
    return listed_on


def test_send_simple(email, password):
    """Send SIMPLEST possible test email"""
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(email, password)
        
        # Simple test message
        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr(("Test", email))
        msg['To'] = email  # Send to self for testing
        msg['Subject'] = "Test Email"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='gmail.com')
        
        body = "Hi,\n\nThis is a test email.\n\nThanks"
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    print("\n" + "=" * 70)
    print("           InboxKing Diagnostic Tool")
    print("=" * 70)
    
    # Test 1: Check public IP
    print(f"\n{Fore.CYAN}[TEST 1] Checking Public IP...{Style.RESET_ALL}")
    ip = get_public_ip()
    print(f"Your Public IP: {ip}")
    
    # Test 2: Check IP blacklist
    print(f"\n{Fore.CYAN}[TEST 2] Checking IP Blacklists...{Style.RESET_ALL}")
    if ip != "Unknown":
        listed = check_ip_blacklist(ip)
        if listed:
            print(f"{Fore.RED}[FAIL] IP is BLACKLISTED on:{Style.RESET_ALL}")
            for bl in listed:
                print(f"  - {bl}")
            print(f"{Fore.YELLOW}[SOLUTION] Use mobile hotspot or VPN{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}[PASS] IP is clean{Style.RESET_ALL}")
    
    # Test 3: Load accounts
    print(f"\n{Fore.CYAN}[TEST 3] Checking Accounts...{Style.RESET_ALL}")
    accounts_file = DATA_DIR / "accounts.csv"
    if not accounts_file.exists():
        print(f"{Fore.RED}[FAIL] accounts.csv not found{Style.RESET_ALL}")
        return
    
    content = load_csv(accounts_file)
    accounts = []
    reader = csv.DictReader(StringIO(content))
    for row in reader:
        cleaned = {k.strip().lower().lstrip('\ufeff'): v for k, v in row.items() if k}
        email = cleaned.get('email', '').strip()
        password = cleaned.get('password', '').strip().replace(' ', '')
        if email and password:
            accounts.append({'email': email, 'password': password, 'daily_sent': int(cleaned.get('daily_sent', '0'))})
    
    print(f"Loaded {len(accounts)} accounts")
    
    # Test 4: Send test email to self
    print(f"\n{Fore.CYAN}[TEST 4] Sending TEST email to yourself...{Style.RESET_ALL}")
    if accounts:
        acc = accounts[0]
        print(f"Testing with: {acc['email']}")
        success, error = test_send_simple(acc['email'], acc['password'])
        if success:
            print(f"{Fore.GREEN}[PASS] Test email sent successfully{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[ACTION] Check {acc['email']} inbox NOW{Style.RESET_ALL}")
            print(f"  - Is it in Inbox? = Account is HEALTHY")
            print(f"  - Is it in Spam? = Account REPUTATION IS LOW")
        else:
            print(f"{Fore.RED}[FAIL] Cannot send: {error}{Style.RESET_ALL}")
    
    # Test 5: Account send counts
    print(f"\n{Fore.CYAN}[TEST 5] Account Activity Check...{Style.RESET_ALL}")
    for acc in accounts:
        status = ""
        if acc['daily_sent'] > 100:
            status = f"{Fore.RED}HEAVILY USED{Style.RESET_ALL}"
        elif acc['daily_sent'] > 50:
            status = f"{Fore.YELLOW}USED A LOT{Style.RESET_ALL}"
        elif acc['daily_sent'] > 20:
            status = f"{Fore.YELLOW}USED{Style.RESET_ALL}"
        else:
            status = f"{Fore.GREEN}FRESH{Style.RESET_ALL}"
        
        print(f"  {acc['email']} - Sent today: {acc['daily_sent']} [{status}]")
    
    # Summary
    print("\n" + "=" * 70)
    print("                   DIAGNOSIS SUMMARY")
    print("=" * 70)
    
    print(f"\n{Fore.YELLOW}COMMON REASONS FOR SPAM:{Style.RESET_ALL}")
    print("1. Sender account reputation is low (used too much recently)")
    print("2. Recipient Gmail accounts are related to sender")
    print("3. Content pattern detected by Gmail AI")
    print("4. IP reputation issue (home IP flagged)")
    print("5. Missing SPF/DKIM (unavoidable for @gmail.com)")
    
    print(f"\n{Fore.CYAN}RECOMMENDED ACTIONS:{Style.RESET_ALL}")
    print("1. Send to mail-tester.com to get score (target: 8+/10)")
    print("2. Use FRESH aged accounts (not overused ones)")
    print("3. Send to UNRELATED Gmail addresses (friends, not team)")
    print("4. Try mobile hotspot to test IP theory")
    print("5. Consider Custom Domain + Google Workspace")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

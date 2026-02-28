"""
send.py  —  Command-line tool to send an email from the agent account.

Usage:
  python3 send.py --to recipient@example.com --subject "System Health Check" --body "Please review and reply."

The sent message ID is automatically logged to sent_log.json so replies
will be matched and processed by agent.py.
"""

import argparse
import yaml
from pathlib import Path
from agent import send_email, load_yaml, CONFIG_PATH

def main():
    parser = argparse.ArgumentParser(description="Send an email from the agent account.")
    parser.add_argument("--to",      required=True,  help="Recipient email address")
    parser.add_argument("--subject", required=True,  help="Email subject (must match a key in tasks/mappings.yaml)")
    parser.add_argument("--body",    required=True,  help="Email body text")
    args = parser.parse_args()

    cfg = load_yaml(CONFIG_PATH)
    msg_id = send_email(cfg, args.to, args.subject, args.body)
    print(f"Sent! Message-ID: {msg_id}")

if __name__ == "__main__":
    main()

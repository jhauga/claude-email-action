"""
Email Agent - Send-only local email server with selective reply ingestion.
This script never needs to be modified. All configuration is in config.yaml
and task mappings are in tasks/mappings.yaml.
"""

import imaplib
import smtplib
import email
import json
import yaml
import re
import time
import logging
import subprocess
import importlib.util
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path

# -- Paths --------------------------------------------------------------------
BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
TASKS_PATH  = BASE_DIR / "tasks" / "mappings.yaml"
SENT_LOG    = BASE_DIR / "sent_log.json"
LOG_FILE    = BASE_DIR / "agent.log"

# -- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# -- Config loader -------------------------------------------------------------
def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# -- Sent log helpers ----------------------------------------------------------
def load_sent_log() -> dict:
    if SENT_LOG.exists():
        with open(SENT_LOG) as f:
            return json.load(f)
    return {}   # { message_id: { "subject": ..., "to": ..., "sent_at": ... } }


def save_sent_log(log_data: dict):
    with open(SENT_LOG, "w") as f:
        json.dump(log_data, f, indent=2)


def record_sent(message_id: str, subject: str, to: str):
    data = load_sent_log()
    data[message_id] = {
        "subject": subject,
        "to": to,
        "sent_at": datetime.utcnow().isoformat(),
    }
    save_sent_log(data)


# -- Subject cleaner -----------------------------------------------------------
# Strips RE:, Fwd:, AW:, SV:, etc. (any depth) and surrounding whitespace
_RE_PREFIX = re.compile(r'^(\s*(re|fwd?|aw|sv|antw|fw)\s*(\[\d+\])?\s*:\s*)+', re.IGNORECASE)

def clean_subject(raw: str) -> str:
    return _RE_PREFIX.sub("", raw).strip()


# -- Email sender --------------------------------------------------------------
def send_email(cfg: dict, to: str, subject: str, body: str) -> str:
    """Send an email and return the Message-ID."""
    smtp_cfg = cfg["smtp"]

    msg = MIMEMultipart()
    msg["From"]    = cfg["email"]["address"]
    msg["To"]      = to
    msg["Subject"] = subject

    # Generate a stable Message-ID
    domain = cfg["email"]["address"].split("@")[-1]
    msg_id = f"<{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}@{domain}>"
    msg["Message-ID"] = msg_id

    msg.attach(MIMEText(body, "plain"))

    use_ssl = smtp_cfg.get("use_ssl", False)
    port    = smtp_cfg.get("port", 587)

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_cfg["host"], port)
        else:
            server = smtplib.SMTP(smtp_cfg["host"], port)
            server.starttls()

        server.login(cfg["email"]["address"], cfg["email"]["password"])
        server.sendmail(cfg["email"]["address"], to, msg.as_string())
        server.quit()
        log.info(f"Email sent → {to} | Subject: {subject} | ID: {msg_id}")
        record_sent(msg_id, subject, to)
        return msg_id

    except Exception as e:
        log.error(f"Failed to send email: {e}")
        raise


# -- Reply parser --------------------------------------------------------------
def extract_json_payload(body: str) -> dict | None:
    """
    Finds and parses the JSON payload from the email body.
    Expects a block like:
        {"continue": "yes", "action": "some_action", "task": "some_task"}
    """
    # Try to find a JSON object in the body
    match = re.search(r'\{[^{}]+\}', body, re.DOTALL)
    if not match:
        return None
    try:
        raw = json.loads(match.group())
        # Normalize boolean-like string values
        cont = raw.get("continue", "no")
        if isinstance(cont, str):
            raw["continue"] = cont.strip().lower() == "yes"
        return raw
    except json.JSONDecodeError:
        return None


# -- Task dispatcher -----------------------------------------------------------
def dispatch(subject_clean: str, payload: dict, mappings: dict, cfg: dict):
    """
    Look up the clean subject in mappings.yaml and run the assigned handler.
    payload  = { "continue": bool, "action": str, "task": str }
    """
    if not payload.get("continue"):
        log.info(f"Payload says continue=false for '{subject_clean}'. Skipping.")
        return

    action = payload.get("action", "").strip()
    task   = payload.get("task",   "").strip()

    # Find matching subject mapping
    subject_map = mappings.get("subjects", {})
    entry = subject_map.get(subject_clean)

    if not entry:
        log.warning(f"No mapping found for subject: '{subject_clean}'")
        return

    log.info(f"Dispatching → subject='{subject_clean}' action='{action}' task='{task}'")

    # Each entry can define: action_handlers and/or task_handlers
    # action_handlers: map action values to commands/functions
    # task_handlers:   map task values to commands/functions

    _run_handler(entry.get("action_handlers", {}), action, payload, cfg, label="action")
    _run_handler(entry.get("task_handlers",   {}), task,   payload, cfg, label="task")


def _run_handler(handlers: dict, key: str, payload: dict, cfg: dict, label: str):
    if not handlers or not key:
        return

    handler = handlers.get(key)
    if not handler:
        log.warning(f"No {label} handler for value: '{key}'")
        return

    handler_type = handler.get("type")

    # -- shell: run a shell command --
    if handler_type == "shell":
        cmd = handler.get("command", "")
        log.info(f"Running shell command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        log.info(f"stdout: {result.stdout.strip()}")
        if result.returncode != 0:
            log.error(f"stderr: {result.stderr.strip()}")

    # -- python: call a function from an external .py file --
    elif handler_type == "python":
        module_path = Path(handler.get("module"))
        func_name   = handler.get("function")
        if not module_path.is_absolute():
            module_path = BASE_DIR / module_path

        spec   = importlib.util.spec_from_file_location("dynamic_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func = getattr(module, func_name)
        log.info(f"Calling {module_path}::{func_name}(payload)")
        func(payload)

    # -- email: send a follow-up email --
    elif handler_type == "email":
        to      = handler.get("to")
        subject = handler.get("subject", "Automated follow-up")
        body    = handler.get("body", "")
        send_email(cfg, to, subject, body)

    else:
        log.warning(f"Unknown handler type: '{handler_type}'")


# -- IMAP reply checker --------------------------------------------------------
def check_replies(cfg: dict, mappings: dict):
    imap_cfg  = cfg["imap"]
    sent_data = load_sent_log()

    if not sent_data:
        log.info("Sent log is empty — nothing to match replies against.")
        return

    try:
        mail = imaplib.IMAP4_SSL(imap_cfg["host"], imap_cfg.get("port", 993))
        mail.login(cfg["email"]["address"], cfg["email"]["password"])
        mail.select(imap_cfg.get("folder", "INBOX"))

        # Search for all unseen messages
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            log.info("No new emails.")
            mail.logout()
            return

        msg_ids = data[0].split()
        log.info(f"Found {len(msg_ids)} unseen email(s).")

        for num in msg_ids:
            status, msg_data = mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Check In-Reply-To / References headers
            in_reply_to = msg.get("In-Reply-To", "").strip()
            references  = msg.get("References",  "").strip()

            matched_id = None
            for sent_id in sent_data:
                if sent_id in in_reply_to or sent_id in references:
                    matched_id = sent_id
                    break

            if not matched_id:
                # Not a reply to anything we sent — leave it as UNSEEN, skip
                log.info(f"Skipping email — not a reply to any sent message.")
                mail.store(num, "-FLAGS", "\\Seen")   # restore unseen
                continue

            # -- It is a reply to something we sent --
            log.info(f"Matched reply to sent ID: {matched_id}")

            # Decode subject
            raw_subject = msg.get("Subject", "")
            decoded_parts = decode_header(raw_subject)
            subject_str = ""
            for part, enc in decoded_parts:
                if isinstance(part, bytes):
                    subject_str += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject_str += part
            subject_clean = clean_subject(subject_str)
            log.info(f"Clean subject: '{subject_clean}'")

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            # Parse JSON payload
            payload = extract_json_payload(body)
            if not payload:
                log.warning(f"No valid JSON payload found in reply body.")
                continue

            log.info(f"Payload: {payload}")
            dispatch(subject_clean, payload, mappings, cfg)

        mail.logout()

    except Exception as e:
        log.error(f"IMAP error: {e}")


# -- Main loop -----------------------------------------------------------------
def main():
    log.info("Email agent starting...")
    cfg      = load_yaml(CONFIG_PATH)
    interval = cfg.get("poll_interval_minutes", 20) * 60

    while True:
        try:
            mappings = load_yaml(TASKS_PATH)   # reload on each cycle — pick up edits
            check_replies(cfg, mappings)
        except Exception as e:
            log.error(f"Cycle error: {e}")

        log.info(f"Sleeping {interval // 60} minutes...")
        time.sleep(interval)


if __name__ == "__main__":
    main()

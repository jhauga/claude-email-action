# Claude Email Agent — Setup & Usage

## Overview

A local background email agent that:
- Sends emails via your CPanel SMTP account
- Polls for replies every 20 minutes (configurable)
- Only processes replies to emails **it** sent (matched via Message-ID headers)
- Strips RE:/Fwd: prefixes from subjects before lookup
- Reads a JSON payload from the reply body and routes to the correct handler
- All routing logic lives in YAML — the Python script never needs to change

---

## Directory Structure

```
email_agent/
├── agent.py            ← Never edit this
├── send.py             ← Repo CLI tool to send emails
├── config.yaml         ← Your credentials and poll interval
├── sent_log.json       ← Auto-created; tracks sent message IDs
├── agent.log           ← Auto-created; running log
├── tasks/
│   └── mappings.yaml   ← Edit this to add/change task mappings
└── handlers/
    ├── pipeline.py     ← Example handler module
    └── your_module.py  ← Add your own handler modules here
```

---

## Setup

### 1. Install dependencies

```bash
pip install pyyaml
```

### 2. Create a CPanel email account

In CPanel → Email Accounts, create something like `agent@yourdomain.com`.
Then go to **Connect Devices** to find your SMTP/IMAP host and ports.

### 3. Fill in config.yaml

```yaml
email:
  address: "agent@yourdomain.com"
  password: "your_password"
smtp:
  host: "mail.yourdomain.com"
  port: 587
  use_ssl: false
imap:
  host: "mail.yourdomain.com"
  port: 993
```

---

## Sending an Email

Use `send.py` to send a tracked email. The subject must match (or will be added to) `tasks/mappings.yaml`.

```bash
python3 send.py \
  --to "someone@example.com" \
  --subject "System Health Check" \
  --body "Please reply with your JSON directive."
```

The Message-ID is logged to `sent_log.json` automatically.

---

## Reply Format

The person (or system) replying should include a JSON block anywhere in the body:

```json
{"continue": "yes", "action": "run_diagnostics", "task": "backup_now"}
```

- `continue`: `"yes"` to proceed, `"no"` to skip all actions
- `action`: must match a key under `action_handlers` for that subject
- `task`: must match a key under `task_handlers` for that subject

---

## Adding a New Task Mapping

Open `tasks/mappings.yaml` and add:

```yaml
"Your Subject Here":
  action_handlers:
    do_something:
      type: shell
      command: "echo 'doing something'"
  task_handlers:
    run_report:
      type: python
      module: "handlers/my_module.py"
      function: "generate_report"
```

Handler types available:

| Type   | What it does |
|--------|-------------|
| shell  | Runs a shell command |
| python | Calls a function(payload) from a .py file |
| email  | Sends a follow-up email |

---

## Running the Agent

### Foreground (testing)

```bash
python3 agent.py
```

### Background (persistent)

```bash
nohup python3 agent.py &
```

### As a systemd service (recommended for always-on)

Create `/etc/systemd/system/email-agent.service`:

```ini
[Unit]
Description=Email Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/email_agent/agent.py
WorkingDirectory=/path/to/email_agent
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable email-agent
sudo systemctl start email-agent
```

---

## Notes

- `mappings.yaml` is reloaded every cycle — changes take effect immediately without restarting
- Emails that are NOT replies to sent messages are left as unread and untouched
- The agent never downloads or stores email content beyond what's needed to parse the payload

"""
Email Sender Bot
Syntecxhub Internship - Task 3, Project 3

Features:
  - Read recipients from CSV (name, email, custom fields)
  - Personalized message via template placeholders
  - Optional file attachments
  - Gmail SMTP with app password (secure, no plain password)
  - Retry logic (3 attempts per recipient)
  - Full send-status logging to file + console
  - CLI flags: --csv, --subject, --body, --attach, --dry-run
"""

import argparse
import csv
import logging
import os
import smtplib
import ssl
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_FILE = "email_sender.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465          # SSL port (use 587 + starttls for TLS)
MAX_RETRIES = 3
RETRY_DELAY = 5          # seconds between retries


# ── Core helpers ──────────────────────────────────────────────────────────────

def load_recipients(csv_path: str) -> list[dict]:
    """Return list of dicts from CSV. Required columns: name, email."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    recipients = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):          # row 1 = header
            name  = row.get("name", "").strip()
            email = row.get("email", "").strip()
            if not name or not email:
                log.warning("Row %d skipped — missing name or email.", i)
                continue
            if "@" not in email:
                log.warning("Row %d skipped — invalid email: %s", i, email)
                continue
            recipients.append(dict(row))   # keep all extra columns for templates
    log.info("Loaded %d valid recipient(s) from %s.", len(recipients), csv_path)
    return recipients


def personalize(template: str, data: dict) -> str:
    """Replace {key} placeholders with values from data dict."""
    try:
        return template.format_map(data)
    except KeyError as exc:
        log.warning("Template placeholder %s not found in CSV row — left as-is.", exc)
        # fall back: replace only known keys
        result = template
        for k, v in data.items():
            result = result.replace("{" + k + "}", v)
        return result


def build_message(
    sender: str,
    recipient: dict,
    subject_tpl: str,
    body_tpl: str,
    attachments: list[str],
) -> MIMEMultipart:
    """Compose a MIME email with optional attachments."""
    subject = personalize(subject_tpl, recipient)
    body    = personalize(body_tpl,    recipient)

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = recipient["email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for filepath in attachments:
        p = Path(filepath)
        if not p.exists():
            log.warning("Attachment not found, skipping: %s", filepath)
            continue
        with open(p, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{p.name}"',
        )
        msg.attach(part)
        log.debug("Attached: %s", p.name)

    return msg


def send_one(
    smtp: smtplib.SMTP_SSL,
    sender: str,
    recipient: dict,
    subject_tpl: str,
    body_tpl: str,
    attachments: list[str],
) -> bool:
    """Send to a single recipient. Returns True on success."""
    email = recipient["email"]
    name  = recipient.get("name", email)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = build_message(sender, recipient, subject_tpl, body_tpl, attachments)
            smtp.sendmail(sender, email, msg.as_string())
            log.info("✓ Sent  →  %s <%s>", name, email)
            return True
        except smtplib.SMTPRecipientsRefused:
            log.error("✗ Refused  →  %s <%s>  (invalid address)", name, email)
            return False          # no point retrying
        except Exception as exc:
            log.warning(
                "Attempt %d/%d failed for %s <%s>: %s",
                attempt, MAX_RETRIES, name, email, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    log.error("✗ Failed after %d attempts  →  %s <%s>", MAX_RETRIES, name, email)
    return False


def run(
    sender_email: str,
    app_password: str,
    csv_path: str,
    subject_tpl: str,
    body_tpl: str,
    attachments: list[str],
    dry_run: bool = False,
):
    recipients = load_recipients(csv_path)
    if not recipients:
        log.error("No valid recipients found. Aborting.")
        return

    sent = failed = skipped = 0

    if dry_run:
        log.info("── DRY RUN MODE — no emails will actually be sent ──")
        for r in recipients:
            subject = personalize(subject_tpl, r)
            body    = personalize(body_tpl, r)
            print(f"\n{'─'*50}")
            print(f"  To      : {r['name']} <{r['email']}>")
            print(f"  Subject : {subject}")
            print(f"  Body    :\n{body}")
            if attachments:
                print(f"  Attach  : {', '.join(attachments)}")
        log.info("Dry-run complete. %d message(s) previewed.", len(recipients))
        return

    context = ssl.create_default_context()
    log.info("Connecting to %s:%d …", SMTP_HOST, SMTP_PORT)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as smtp:
            smtp.login(sender_email, app_password)
            log.info("Logged in as %s", sender_email)

            for r in recipients:
                ok = send_one(smtp, sender_email, r, subject_tpl, body_tpl, attachments)
                if ok:
                    sent += 1
                else:
                    failed += 1
                time.sleep(1)   # polite delay between sends

    except smtplib.SMTPAuthenticationError:
        log.critical(
            "Authentication failed. Check your Gmail address and App Password.\n"
            "  → Enable 2-FA then generate an App Password at:\n"
            "    https://myaccount.google.com/apppasswords"
        )
        return
    except Exception as exc:
        log.critical("SMTP connection error: %s", exc)
        return

    log.info(
        "Done. Sent: %d  |  Failed: %d  |  Total: %d",
        sent, failed, len(recipients),
    )
    log.info("Full log saved to: %s", LOG_FILE)


# ── CLI ───────────────────────────────────────────────────────────────────────

def cli():
    parser = argparse.ArgumentParser(
        description="Email Sender Bot — Syntecxhub Task 3 Project 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview without sending:
  python email_sender.py --dry-run

  # Send with default CSV and template:
  python email_sender.py --sender you@gmail.com --password YOUR_APP_PASS

  # Custom CSV, subject, body, and attachment:
  python email_sender.py \\
      --sender you@gmail.com --password YOUR_APP_PASS \\
      --csv recipients.csv \\
      --subject "Hello {name}!" \\
      --body "Hi {name},\\n\\nThis is a test.\\n\\nRegards" \\
      --attach report.pdf invoice.xlsx

Gmail App Password guide:
  1. Enable 2-Step Verification on your Google account.
  2. Go to  https://myaccount.google.com/apppasswords
  3. Generate a password for "Mail" → use it as --password.
        """,
    )
    parser.add_argument("--sender",   default=os.getenv("SENDER_EMAIL", ""),
                        help="Your Gmail address (or set SENDER_EMAIL env var)")
    parser.add_argument("--password", default=os.getenv("GMAIL_APP_PASS", ""),
                        help="Gmail App Password (or set GMAIL_APP_PASS env var)")
    parser.add_argument("--csv",      default="recipients.csv",
                        help="Path to recipients CSV (default: recipients.csv)")
    parser.add_argument("--subject",  default="Hello {name}!",
                        help='Email subject. Use {column_name} for personalization.')
    parser.add_argument("--body",     default=(
                            "Hi {name},\n\n"
                            "This is an automated message.\n\n"
                            "Best regards"
                        ),
                        help="Email body text. Use {column_name} for personalization.")
    parser.add_argument("--attach",   nargs="*", default=[],
                        help="One or more file paths to attach.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Preview emails without sending.")

    args = parser.parse_args()

    if not args.dry_run:
        if not args.sender:
            parser.error("--sender is required (or set SENDER_EMAIL env var).")
        if not args.password:
            parser.error("--password is required (or set GMAIL_APP_PASS env var).")

    run(
        sender_email=args.sender,
        app_password=args.password,
        csv_path=args.csv,
        subject_tpl=args.subject,
        body_tpl=args.body,
        attachments=args.attach or [],
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    cli()

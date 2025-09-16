import os
from email.message import EmailMessage
import smtplib
from fastapi import BackgroundTasks


def _get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "localhost"),
        "port": int(os.getenv("SMTP_PORT", "25")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", "no-reply@example.com"),
    }


def send_verification_email(to_email: str, code: str):
    cfg = _get_smtp_config()
    msg = EmailMessage()
    msg["Subject"] = "Your verification code"
    msg["From"] = cfg["from"]
    msg["To"] = to_email
    msg.set_content(f"Your verification code: {code}\n\nThis code expires in 10 minutes.")

    try:
        if cfg["user"]:
            s = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
            s.starttls()
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
            s.quit()
        else:
            # local unauthed send
            s = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
            s.send_message(msg)
            s.quit()
    except Exception as err:
        # In production, log and surface monitoring; for now re-raise
        raise


def send_verification_email_background(background_tasks: BackgroundTasks, to_email: str, code: str):
    background_tasks.add_task(send_verification_email, to_email, code)

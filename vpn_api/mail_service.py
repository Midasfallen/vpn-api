import logging
import os
import smtplib
from email.message import EmailMessage

from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


def _get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "localhost"),
        "port": int(os.getenv("SMTP_PORT", "25")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", "no-reply@example.com"),
    }


def send_verification_email(to_email: str, code: str):
    # In test environments we may want to avoid external SMTP. Honor SMTP_DRY_RUN=1
    if os.getenv("SMTP_DRY_RUN", "0") in ("1", "true", "yes"):
        logger.debug(
            "SMTP_DRY_RUN enabled — skipping sending email to %s (code=%s)", to_email, code
        )
        return
    cfg = _get_smtp_config()
    msg = _prepare_message(to_email, code)
    try:
        use_ssl = False
        # allow explicit SSL when using port 465 or env flag
        if cfg.get("port") == 465 or os.getenv("SMTP_USE_SSL", "false").lower() in (
            "1",
            "true",
            "yes",
        ):
            use_ssl = True

        if use_ssl:
            # SMTP over SSL
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10) as s:
                try:
                    s.ehlo()
                except Exception:
                    logger.debug(
                        "EHLO failed on SSL connection to %s:%s",
                        cfg["host"],
                        cfg["port"],
                        exc_info=True,
                    )
                _attempt_login(s, cfg)
                s.send_message(msg)
        else:
            # plain SMTP with optional STARTTLS
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as s:
                # be explicit: send EHLO and only call starttls if the server advertises it
                try:
                    s.ehlo()
                    if s.has_extn("starttls"):
                        try:
                            s.starttls()
                            s.ehlo()
                        except Exception:
                            # STARTTLS negotiation failed — log full stack and continue without TLS
                            logger.debug(
                                "STARTTLS negotiation failed for %s:%s",
                                cfg["host"],
                                cfg["port"],
                                exc_info=True,
                            )
                    else:
                        logger.debug(
                            "SMTP server %s:%s does not advertise STARTTLS; sending without TLS",
                            cfg["host"],
                            cfg["port"],
                        )
                except Exception:
                    # EHLO can fail in odd network cases; log and continue
                    logger.debug(
                        "EHLO/STARTTLS check failed for %s:%s",
                        cfg["host"],
                        cfg["port"],
                        exc_info=True,
                    )
                _attempt_login(s, cfg)
                s.send_message(msg)
    except Exception:
        # Log details for diagnostics and re-raise so caller knows sending failed
        logger.exception(
            "Failed to send verification email to %s using SMTP host %s:%s",
            to_email,
            cfg["host"],
            cfg["port"],
        )
        raise


def _prepare_message(to_email: str, code: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Your verification code"
    msg["From"] = _get_smtp_config().get("from")
    msg["To"] = to_email
    msg.set_content(f"Your verification code: {code}\n\nThis code expires in 10 minutes.")
    return msg


def _attempt_login(server: smtplib.SMTP, cfg: dict):
    if not cfg.get("user"):
        return
    try:
        if server.has_extn("auth"):
            server.login(cfg["user"], cfg["password"])
        else:
            logger.debug(
                "SMTP server %s:%s does not support AUTH; skipping login", cfg["host"], cfg["port"]
            )
    except Exception:
        logger.exception("SMTP login failed for %s@%s", cfg.get("user"), cfg.get("host"))
        raise


def send_verification_email_background(background_tasks: BackgroundTasks, to_email: str, code: str):
    background_tasks.add_task(send_verification_email, to_email, code)

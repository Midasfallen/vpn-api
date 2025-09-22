import smtplib

from vpn_api import mail_service


def test_smtp_dry_run(monkeypatch):
    monkeypatch.setenv("SMTP_DRY_RUN", "1")
    # Should not raise and should return early
    mail_service.send_verification_email("a@b", "code")


def test_prepare_message():
    msg = mail_service._prepare_message("x@y", "999")
    assert "Your verification code" in msg["Subject"] or msg.get_content()


def test_attempt_login_no_auth(monkeypatch):
    # server without 'auth' ext -> should just return without raising
    class Dummy:
        def has_extn(self, name):
            return False

        def login(self, u, p):
            raise AssertionError("Should not be called")

    cfg = {"host": "h", "port": 25, "user": "", "password": ""}
    mail_service._attempt_login(Dummy(), cfg)


def test_send_smtp_exception(monkeypatch):
    # Simulate smtplib.SMTP throwing on send_message to exercise exception path
    class FakeSMTP:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            pass

        def has_extn(self, name):
            return False

        def send_message(self, msg):
            raise RuntimeError("send failed")

    monkeypatch.setenv("SMTP_DRY_RUN", "0")
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "25")
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: FakeSMTP())
    try:
        mail_service.send_verification_email("a@b", "c")
    except Exception:
        # exception is expected and should propagate
        return
    raise AssertionError("Expected exception from send_verification_email")

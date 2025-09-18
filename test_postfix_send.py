import traceback

from vpn_api.mail_service import _get_smtp_config, send_verification_email

print("SMTP config inside container:", _get_smtp_config())
try:
    send_verification_email("ravinski.genlawyer+test@gmail.com", "POSTFIX_TEST_PY")
    print("send ok")
except Exception:
    traceback.print_exc()

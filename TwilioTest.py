# TwilioTest.py
import os, sys
from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException




if not sid or not tok:
    print("Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in environment.")
    sys.exit(1)

try:
    from twilio.rest import Client
    client = Client(sid, tok)

    # Validate credentials (no SMS)
    acct = client.api.accounts(sid).fetch()
    print("Authenticated to account:", acct.friendly_name)

    # Send test SMS
    if not frm:
        print("Missing TWILIO_FROM_NUMBER; cannot send SMS.")
        sys.exit(1)

    msg = client.messages.create(body="MX app test message", from_=frm, to=to)
    print("Sent message SID:", msg.sid, "status:", msg.status)

except TwilioRestException as e:
    print("Twilio API error:", e)
except Exception as e:
    print("Unexpected error:", e)
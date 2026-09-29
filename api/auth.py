"""HTTP Basic Authentication helpers.

Credentials are read from the MOMO_API_USER / MOMO_API_PASS environment variables.
The defaults below are for local development only.
"""

import base64
import binascii
import hmac
import os

DEFAULT_USER = "admin"
DEFAULT_PASS = "password123"
REALM = "MoMo API"


def get_credentials():
    return os.environ.get("MOMO_API_USER", DEFAULT_USER), os.environ.get("MOMO_API_PASS", DEFAULT_PASS)


def check_basic_auth(header_value):
    """Return True if the Authorization header contains valid Basic credentials."""
    if not header_value or not header_value.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header_value[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, sep, password = decoded.partition(":")
    if not sep:
        return False
    expected_user, expected_pass = get_credentials()
    # compare_digest takes constant time, so response timing does not leak partial matches.
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    pass_ok = hmac.compare_digest(password.encode(), expected_pass.encode())
    return user_ok and pass_ok

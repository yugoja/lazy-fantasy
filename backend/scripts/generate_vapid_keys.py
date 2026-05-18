"""Generate a VAPID key pair for Web Push notifications.

Run once, then set the output values in your .env (both local and on the droplet).
Keep the same key pair across environments — changing keys invalidates all existing
browser subscriptions and users will need to re-subscribe.

Usage:
    cd backend
    ./venv/bin/python scripts/generate_vapid_keys.py
"""

import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption
)


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())

    priv_pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
    ).decode().strip()

    pub_raw = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode()

    print("Add these to backend/.env (and on the droplet via nano /opt/lazyfantasy/backend/.env):\n")
    print(f"VAPID_PUBLIC_KEY={pub_b64}")
    print(f"VAPID_PRIVATE_KEY={priv_pem}")
    print(f"VAPID_CLAIMS_EMAIL=you@lazyfantasy.app")
    print()
    print("NOTE: The private key is multi-line. In your .env file set it as:")
    print('VAPID_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\\n<base64>\\n-----END EC PRIVATE KEY-----"')
    print()
    print("Or use the single-line version by running with --raw:")


if __name__ == "__main__":
    import sys
    if "--raw" in sys.argv:
        key = ec.generate_private_key(ec.SECP256R1())
        priv_der = key.private_bytes(Encoding.DER, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        priv_b64 = base64.urlsafe_b64encode(priv_der).rstrip(b"=").decode()
        pub_raw = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        pub_b64 = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode()
        print(f"VAPID_PUBLIC_KEY={pub_b64}")
        print(f"VAPID_PRIVATE_KEY={priv_b64}")
    else:
        main()

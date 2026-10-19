"""Shared Snowflake connection helper (reads credentials from environment variables).

Required:  SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER
Auth:      SNOWFLAKE_PASSWORD   or   SNOWFLAKE_PRIVATE_KEY_PATH (+ optional SNOWFLAKE_PRIVATE_KEY_PASSPHRASE)
Optional:  SNOWFLAKE_ROLE (SYSADMIN), SNOWFLAKE_WAREHOUSE (TAXI_WH), SNOWFLAKE_DATABASE (NYC_TAXI)

Newer Snowflake accounts enforce MFA for password logins, so key-pair auth is the
smoother option for scripts.
"""
import os

import snowflake.connector


def _private_key_bytes(path: str, passphrase: str | None) -> bytes:
    from cryptography.hazmat.primitives import serialization

    with open(path, "rb") as fh:
        key = serialization.load_pem_private_key(
            fh.read(), password=passphrase.encode() if passphrase else None
        )
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect(schema: str = "RAW"):
    params = dict(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        role=os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "TAXI_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "NYC_TAXI"),
        schema=schema,
    )
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if key_path:
        params["private_key"] = _private_key_bytes(key_path, os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"))
    else:
        params["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**params)

"""Generate disposable local-CI secrets. Never overwrite an existing developer .env."""
import secrets
from pathlib import Path

values = {
    "MYSQL_ROOT_PASSWORD": secrets.token_hex(24),
    "MYSQL_DATABASE": "ouc_tongpin",
    "MYSQL_USER": "tongpin",
    "MYSQL_PASSWORD": secrets.token_hex(24),
    "MYSQL_PORT": "3307",
    "REDIS_PASSWORD": secrets.token_hex(24),
    "ANON_ID_SECRET": secrets.token_hex(32),
    "WEB_PORT": "8080",
}
with Path(".env").open("x", encoding="utf-8") as output:
    output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
print("Generated disposable .env (values omitted)")

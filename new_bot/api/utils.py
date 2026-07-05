from pydantic import BaseModel
import hmac
import hashlib
import time
import os
from urllib.parse import parse_qsl


BOT_TOKEN = os.getenv("BOT_TOKEN")

class InitData(BaseModel):
    initData: str

def validate_init_data(init_data: str):
    data = dict(parse_qsl(init_data))

    print("TG DATA GET :::::::::::>>", data)
    if "hash" not in data:
        return None

    received_hash = data.pop("hash")

    # 1. Сортируем данные
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )
    print("data_check_string GET :::::::::::>>", data)
    # 2. secret key
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    print("secret_key GET :::::::::::>>", data)
    # 3. hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    print("computed_hash GET :::::::::::>>", data)

    if computed_hash != received_hash:
        return None

    # 4. проверка времени (24h)
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return None
    print("auth_date GET :::::::::::>>", data)

    return data
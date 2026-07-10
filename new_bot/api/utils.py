from pydantic import BaseModel
import hmac
import hashlib
import time
import os
from urllib.parse import parse_qsl
import json


BOT_TOKEN = os.getenv("BOT_TOKEN")

class InitData(BaseModel):
    initData: str

def eprint(text, *args):
    print(f"\033[31m{text}\033[0m", " ".join(args))
    
def validate_init_data(init_data: str):
    data = dict(parse_qsl(init_data))

    # print("TG DATA GET :::::::::::>>", data)
    if "hash" not in data:
        return None

    received_hash = data.pop("hash")

    # 1. Сортируем данные
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )
    
    # 2. secret key
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    
    # 3. hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if computed_hash != received_hash:
        eprint("if computed_hash != received_hash", computed_hash, received_hash)
        # return None

    # 4. проверка времени (24h)
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        eprint("if time.time() - auth_date > 86400")
    #     return None
    
    data['user'] =  json.loads(data['user'])
    return data

QUIZES = [
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 1', 'secret_code':'DSFGS', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 2', 'secret_code':'CACTD', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 1},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 3', 'secret_code':'FXZJN', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 2},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 4', 'secret_code':'VGNMD', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 3},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 5', 'secret_code':'UZQYX', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 4},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 6', 'secret_code':'KBCFL', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 5},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 7', 'secret_code':'XTHFL', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 6},
    {'question':'Как называется самая известная смотровая площадка Москвы? Нажмите 8', 'secret_code':'EGLPZ', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 7}
]


TEAMS = [
    'Выгода', 
    'Реклама', 
    'Город', 
    'Покупки', 
    'Путешествия', 
    'Т-Авто', 
    'Общие платформы', 
    'Команда аналитики, роста и монетизации', 
    'HR'
]
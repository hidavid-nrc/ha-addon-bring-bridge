from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import os, time
from typing import List, Optional
from bring_api import BringApi

API_KEY = os.environ.get("API_KEY", "")
BRING_EMAIL = os.environ["BRING_EMAIL"]
BRING_PASSWORD = os.environ["BRING_PASSWORD"]
DEFAULT_LIST_NAME = os.environ.get("BRING_LIST_NAME")

app = FastAPI(title="Bring Bridge", version="1.0.0")
api = BringApi(BRING_EMAIL, BRING_PASSWORD)
api.login()
last_login = time.time()

def ensure_login():
    global last_login
    if time.time() - last_login > 6 * 3600:
        api.login()
        last_login = time.time()

def get_default_list_uuid():
    ensure_login()
    lists = api.get_lists()
    if "lists" not in lists or not lists["lists"]:
        raise HTTPException(500, "No Bring! lists found")
    if DEFAULT_LIST_NAME:
        for l in lists["lists"]:
            if l["name"].strip().lower() == DEFAULT_LIST_NAME.strip().lower():
                return l["listUuid"]
    return lists["lists"][0]["listUuid"]

def normalize(s: str) -> str:
    return (s or "").strip().lower()

def require_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")

@app.get("/health")
def health(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    return {"status":"ok"}

@app.get("/list")
def list_items(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    list_uuid = get_default_list_uuid()
    return api.get_items(list_uuid)

class AddReq(BaseModel):
    name: str
    spec: Optional[str] = None

class BatchReq(BaseModel):
    items: List[AddReq]

@app.post("/add")
def add_item(payload: AddReq, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    list_uuid = get_default_list_uuid()
    existing = api.get_items(list_uuid).get("purchase", [])
    exists = {(normalize(i["name"]), normalize(i.get("spec"))) for i in existing}
    key = (normalize(payload.name), normalize(payload.spec))
    if key in exists:
        return {"status":"skipped","reason":"already present","item":payload.model_dump()}
    api.save_item(list_uuid, payload.name, payload.spec)
    return {"status":"ok","added":payload.model_dump()}

@app.post("/add_batch")
def add_batch(payload: BatchReq, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    list_uuid = get_default_list_uuid()
    existing = api.get_items(list_uuid).get("purchase", [])
    exists = {(normalize(i["name"]), normalize(i.get("spec"))) for i in existing}
    added, skipped = [], []
    for it in payload.items:
        key = (normalize(it.name), normalize(it.spec))
        if key in exists:
            skipped.append(it.model_dump())
            continue
        api.save_item(list_uuid, it.name, it.spec)
        added.append(it.model_dump())
        exists.add(key)
    return {"status":"ok","added":added,"skipped":skipped}

@app.post("/remove")
def remove_item(payload: AddReq, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    list_uuid = get_default_list_uuid()
    api.remove_item(list_uuid, payload.name, payload.spec)
    return {"status":"ok","removed":payload.model_dump()}


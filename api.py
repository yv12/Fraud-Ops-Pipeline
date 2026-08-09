import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import duckdb
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import threading
import time
import queue
import json
import asyncio
import os

os.makedirs("dashboard", exist_ok=True)

app = FastAPI(title="Fraud Scoring API")

DB_PATH = "fraud_pipeline.duckdb"
mlflow.set_tracking_uri("sqlite:///mlflow.db")

models = {"Production": None, "Candidate": None}
model_versions = {"Production": None, "Candidate": None}
model_metrics = {"Production": None, "Candidate": None}
db_queue = queue.Queue()

# Global state for dashboard history
live_transaction_count = 0
recent_logs = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class TransactionRequest(BaseModel):
    transaction_id: str
    features: dict
    
class GroundTruthRequest(BaseModel):
    transaction_id: str
    actual_label: int

def db_worker():
    conn = duckdb.connect(DB_PATH)
    while True:
        item = db_queue.get()
        if item is None: break
        action = item[0]
        try:
            if action == "TX":
                _, tx_id, features = item
                cols = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']
                vals = [features.get(c, 0.0) for c in cols]
                conn.execute(
                    f"INSERT INTO transactions (transaction_id, {','.join(cols)}) VALUES (?, {','.join(['?']*30)})",
                    [tx_id] + vals
                )
            elif action == "SCORE":
                _, tx_id, model_ver, score, pred_type = item
                conn.execute(
                    "INSERT INTO predictions (transaction_id, model_version, score, prediction_type) VALUES (?, ?, ?, ?)",
                    [tx_id, model_ver, score, pred_type]
                )
            elif action == "GROUND_TRUTH":
                _, tx_id, actual_label = item
                conn.execute(
                    "INSERT INTO ground_truth (transaction_id, actual_label) VALUES (?, ?)", 
                    [tx_id, actual_label]
                )
        except Exception as e:
            print(f"Failed to log {action} to DB:", e)
        db_queue.task_done()

def load_models_from_mlflow():
    client = MlflowClient()
    model_name = "FraudScoringModel"
    try:
        prod_info = client.get_model_version_by_alias(model_name, "Production")
        if model_versions["Production"] != prod_info.version:
            print(f"Loading Production model v{prod_info.version}...")
            models["Production"] = mlflow.sklearn.load_model(f"models:/{model_name}@Production")
            model_versions["Production"] = prod_info.version
            try:
                run = client.get_run(prod_info.run_id)
                model_metrics["Production"] = {
                    "precision": run.data.metrics.get("precision", 0.0),
                    "recall": run.data.metrics.get("recall", 0.0)
                }
            except Exception: pass
    except Exception: pass 
    
    try:
        cand_info = client.get_model_version_by_alias(model_name, "Candidate")
        if model_versions["Candidate"] != cand_info.version:
            print(f"Loading Candidate model v{cand_info.version}...")
            models["Candidate"] = mlflow.sklearn.load_model(f"models:/{model_name}@Candidate")
            model_versions["Candidate"] = cand_info.version
            try:
                run = client.get_run(cand_info.run_id)
                model_metrics["Candidate"] = {
                    "precision": run.data.metrics.get("precision", 0.0),
                    "recall": run.data.metrics.get("recall", 0.0)
                }
            except Exception: pass
    except Exception: pass 

def poll_mlflow():
    while True:
        time.sleep(10)
        load_models_from_mlflow()

@app.on_event("startup")
def startup_event():
    print("Starting API...")
    threading.Thread(target=db_worker, daemon=True).start()
    load_models_from_mlflow()
    threading.Thread(target=poll_mlflow, daemon=True).start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send the historical state so dashboard doesn't reset on refresh
    await websocket.send_json({
        "type": "INIT",
        "total_count": live_transaction_count,
        "recent_logs": recent_logs
    })
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/score")
async def score_transaction(request: TransactionRequest):
    if models["Production"] is None:
        return {"error": "System not ready."}
        
    global live_transaction_count
    live_transaction_count += 1
        
    db_queue.put(("TX", request.transaction_id, request.features))
    
    features_for_model = {k: v for k, v in request.features.items() if k != 'Time'}
    df_features = pd.DataFrame([features_for_model])
    
    prod_prob = models["Production"].predict_proba(df_features)[0][1] 
    prod_decision = 1 if prod_prob >= 0.5 else 0
    db_queue.put(("SCORE", request.transaction_id, f"v{model_versions['Production']}", prod_prob, "Production"))

    cand_prob = None
    if models["Candidate"] is not None:
        try:
            cand_prob = models["Candidate"].predict_proba(df_features)[0][1]
            db_queue.put(("SCORE", request.transaction_id, f"v{model_versions['Candidate']}", cand_prob, "Shadow"))
        except Exception:
            pass
            
    amount = request.features.get("Amount", 0.0)
    
    payload = {
        "type": "TX",
        "transaction_id": request.transaction_id,
        "amount": round(amount, 2),
        "prod_prob": round(prod_prob, 4),
        "prod_decision": prod_decision,
        "cand_prob": round(cand_prob, 4) if cand_prob is not None else None,
        "cand_decision": 1 if (cand_prob is not None and cand_prob >= 0.5) else 0,
        "prod_version": model_versions["Production"],
        "cand_version": model_versions["Candidate"],
        "prod_metrics": model_metrics["Production"],
        "cand_metrics": model_metrics["Candidate"],
        "total_count": live_transaction_count
    }
    
    recent_logs.append(payload)
    if len(recent_logs) > 50:
        recent_logs.pop(0)
    
    await manager.broadcast(payload)

    return {
        "transaction_id": request.transaction_id,
        "fraud_probability": round(prod_prob, 4),
        "decision": prod_decision
    }

@app.post("/ground_truth")
async def receive_ground_truth(request: GroundTruthRequest):
    db_queue.put(("GROUND_TRUTH", request.transaction_id, request.actual_label))
    return {"status": "accepted"}

app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")

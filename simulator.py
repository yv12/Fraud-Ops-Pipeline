import pandas as pd
import requests
import uuid
import time
import random

API_SCORE_URL = "http://localhost:8000/score"

def run_continuous_simulation():
    print("Starting continuous live traffic simulation for dashboard...")
    header = pd.read_csv("Data/creditcard.csv", nrows=0).columns
    # Let's take a slice of 10000 rows to cycle through
    df = pd.read_csv("Data/creditcard.csv", skiprows=range(1, 100000), nrows=10000)
    df.columns = header
    
    while True: # Infinite loop for the dashboard
        # Pick a random row to simulate live traffic
        row = df.sample(1).iloc[0]
        tx_id = str(uuid.uuid4())
        
        payload = {
            "transaction_id": tx_id,
            "features": row.drop(['Class']).to_dict()
        }
        
        try:
            requests.post(API_SCORE_URL, json=payload, timeout=2)
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e} - Retrying in 5 seconds...")
            time.sleep(5)
            continue
            
        time.sleep(random.uniform(0.5, 2.0)) # Random delay between transactions

if __name__ == "__main__":
    run_continuous_simulation()

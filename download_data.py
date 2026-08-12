"""
Generates a synthetic Credit Card Fraud Detection dataset if not present locally.
Since the original Kaggle CSV is 150MB and public mirrors frequently 404 or rate-limit,
generating a synthetic version ensures the Railway deployment is 100% reliable.
"""
import os
import pandas as pd
import numpy as np

DATA_DIR = "Data"
CSV_PATH = os.path.join(DATA_DIR, "creditcard.csv")
NUM_ROWS = 120000  # Enough for baseline (50k), shadow (2k), and simulator (10k)

def download_dataset():
    if os.path.exists(CSV_PATH):
        print(f"[DATA] {CSV_PATH} already exists. Skipping generation.")
        return True
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print(f"[DATA] Generating {NUM_ROWS} rows of synthetic credit card data...")
    try:
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # 1. Generate Time (sequential seconds)
        time_col = np.sort(np.random.uniform(0, 172792, NUM_ROWS))
        
        # 2. Generate PCA features V1-V28 (standard normal distribution)
        # Real PCA features usually have mean ~0 and variance ~1, with decreasing variance
        v_cols = {}
        for i in range(1, 29):
            scale = max(0.5, 2.0 - (i * 0.05)) # simulate decreasing variance
            v_cols[f'V{i}'] = np.random.normal(0, scale, NUM_ROWS)
            
        # 3. Generate Amount (log-normal distribution to simulate real transaction amounts)
        amount_col = np.random.lognormal(mean=3.0, sigma=1.2, size=NUM_ROWS)
        amount_col = np.round(amount_col, 2)
        
        # 4. Generate Class (mostly 0, roughly 0.2% fraud)
        class_col = np.random.choice([0, 1], size=NUM_ROWS, p=[0.998, 0.002])
        
        # Inject realistic fraud patterns into V1, V2, V3 for the fraudulent rows
        # This ensures the Logistic Regression model can actually learn something!
        fraud_idx = class_col == 1
        v_cols['V1'][fraud_idx] -= np.random.normal(3.0, 1.0, fraud_idx.sum())
        v_cols['V2'][fraud_idx] += np.random.normal(2.0, 1.0, fraud_idx.sum())
        v_cols['V3'][fraud_idx] -= np.random.normal(4.0, 1.5, fraud_idx.sum())
        
        # Build DataFrame
        df = pd.DataFrame({'Time': time_col})
        for i in range(1, 29):
            df[f'V{i}'] = v_cols[f'V{i}']
        df['Amount'] = amount_col
        df['Class'] = class_col
        
        print(f"[DATA] Saving synthetic dataset to {CSV_PATH}...")
        df.to_csv(CSV_PATH, index=False)
        
        size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
        print(f"[DATA] Synthetic dataset ready: {CSV_PATH} ({size_mb:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"[DATA] Generation failed: {e}")
        return False

if __name__ == "__main__":
    download_dataset()

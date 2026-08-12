"""
Generates a synthetic Credit Card Fraud Detection dataset and uploads it directly
to the PostgreSQL database, eliminating the need for a local 150MB CSV file.
"""
import os
import pandas as pd
import numpy as np
import db
import math

NUM_ROWS = 70000  # Enough for baseline (50k), shadow (2k), and simulator (10k)

def generate_and_upload():
    conn = db.get_connection()
    
    # Check if data already exists
    count_df = db.get_dataframe(conn, "SELECT COUNT(*) as count FROM historical_data")
    if count_df['count'].iloc[0] >= NUM_ROWS:
        print(f"[DATA] historical_data table already has {count_df['count'].iloc[0]} rows. Skipping upload.")
        return
    
    print(f"[DATA] Generating {NUM_ROWS} rows of synthetic credit card data...")
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # 1. Generate Time (sequential seconds)
    time_col = np.sort(np.random.uniform(0, 172792, NUM_ROWS))
    
    # 2. Generate PCA features V1-V28 (standard normal distribution)
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
    
    print("[DATA] Uploading to PostgreSQL database in batches...")
    
    # Clear existing data first
    db.execute_query(conn, "DELETE FROM historical_data")
    
    # Get column names for insert
    cols = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']
    is_postgres = os.environ.get("DATABASE_URL") is not None
    
    batch_size = 10000
    num_batches = math.ceil(NUM_ROWS / batch_size)
    
    for i in range(num_batches):
        batch = df.iloc[i*batch_size : (i+1)*batch_size]
        
        if is_postgres:
            # For Postgres we use execute_values via psycopg2.extras for speed
            import psycopg2.extras
            cursor = conn.cursor()
            query = f"INSERT INTO historical_data ({','.join(cols)}) VALUES %s"
            # Extract values as a list of tuples
            values = [tuple(x) for x in batch.to_numpy()]
            psycopg2.extras.execute_values(cursor, query, values)
            conn.commit()
            cursor.close()
        else:
            # DuckDB
            # We can register the dataframe and insert directly
            conn.register('batch_df', batch)
            conn.execute("INSERT INTO historical_data (Time, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, Amount, Class) SELECT * FROM batch_df")
            conn.unregister('batch_df')
            
        print(f"[DATA] Uploaded batch {i+1}/{num_batches}")
        
    print("[DATA] Upload complete!")

if __name__ == "__main__":
    generate_and_upload()

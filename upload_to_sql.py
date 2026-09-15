"""
Generates a synthetic Credit Card Fraud Detection dataset and uploads it directly
to the PostgreSQL database, eliminating the need for a local 150MB CSV file.

Memory-optimized: generates and uploads in small chunks to avoid OOM on Railway.
"""
import os
import numpy as np
import db
import gc

NUM_ROWS = 70000  # Enough for baseline (50k), shadow (2k), and simulator (10k)
CHUNK_SIZE = 2000  # Generate and upload in small chunks to keep memory low


def _generate_chunk(start_idx, chunk_size, global_seed=42):
    """Generate a single chunk of synthetic data as a list of tuples (no pandas)."""
    # Use a deterministic seed per chunk so results are reproducible
    rng = np.random.RandomState(global_seed + start_idx)
    
    # 1. Time (sorted within chunk, offset by start_idx)
    time_col = np.sort(rng.uniform(
        (start_idx / NUM_ROWS) * 172792,
        ((start_idx + chunk_size) / NUM_ROWS) * 172792,
        chunk_size
    ))
    
    # 2. PCA features V1-V28
    v_cols = {}
    for i in range(1, 29):
        scale = max(0.5, 2.0 - (i * 0.05))
        v_cols[f'V{i}'] = rng.normal(0, scale, chunk_size)
    
    # 3. Amount
    amount_col = np.round(rng.lognormal(mean=3.0, sigma=1.2, size=chunk_size), 2)
    
    # 4. Class (mostly 0, roughly 0.2% fraud)
    class_col = rng.choice([0, 1], size=chunk_size, p=[0.998, 0.002])
    
    # Inject realistic fraud patterns
    fraud_idx = class_col == 1
    if fraud_idx.sum() > 0:
        v_cols['V1'][fraud_idx] -= rng.normal(3.0, 1.0, fraud_idx.sum())
        v_cols['V2'][fraud_idx] += rng.normal(2.0, 1.0, fraud_idx.sum())
        v_cols['V3'][fraud_idx] -= rng.normal(4.0, 1.5, fraud_idx.sum())
    
    # Build rows as list of tuples (avoids pandas DataFrame overhead)
    rows = []
    for j in range(chunk_size):
        row = [float(time_col[j])]
        for i in range(1, 29):
            row.append(float(v_cols[f'V{i}'][j]))
        row.append(float(amount_col[j]))
        row.append(int(class_col[j]))
        rows.append(tuple(row))
    
    return rows


def generate_and_upload():
    conn = db.get_connection()
    
    # Check if data already exists
    count_df = db.get_dataframe(conn, "SELECT COUNT(*) as count FROM historical_data")
    if count_df['count'].iloc[0] >= NUM_ROWS:
        print(f"[DATA] historical_data table already has {count_df['count'].iloc[0]} rows. Skipping upload.")
        del count_df
        return
    del count_df
    
    print(f"[DATA] Generating {NUM_ROWS} rows of synthetic credit card data in chunks of {CHUNK_SIZE}...")
    
    # Clear existing data first
    db.execute_query(conn, "DELETE FROM historical_data")
    
    cols = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']
    is_postgres = os.environ.get("DATABASE_URL") is not None
    
    num_chunks = (NUM_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * CHUNK_SIZE
        current_chunk_size = min(CHUNK_SIZE, NUM_ROWS - start_idx)
        
        # Generate this chunk (no pandas, just numpy + list of tuples)
        rows = _generate_chunk(start_idx, current_chunk_size)
        
        if is_postgres:
            import psycopg2.extras
            cursor = conn.cursor()
            query = f"INSERT INTO historical_data ({','.join(cols)}) VALUES %s"
            psycopg2.extras.execute_values(cursor, query, rows)
            conn.commit()
            cursor.close()
        else:
            # DuckDB — use executemany
            placeholders = ','.join(['?'] * len(cols))
            query = f"INSERT INTO historical_data ({','.join(cols)}) VALUES ({placeholders})"
            for row in rows:
                conn.execute(query, list(row))
        
        # Free this chunk immediately
        del rows
        gc.collect()
        
        print(f"[DATA] Uploaded chunk {chunk_idx + 1}/{num_chunks} ({start_idx + current_chunk_size}/{NUM_ROWS} rows)")
    
    print("[DATA] Upload complete!")


if __name__ == "__main__":
    generate_and_upload()

# pyrefly: ignore [missing-import]
import duckdb

def setup_database():
    conn = duckdb.connect('fraud_pipeline.duckdb')
    
    print("Creating transactions table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR PRIMARY KEY,
            Time DOUBLE,
            V1 DOUBLE, V2 DOUBLE, V3 DOUBLE, V4 DOUBLE, V5 DOUBLE, 
            V6 DOUBLE, V7 DOUBLE, V8 DOUBLE, V9 DOUBLE, V10 DOUBLE, 
            V11 DOUBLE, V12 DOUBLE, V13 DOUBLE, V14 DOUBLE, V15 DOUBLE, 
            V16 DOUBLE, V17 DOUBLE, V18 DOUBLE, V19 DOUBLE, V20 DOUBLE, 
            V21 DOUBLE, V22 DOUBLE, V23 DOUBLE, V24 DOUBLE, V25 DOUBLE, 
            V26 DOUBLE, V27 DOUBLE, V28 DOUBLE,
            Amount DOUBLE
        );
    """)

    print("Creating predictions table...")
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_pred_id;
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER DEFAULT nextval('seq_pred_id') PRIMARY KEY,
            transaction_id VARCHAR,
            model_version VARCHAR,
            score DOUBLE,
            prediction_type VARCHAR, -- 'Production' or 'Shadow'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    print("Creating ground truth table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ground_truth (
            transaction_id VARCHAR PRIMARY KEY,
            actual_label INTEGER,
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    print("Database schema successfully created in fraud_pipeline.duckdb")
    
    # Show tables to verify
    tables = conn.execute("SHOW TABLES").fetchall()
    print("Tables in database:", tables)

if __name__ == "__main__":
    setup_database()

# pyrefly: ignore [missing-import]
import os
import db

def setup_database():
    conn = db.get_connection()
    is_postgres = os.environ.get("DATABASE_URL") is not None
    
    print("Creating transactions table...")
    db.execute_query(conn, """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR PRIMARY KEY,
            Time DOUBLE PRECISION,
            V1 DOUBLE PRECISION, V2 DOUBLE PRECISION, V3 DOUBLE PRECISION, V4 DOUBLE PRECISION, V5 DOUBLE PRECISION, 
            V6 DOUBLE PRECISION, V7 DOUBLE PRECISION, V8 DOUBLE PRECISION, V9 DOUBLE PRECISION, V10 DOUBLE PRECISION, 
            V11 DOUBLE PRECISION, V12 DOUBLE PRECISION, V13 DOUBLE PRECISION, V14 DOUBLE PRECISION, V15 DOUBLE PRECISION, 
            V16 DOUBLE PRECISION, V17 DOUBLE PRECISION, V18 DOUBLE PRECISION, V19 DOUBLE PRECISION, V20 DOUBLE PRECISION, 
            V21 DOUBLE PRECISION, V22 DOUBLE PRECISION, V23 DOUBLE PRECISION, V24 DOUBLE PRECISION, V25 DOUBLE PRECISION, 
            V26 DOUBLE PRECISION, V27 DOUBLE PRECISION, V28 DOUBLE PRECISION,
            Amount DOUBLE PRECISION
        );
    """)

    print("Creating predictions table...")
    if is_postgres:
        db.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id SERIAL PRIMARY KEY,
                transaction_id VARCHAR,
                model_version VARCHAR,
                score DOUBLE PRECISION,
                prediction_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        db.execute_query(conn, """
            CREATE SEQUENCE IF NOT EXISTS seq_pred_id;
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id INTEGER DEFAULT nextval('seq_pred_id') PRIMARY KEY,
                transaction_id VARCHAR,
                model_version VARCHAR,
                score DOUBLE,
                prediction_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    print("Creating ground truth table...")
    db.execute_query(conn, """
        CREATE TABLE IF NOT EXISTS ground_truth (
            transaction_id VARCHAR PRIMARY KEY,
            actual_label INTEGER,
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    print("Creating historical data table...")
    db.execute_query(conn, """
        CREATE TABLE IF NOT EXISTS historical_data (
            id SERIAL PRIMARY KEY,
            Time DOUBLE PRECISION,
            V1 DOUBLE PRECISION, V2 DOUBLE PRECISION, V3 DOUBLE PRECISION, V4 DOUBLE PRECISION, V5 DOUBLE PRECISION, 
            V6 DOUBLE PRECISION, V7 DOUBLE PRECISION, V8 DOUBLE PRECISION, V9 DOUBLE PRECISION, V10 DOUBLE PRECISION, 
            V11 DOUBLE PRECISION, V12 DOUBLE PRECISION, V13 DOUBLE PRECISION, V14 DOUBLE PRECISION, V15 DOUBLE PRECISION, 
            V16 DOUBLE PRECISION, V17 DOUBLE PRECISION, V18 DOUBLE PRECISION, V19 DOUBLE PRECISION, V20 DOUBLE PRECISION, 
            V21 DOUBLE PRECISION, V22 DOUBLE PRECISION, V23 DOUBLE PRECISION, V24 DOUBLE PRECISION, V25 DOUBLE PRECISION, 
            V26 DOUBLE PRECISION, V27 DOUBLE PRECISION, V28 DOUBLE PRECISION,
            Amount DOUBLE PRECISION,
            Class INTEGER
        );
    """)
    
    print("Database schema successfully created!")

if __name__ == "__main__":
    setup_database()

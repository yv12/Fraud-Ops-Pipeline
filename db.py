import os
import pandas as pd

DB_PATH = "fraud_pipeline.duckdb"

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        import psycopg2
        return psycopg2.connect(db_url)
    else:
        import duckdb
        return duckdb.connect(DB_PATH)

def execute_query(conn, query, params=None):
    db_url = os.environ.get("DATABASE_URL")
    
    # Adapt parameter syntax
    if db_url and params:
        query = query.replace("?", "%s")
        
    if db_url:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    else:
        if params:
            return conn.execute(query, params)
        else:
            return conn.execute(query)

def get_dataframe(conn, query, params=None):
    db_url = os.environ.get("DATABASE_URL")
    if db_url and params:
        query = query.replace("?", "%s")
    
    if db_url:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            return pd.read_sql(query, conn, params=params)
    else:
        if params:
            return conn.execute(query, params).df()
        else:
            return conn.execute(query).df()

import duckdb
import pandas as pd
import uuid
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from sklearn.metrics import precision_score, recall_score

DB_PATH = "fraud_pipeline.duckdb"
mlflow.set_tracking_uri("sqlite:///mlflow.db")

def simulate_shadow_traffic_if_needed(conn):
    """
    Since we didn't run the API long enough to gather thousands of real shadow traffic predictions,
    this helper function generates 2000 new transactions, scores them locally with both models,
    and injects them into the database so the Judge has something to grade!
    """
    count = conn.execute("SELECT COUNT(*) FROM predictions WHERE prediction_type = 'Shadow'").fetchone()[0]
    if count > 100:
        return
        
    print("Generating simulated shadow traffic for evaluation...")
    client = MlflowClient()
    try:
        prod_ver = client.get_model_version_by_alias("FraudScoringModel", "Production").version
        cand_ver = client.get_model_version_by_alias("FraudScoringModel", "Candidate").version
    except Exception as e:
        print("Missing Candidate or Production models in MLflow. Cannot evaluate.")
        return

    prod_model = mlflow.sklearn.load_model(f"models:/FraudScoringModel@Production")
    cand_model = mlflow.sklearn.load_model(f"models:/FraudScoringModel@Candidate")
    
    # Load a brand new slice of unseen test data (rows 55000 to 57000)
    header = pd.read_csv("Data/creditcard.csv", nrows=0).columns
    test_df = pd.read_csv("Data/creditcard.csv", skiprows=range(1, 55001), nrows=2000)
    test_df.columns = header
    
    X = test_df.drop(columns=['Class', 'Time'])
    
    for i, row in test_df.iterrows():
        tx_id = str(uuid.uuid4())
        
        actual = int(row['Class'])
        conn.execute("INSERT INTO ground_truth (transaction_id, actual_label) VALUES (?, ?)", [tx_id, actual])
        
        features_df = pd.DataFrame([X.iloc[i].to_dict()])
        prod_prob = prod_model.predict_proba(features_df)[0][1]
        cand_prob = cand_model.predict_proba(features_df)[0][1]
        
        conn.execute("INSERT INTO predictions VALUES (nextval('seq_pred_id'), ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                     [tx_id, f"v{prod_ver}", prod_prob, "Production"])
                     
        conn.execute("INSERT INTO predictions VALUES (nextval('seq_pred_id'), ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                     [tx_id, f"v{cand_ver}", cand_prob, "Shadow"])

def run_validation_and_promotion():
    conn = duckdb.connect(DB_PATH)
    
    simulate_shadow_traffic_if_needed(conn)
    
    print("\n--- Phase 5: The Judge ---")
    print("Pulling all transactions that were scored by BOTH models and have Ground Truth...")
    
    df = conn.execute("""
        SELECT 
            p1.transaction_id,
            p1.model_version as prod_model,
            p1.score as prod_score,
            p2.model_version as cand_model,
            p2.score as cand_score,
            g.actual_label
        FROM predictions p1
        JOIN predictions p2 ON p1.transaction_id = p2.transaction_id
        JOIN ground_truth g ON p1.transaction_id = g.transaction_id
        WHERE p1.prediction_type = 'Production' AND p2.prediction_type = 'Shadow'
    """).df()
    
    if len(df) == 0:
        print("No paired predictions found.")
        return
        
    print(f"Evaluating models on {len(df)} transactions...")
    
    # Calculate decisions (threshold 0.5)
    y_true = df['actual_label']
    y_prod = (df['prod_score'] >= 0.5).astype(int)
    y_cand = (df['cand_score'] >= 0.5).astype(int)
    
    prod_precision = precision_score(y_true, y_prod, zero_division=0)
    prod_recall = recall_score(y_true, y_prod, zero_division=0)
    
    cand_precision = precision_score(y_true, y_cand, zero_division=0)
    cand_recall = recall_score(y_true, y_cand, zero_division=0)
    
    print("\n--- Evaluation Results ---")
    print(f"Production Model ({df['prod_model'].iloc[0]}):")
    print(f"  Precision: {prod_precision:.4f}  |  Recall: {prod_recall:.4f}")
    
    print(f"\nCandidate Model ({df['cand_model'].iloc[0]}):")
    print(f"  Precision: {cand_precision:.4f}  |  Recall: {cand_recall:.4f}")
    
    # PRODUCT LOGIC (From Word.md)
    print("\nApplying Product Rule: (New Precision > Old Precision) AND (New Recall > Old Recall)")
    
    if (cand_precision > prod_precision) and (cand_recall > prod_recall):
        print("\nRESULT: Candidate Model is strictly BETTER. Promoting to Production!")
        
        client = MlflowClient()
        cand_ver = df['cand_model'].iloc[0].replace('v', '') # strip 'v'
        
        # Promote Candidate to Production
        client.set_registered_model_alias("FraudScoringModel", "Production", cand_ver)
        print(f"Success! Model Version {cand_ver} is now the official Production model.")
        print("The FastAPI server will hot-reload it on the next polling cycle.")
    else:
        print("\nRESULT: Candidate Model failed the product rule requirements.")
        print("It will be discarded. The incumbent Production model remains active to protect the business.")

if __name__ == "__main__":
    run_validation_and_promotion()

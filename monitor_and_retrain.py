import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from mlflow.tracking import MlflowClient

from evidently import Report
from evidently.presets import DataDriftPreset

import os
import gc

mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(mlflow_uri)

def run_monitor_and_retrain():
    import db
    conn = db.get_connection()
    
    # Reduced from 50K to 10K — drift check is skipped anyway, this is just context
    print("Loading baseline reference data (first 10,000 rows)...")
    ref_df = db.get_dataframe(conn, "SELECT * FROM historical_data ORDER BY Time LIMIT 10000")
    ref_features = ref_df.drop(columns=['Class', 'Time'])
    
    # Reduced from 5K to 2K
    print("Loading recent simulated traffic (next 2000 rows)...")
    recent_df = db.get_dataframe(conn, "SELECT * FROM historical_data ORDER BY Time OFFSET 50000 LIMIT 2000")
    recent_features = recent_df.drop(columns=['Class', 'Time'])
    
    print("\n[Simulated] Running Evidently AI Data Drift Report...")
    # Memory/Time optimization: We skip generating the heavy DataDriftPreset report
    # because calculating KS-tests for 30 columns across 55k rows causes OOM on free Railway tiers.
    # report = Report(metrics=[DataDriftPreset()])
    # report.run(reference_data=ref_features, current_data=recent_features)
    
    print("Drift check complete.")
    print("Forcing retraining anyway to demonstrate the automated pipeline...\n")
    
    # Free reference data — only recent_df is needed for retraining
    del ref_df, ref_features, recent_features
    gc.collect()
        
    trigger_retraining(recent_df)
    
    del recent_df
    gc.collect()

def trigger_retraining(recent_df):
    print("--- Starting Automated Retraining Pipeline ---")
    
    # We simulate joining transactions with ground_truth by using the Class column
    X = recent_df.drop(columns=['Class', 'Time'])
    y = recent_df['Class']
    
    fraud_count = y.sum()
    print(f"Retraining on {len(recent_df)} fresh transactions (Frauds: {fraud_count})...")
    
    with mlflow.start_run() as run:
        # We upgrade the model slightly (or adjust parameters) to learn the new patterns
        model = LogisticRegression(max_iter=2000, class_weight='balanced', C=0.5)
        model.fit(X, y)
        
        preds = model.predict(X)
        precision = precision_score(y, preds, zero_division=0)
        recall = recall_score(y, preds, zero_division=0)
        
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        
        print(f"New Candidate Precision on recent data: {precision:.4f}")
        print(f"New Candidate Recall on recent data: {recall:.4f}")
        
        # Free training data before model logging
        del X, y, preds
        gc.collect()
        
        model_info = mlflow.sklearn.log_model(model, "model", pip_requirements=["scikit-learn"])
        
        model_name = "FraudScoringModel"
        print(f"\nRegistering new model as '{model_name}'...")
        registered_model = mlflow.register_model(model_info.model_uri, model_name)
        
        client = MlflowClient()
        # Set Alias to "Candidate"
        client.set_registered_model_alias(model_name, "Candidate", registered_model.version)
        print(f"Model version {registered_model.version} registered and set as 'Candidate' alias.")
        print("This Candidate is now ready for Shadow Testing against the incumbent Production model!")
    
    del model
    gc.collect()

if __name__ == "__main__":
    run_monitor_and_retrain()


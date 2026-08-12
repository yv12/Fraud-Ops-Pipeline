import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from mlflow.tracking import MlflowClient

from evidently import Report
from evidently.presets import DataDriftPreset

import os

mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(mlflow_uri)

def run_monitor_and_retrain():
    print("Loading baseline reference data (first 50,000 rows)...")
    ref_df = pd.read_csv("Data/creditcard.csv", nrows=50000)
    ref_features = ref_df.drop(columns=['Class', 'Time'])
    
    print("Loading recent simulated traffic (next 5000 rows)...")
    # Simulate pulling the recent traffic from the database
    header = pd.read_csv("Data/creditcard.csv", nrows=0).columns
    recent_df = pd.read_csv("Data/creditcard.csv", skiprows=range(1, 50001), nrows=5000)
    recent_df.columns = header
    recent_features = recent_df.drop(columns=['Class', 'Time'])
    
    print("\nRunning Evidently AI Data Drift Report...")
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_features, current_data=recent_features)
    
    print("Drift check complete.")
    print("Forcing retraining anyway to demonstrate the automated pipeline...\n")
        
    trigger_retraining(recent_df)

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
        
        model_info = mlflow.sklearn.log_model(model, "model")
        
        model_name = "FraudScoringModel"
        print(f"\nRegistering new model as '{model_name}'...")
        registered_model = mlflow.register_model(model_info.model_uri, model_name)
        
        client = MlflowClient()
        # Set Alias to "Candidate"
        client.set_registered_model_alias(model_name, "Candidate", registered_model.version)
        print(f"Model version {registered_model.version} registered and set as 'Candidate' alias.")
        print("This Candidate is now ready for Shadow Testing against the incumbent Production model!")

if __name__ == "__main__":
    run_monitor_and_retrain()

import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from mlflow.tracking import MlflowClient
import os
import gc

def train_and_register_baseline():
    # Use a local SQLite database for MLflow to enable the Model Registry
    mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment("Fraud_Scoring_Baseline")

    print("Loading data for baseline model from PostgreSQL...")
    import db
    conn = db.get_connection()
    # Reduced from 50K to 20K — LogisticRegression converges fine with less data
    df = db.get_dataframe(conn, "SELECT * FROM historical_data ORDER BY Time LIMIT 20000")
    
    # Features and Target
    X = df.drop(columns=['Class', 'Time'])
    y = df['Class']
    del df  # Free the original DataFrame
    gc.collect()

    print(f"Training Logistic Regression on {len(X)} transactions (Frauds: {y.sum()})...")
    with mlflow.start_run() as run:
        # Deliberately basic model
        model = LogisticRegression(max_iter=1000, class_weight='balanced')
        model.fit(X, y)
        
        preds = model.predict(X)
        precision = precision_score(y, preds, zero_division=0)
        recall = recall_score(y, preds, zero_division=0)
        
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        
        print(f"Baseline Precision on training data: {precision:.4f}")
        print(f"Baseline Recall on training data: {recall:.4f}")
        
        # Free training data before model logging (which can spike memory)
        del X, y, preds
        gc.collect()
        
        # Log the model with explicit requirements to prevent OOM during environment inference
        model_info = mlflow.sklearn.log_model(model, "model", pip_requirements=["scikit-learn"])
        
        # Register the model
        model_name = "FraudScoringModel"
        print(f"Registering model as '{model_name}'...")
        registered_model = mlflow.register_model(model_info.model_uri, model_name)
        
        client = MlflowClient()
        # Set Alias to "Production"
        client.set_registered_model_alias(model_name, "Production", registered_model.version)
        print(f"Model version {registered_model.version} registered and set as Production alias.")
    
    # Final cleanup
    del model
    gc.collect()

if __name__ == "__main__":
    train_and_register_baseline()

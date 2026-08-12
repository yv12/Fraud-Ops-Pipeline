import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from mlflow.tracking import MlflowClient
import os

def train_and_register_baseline():
    # Use a local SQLite database for MLflow to enable the Model Registry
    mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment("Fraud_Scoring_Baseline")

    print("Loading data for baseline model...")
    # Load just the first 50,000 rows for the baseline to simulate starting from the past
    df = pd.read_csv("Data/creditcard.csv", nrows=50000)
    
    # Features and Target
    X = df.drop(columns=['Class', 'Time'])
    y = df['Class']

    print(f"Training Logistic Regression on {len(df)} transactions (Frauds: {y.sum()})...")
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
        
        # Log the model
        model_info = mlflow.sklearn.log_model(model, "model")
        
        # Register the model
        model_name = "FraudScoringModel"
        print(f"Registering model as '{model_name}'...")
        registered_model = mlflow.register_model(model_info.model_uri, model_name)
        
        client = MlflowClient()
        # Set Alias to "Production"
        client.set_registered_model_alias(model_name, "Production", registered_model.version)
        print(f"Model version {registered_model.version} registered and set as Production alias.")

if __name__ == "__main__":
    train_and_register_baseline()

web: uvicorn api:app --host 0.0.0.0 --port $PORT
mlflow: mlflow server -h 0.0.0.0 -p $PORT --backend-store-uri $DATABASE_URL --default-artifact-root /app/artifacts --serve-artifacts
monitor: python monitor_and_retrain.py
validate: python validate_and_promote.py

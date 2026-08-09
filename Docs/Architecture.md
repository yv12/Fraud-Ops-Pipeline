# System Architecture: Automated Fraud Scoring Pipeline

Based on the required capabilities, constraints (local machine, open-source only), and the goal of fully automating the model lifecycle without exposing live traffic to unproven models, here is the proposed architecture.

## 1. Technology Stack

Since this must run locally on a single machine and use free, open-source tools, we will use a lightweight Python-centric MLOps stack:

*   **Model Tracking & Registry:** **MLflow** 
    *   *Why:* Industry standard for tracking experiments, saving model artifacts, and managing model versions/stages (e.g., `Production`, `Staging`, `Archived`).
*   **Model Serving:** **FastAPI**
    *   *Why:* Fast, lightweight framework to serve the model as a REST API within the required latency budget.
*   **Data & Log Storage:** **DuckDB or SQLite**
    *   *Why:* Zero-setup, serverless databases perfect for local execution. Used to store incoming simulated transactions, their predictions, and delayed ground-truth labels.
*   **Monitoring & Drift Detection:** **Evidently AI**
    *   *Why:* Open-source library specifically designed to evaluate, test, and monitor ML models for data drift and concept drift.
*   **Pipeline Orchestration:** **Prefect** (or simple Python scheduled scripts)
    *   *Why:* To orchestrate the periodic monitoring, retraining, and validation jobs without manual intervention.

---

## 2. System Components & Capabilities

### A. The Simulator (Live Traffic Mock)
Since live traffic isn't available, a Python script will stream historical transactions from the dataset chronologically.
*   Sends "scoring requests" to the Serving API.
*   Sends "ground truth" (chargebacks/labels) to the database with a simulated delay.

### B. Serving API & Shadow Testing (FastAPI)
The API holds the models in memory to ensure low latency.
*   **Shadow Mode:** When a request arrives, the API loads both the `Production` model and the `Candidate` (Staging) model.
*   Both models score the transaction.
*   Only the `Production` score is returned to the simulated client.
*   Both scores (along with the model version IDs) are logged to the local database for auditability and risk-free testing.

### C. Monitoring Engine (Evidently AI)
Runs periodically to check the health of the `Production` model.
*   Compares the recent batch of incoming traffic against the model's original training data.
*   If data drift or a drop in simulated performance is detected, it raises a flag and triggers the retraining pipeline.

### D. Automated Retraining Pipeline
Triggered automatically by the Monitoring Engine.
*   Pulls the latest available historical data (including recent ground-truth labels).
*   Trains a new model.
*   Logs the data version, hyperparameters, and evaluation metrics to **MLflow**.
*   Registers the new model in MLflow and assigns it the `Staging` tag (making it the new Candidate).

### E. Validation & Promotion Job
Runs continuously or periodically to evaluate the `Candidate` model.
*   Compares the shadow scores of the `Candidate` model against the `Production` model on live traffic.
*   If the Candidate model demonstrably outperforms the incumbent over a statistically significant period, it is automatically promoted to `Production` in MLflow.
*   The Serving API polls MLflow and hot-reloads the new Production model without downtime.

---

## 3. Workflow Summary

1.  **Serve & Log:** FastAPI serves predictions, logging which version made which decision. It safely scores with the candidate model in the background.
2.  **Monitor:** Evidently AI watches for degradation in the background.
3.  **Trigger:** Upon degradation, a new model is trained and logged to MLflow as a Candidate.
4.  **Shadow:** The Candidate scores alongside Production without affecting real decisions.
5.  **Promote:** If the Candidate wins the shadow test, it is automatically promoted, and the cycle continues.

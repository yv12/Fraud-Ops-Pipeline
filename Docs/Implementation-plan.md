# Implementation Plan: Automated Fraud Scoring MLOps Pipeline

This plan breaks down the construction of the system detailed in `Architecture.md` and `problem-statement.md` into five logical phases. It incorporates the business logic for model promotion defined in `Word.md`.

## Phase 1: Project Initialization & Infrastructure
**Goal:** Set up the basic environment and the core data/tracking infrastructure.

1. **Environment Setup:** Create a Python virtual environment and install necessary open-source libraries (`fastapi`, `uvicorn`, `mlflow`, `duckdb`, `evidently`, `pandas`, `scikit-learn`).
2. **MLflow Initialization:** Configure a local MLflow tracking server to manage experiments and model versions.
3. **Database Schema Setup (DuckDB/SQLite):** 
   - Create a `transactions` table (raw incoming features).
   - Create a `predictions` table (stores model version, transaction ID, score, and whether it was a Production or Shadow prediction).
   - Create a `ground_truth` table (stores delayed actual labels, e.g., chargebacks).

## Phase 2: Baseline Model & Simulator
**Goal:** Get a basic model into the registry and build the mechanism to mimic the passage of time.

1. **Train Initial Baseline:** Use the earliest chronological slice of `creditcard.csv` to train a simple, deliberately basic model (e.g., Logistic Regression).
2. **Register Model:** Log this initial model to MLflow and tag it as `Production`.
3. **Build the Simulator:** Write a script that iterates through the remaining chronological rows in `creditcard.csv` to simulate the "real world". 
   - It will send transaction features via HTTP requests to our (soon-to-be-built) Serving API.
   - It will inject the actual class label (0 or 1) into the `ground_truth` table with a simulated delay (e.g., 7 days later).

## Phase 3: Model Serving API & Shadow Testing
**Goal:** Serve predictions in real-time and safely test unproven models without affecting the business.

1. **FastAPI Setup:** Create the REST API with a `/score` endpoint to receive transactions from the Simulator.
2. **Dynamic Loading:** The API reads MLflow on startup (and polls periodically) to hold the current `Production` model and `Candidate` model (if one exists) in memory.
3. **Shadow Scoring Logic:**
   - Transaction arrives.
   - `Production` model scores it.
   - `Candidate` model scores it (Shadow mode).
   - Both scores are written to the database along with their respective model IDs.
   - *Only* the `Production` decision is returned to the client/Simulator.

## Phase 4: Monitoring & Automated Retraining
**Goal:** Detect when the model goes stale and automatically generate a replacement.

1. **Monitoring Job (Evidently AI):** Create a script that runs periodically to evaluate recent transactions stored in the database.
   - Compares the distribution of recent features against the baseline training features to detect **Data Drift**.
2. **Retraining Pipeline:** 
   - Automatically triggered if the Monitoring Job detects significant drift.
   - Queries DuckDB for the latest available historical data and joined ground-truth labels.
   - Trains a new model on this fresh data.
   - Registers this new model into MLflow and transitions it to the `Candidate` (Staging) stage.

## Phase 5: Validation & Automated Promotion
**Goal:** Prove the new model is actually better using live traffic, then deploy it safely.

1. **Validation Job:** A script that evaluates the `Candidate` model by looking at its shadow predictions compared to actual ground truth that has finally trickled in.
2. **Evaluation Metrics (Product Logic):** Based on the criteria defined in `Word.md`, compare the incumbent and the candidate:
   - Calculate Precision and Recall for both models over the same recent timeframe.
   - **Promotion Rule:** `If (New Precision > Old Precision) AND (New Recall > Old Recall)` then the model is considered better.
3. **Automated Promotion:** If the rule passes, the script tells MLflow to transition the `Candidate` model to `Production`.
4. **Hot Reload:** The FastAPI server detects the state change in MLflow and seamlessly starts serving the new model as Production.

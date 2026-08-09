# Product & Business Logic

## 1. Metrics To decide if the New model is better than the last one:

Will depend on:
What the dataset says, say you have 2 classes: 0 for not fraud and 1 for fraud.

New model metrics should be better than old one:

* If new precision is > old precision and new recall is > old recall then new model is better.
* Better on what has to be decided by me because it is a product decision not code.

---

# System Walkthrough for Business Owners

This section explains in plain English exactly what the engineering team is building, how the data flows, and what each piece of technology does. It is designed so you can understand the exact logic and participate in the product decisions.

## Phase 1: The Foundation (What we just built)
**What it is:** We set up the digital "filing cabinets" and the environment where our AI models will live.
* **The Environment (Python):** We installed the necessary tools so our code can run securely on the server.
* **The Database (DuckDB):** This is our ledger. We created three specific tables (or spreadsheets):
  1. **Transactions:** Holds every single card swipe and its details (amount, time, etc.) *before* we know if it's fraud.
  2. **Predictions:** Records what our AI guessed about each transaction. Crucially, it records exactly *which* version of the model made the guess, so we have a permanent audit trail.
  3. **Ground Truth:** Holds the final answer. When a customer calls a week later to say "I didn't buy this!", that confirmed fraud report (chargeback) is saved here so we can grade our AI later.

## Phase 2: The Baseline & The Simulator
**What it is:** Creating our first simple AI and building a "time machine" to test it.
* **Baseline Model:** We take the earliest historical data and train a very basic AI model. This is our "Version 1.0". We register it in our tracking system (**MLflow**) so it's officially marked as the active `Production` model.
* **The Simulator:** Because we don't want to plug this directly into a real bank yet, we wrote a script that pretends to be the real world. It feeds historical transactions into our system one by one, exactly as they happened in real life, to simulate the passage of time.

## Phase 3: The Front Door & The "Shadow" Test
**What it is:** The reception desk that receives transactions and makes decisions safely.
* **The API (FastAPI):** This is the front door. The simulator knocks on the door and hands it a transaction.
* **Shadow Testing:** The API takes the transaction and asks the active `Production` model for a decision. It returns this decision to the simulator. 
* *However*, if we have a newer, unproven model (a `Candidate` model) waiting in the wings, the API secretly asks it for a decision too. It writes both decisions in our Database (from Phase 1). This allows us to see how the new model *would have* performed on real traffic without ever letting it make a real business decision.

## Phase 4: The Watchdog & Automatic Learning
**What it is:** An alarm system that notices when the world changes, and an automated factory that builds new AI to adapt.
* **The Monitor (Evidently AI):** Fraudsters change tactics constantly. This tool wakes up periodically, looks at the recent transactions in our Database, and compares them to the data our active model was originally trained on. If it sees that customer behavior or fraud patterns look completely different now (Data Drift), it sounds the alarm.
* **Automated Retraining:** When the alarm sounds, the system doesn't wait for a human. It immediately pulls all the freshest data (and recent ground truth chargebacks) from the Database, studies it, and trains a brand-new AI model. It saves this new model as a `Candidate` ready for shadow testing.

## Phase 5: The Judge (Automated Promotion)
**What it is:** The final exam. This phase decides if the new AI actually gets the job.
* **Validation:** The system looks at the Database to grade the `Candidate` model's secret "shadow" predictions against the actual Ground Truth that finally arrived weeks later.
* **The Product Decision:** It uses the exact business rules you defined at the top of this document: *Did both Precision AND Recall improve?* 
* **Promotion:** If the answer is yes, the system automatically fires the old model and promotes the `Candidate` to `Production`. From that second forward, the API starts using the new model for all live decisions.

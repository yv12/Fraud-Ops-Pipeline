# Edge Cases & Mitigation Strategies

Based on the proposed Architecture and Implementation Plan for the automated Fraud Scoring Pipeline, there are several edge cases and potential failure modes that the system must handle gracefully. This document outlines these scenarios from a product and business logic perspective.

## 1. System Reliability (Scoring Traffic)

### A. The Missing Candidate Model
* **Scenario:** When the system first turns on, or if a test model was recently removed, there might only be a main "Production" model making live decisions, and no new "Candidate" model ready for background testing.
* **Impact:** The system might get confused if it's expecting to test two models but only finds one, potentially causing a technical error that blocks real transactions.
* **Mitigation:** The system must be designed to check if a test model actually exists first. If it doesn't, it should smoothly skip the background test and just return the Production model's decision without any hiccups.

### B. Background Testing Slowing Down Real Decisions
* **Scenario:** The new "Candidate" model we are secretly testing in the background takes too long to analyze a transaction, or it completely crashes due to a bug.
* **Impact:** Because the system tests this new model at the exact same time it's scoring a real transaction, a crash in the test model could accidentally block or delay the final "Approve/Decline" decision for the actual customer.
* **Mitigation:** Background testing must be completely separated from the main customer flow (asynchronous). If the test model fails or takes too long, the system must ignore it and guarantee that the Production model's decision is delivered instantly.

## 2. Data & Retraining Edge Cases

### A. The "Late Ground Truth" Problem
* **Scenario:** The system realizes our current model is getting worse at catching fraud, so it automatically decides to build a new one. It pulls data from the last 30 days to learn from. However, actual fraud reports (chargebacks) take weeks to arrive from the bank. 
* **Impact:** If the system trains on data from the last 2 weeks, it will mistakenly assume all those transactions were "safe" because the chargebacks haven't arrived yet. The new model will learn the wrong patterns (training on false negatives).
* **Mitigation:** The system must only learn from "mature" data (e.g., transactions older than 30 or 60 days). This ensures we have a complete and accurate picture of what was truly fraud before teaching the model.

### B. Missing Information in Real-Time
* **Scenario:** An upstream payment system has a glitch, and an incoming transaction arrives missing a normal piece of information (like the customer's location or the transaction amount).
* **Impact:** The model doesn't know how to handle the blank space and breaks, potentially declining a perfectly legitimate transaction by default.
* **Mitigation:** The system must validate incoming data before scoring it. If something non-critical is missing, it should have a backup plan (like filling in an average value) rather than failing outright.

## 3. Product Rules & Model Promotion

### A. The Stagnation Trap (Metrics Conflict)
* **Scenario:** Our business rule (from `Word.md`) states that a new model is only promoted to Production if it is better at catching fraud (higher Recall) **AND** better at not bothering good customers (higher Precision). 
* **Impact:** In reality, there is almost always a trade-off: catching more fraud usually means slightly more false alarms. It is extremely rare for a new model to perfectly beat the old model on *both* metrics at the exact same time. If we enforce this strict rule, new models will constantly be rejected, and our system will stagnate while fraudsters adapt.
* **Mitigation:** We need a more flexible product rule. For example, we might require that a new model catches more fraud (Recall improves), but only enforce that the false alarm rate (Precision) stays above a minimally acceptable baseline, rather than demanding it strictly beats the old one.

### B. Forgetting the Past
* **Scenario:** To stay fresh, the pipeline automatically builds a new model using only the most recent two months of data.
* **Impact:** The model becomes an expert at catching today's fraud but completely forgets how to catch seasonal fraud (like Black Friday scams) that happened 8 months ago.
* **Mitigation:** The system should always mix in a "golden dataset"—a hand-picked collection of historical, classic fraud cases—whenever it learns. This ensures it doesn't lose its memory of past attack strategies.

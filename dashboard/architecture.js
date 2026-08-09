// Step explanations (plain English for business owners)
const stepInfo = {
    "arch-simulator": {
        title: "Step 1 — Simulator (Live Traffic Source)",
        text: "In production, this would be your real payment gateway. For our demo, a simulator script picks a real transaction from the dataset and sends it to our system every 1-2 seconds — exactly how a customer swiping their card would work.",
        color: "glow"
    },
    "arch-api": {
        title: "Step 2 — API Gateway (Front Door)",
        text: "Every transaction enters through this single door. The FastAPI server receives it, logs it into the database, and then asks BOTH models to score it. Only the Production model's answer goes back to the customer.",
        color: "glow"
    },
    "arch-prod": {
        title: "Step 3a — Production Model (Fraud Detector)",
        text: "This is the model protecting your business RIGHT NOW. It calculates a risk score from 1 to 99. If the score is 50+, it BLOCKS the transaction as FRAUD (red). Its decisions are final and affect real customers.",
        color: "glow-red"
    },
    "arch-cand": {
        title: "Step 3b — Candidate Model (Silent Challenger)",
        text: "This model was trained on fresher data. But we don't trust it yet! It scores every transaction silently in the background. Its answers are recorded but NEVER used for real decisions until it proves it's better.",
        color: "glow"
    },
    "arch-db": {
        title: "Step 4 — DuckDB Ledger (Permanent Record)",
        text: "Every piece of data is permanently recorded: the transaction, what Production predicted, what the Candidate predicted, and eventually the ground truth (was it actually fraud?). This is your complete audit trail.",
        color: "glow"
    },
    "arch-monitor": {
        title: "Step 5 — Drift Monitor (The Watchdog)",
        text: "Fraud patterns change constantly. This component uses Evidently AI to compare today's transactions against historical data. If fraud patterns have shifted significantly, it raises the alarm and triggers an automatic retrain.",
        color: "glow"
    },
    "arch-retrain": {
        title: "Step 6 — Retrain Pipeline (The Builder)",
        text: "When the Watchdog detects drift, this pipeline automatically pulls latest data, trains a brand-new model, and registers it in MLflow as a Candidate. No engineer needs to lift a finger.",
        color: "glow-green"
    },
    "arch-judge": {
        title: "Step 7 — The Judge (Your Product Rule)",
        text: "This is YOUR business rule in action. It compares the Candidate vs Production using real ground truth. If the new model has BOTH higher Precision AND Recall, it wins. Otherwise, it's REJECTED. No unproven model ever touches live traffic.",
        color: "glow-red"
    },
    "arch-mlflow": {
        title: "Step 8 — MLflow Registry (Model Vault)",
        text: "The vault that stores every model version ever trained with its metrics. Models are tagged 'Production' or 'Candidate'. When the Judge promotes a winner, MLflow swaps the tags and the API auto-loads the new champion within seconds.",
        color: "glow"
    }
};

// Animation order
const animOrder = [
    "arch-simulator", "arch-api", "arch-prod", "arch-cand",
    "arch-db", "arch-monitor", "arch-retrain", "arch-judge", "arch-mlflow"
];

let animStep = 0;

function animateFlow() {
    const id = animOrder[animStep];
    const info = stepInfo[id];
    const node = document.getElementById(id);
    if (!node || !info) return;

    // Clear all glows
    document.querySelectorAll(".arch-node").forEach(n => {
        n.classList.remove("glow", "glow-green", "glow-red");
    });

    // Light up this node with the right color
    node.classList.add(info.color);

    // Update the explanation panel
    document.getElementById("step-title").innerText = info.title;
    document.getElementById("step-text").innerText = info.text;

    animStep = (animStep + 1) % animOrder.length;
}

// Click handler
document.querySelectorAll(".arch-node").forEach(node => {
    node.addEventListener("click", () => {
        const id = node.id;
        const info = stepInfo[id];
        if (!info) return;

        document.getElementById("step-title").innerText = info.title;
        document.getElementById("step-text").innerText = info.text;

        document.querySelectorAll(".arch-node").forEach(n => {
            n.classList.remove("glow", "glow-green", "glow-red");
        });

        node.classList.add(info.color);
    });
});

// Auto-play the flow every 3 seconds
setInterval(animateFlow, 3000);

// First animation fires immediately
setTimeout(animateFlow, 300);

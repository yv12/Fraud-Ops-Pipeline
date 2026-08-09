const connectionStatus = document.getElementById('connection-status');
const incomingNode = document.getElementById('node-incoming');
const incomingAmount = document.getElementById('incoming-amount');
const dbNode = document.getElementById('node-database');

const cardProd = document.getElementById('card-production');
const scoreProd = document.getElementById('prod-score');
const decProd = document.getElementById('prod-decision');
const verProd = document.getElementById('prod-version');
const metProd = document.getElementById('prod-metrics');

const cardCand = document.getElementById('card-candidate');
const scoreCand = document.getElementById('cand-score');
const decCand = document.getElementById('cand-decision');
const verCand = document.getElementById('cand-version');
const metCand = document.getElementById('cand-metrics');

const terminal = document.getElementById('terminal');
const txCounter = document.getElementById('tx-counter');

let totalTransactions = 0;

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = () => {
        connectionStatus.classList.remove('red');
        connectionStatus.classList.add('green');
        logTerminal('SYSTEM', 'Connected to WebSocket stream');
    };

    ws.onclose = () => {
        connectionStatus.classList.remove('green');
        connectionStatus.classList.add('red');
        logTerminal('SYSTEM', 'Disconnected. Reconnecting in 3s...');
        setTimeout(connect, 3000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "INIT") {
            // Restore state from background so it doesn't reset on refresh!
            totalTransactions = data.total_count;
            txCounter.innerText = totalTransactions;
            
            terminal.innerHTML = ""; // Clear existing
            data.recent_logs.forEach(log => logTerminalTx(log));
            
            if (data.recent_logs.length > 0) {
                const last = data.recent_logs[data.recent_logs.length - 1];
                updateModel(cardProd, scoreProd, decProd, verProd, metProd, last.prod_prob, last.prod_decision, last.prod_version, last.prod_metrics);
                if (last.cand_prob !== null) {
                    cardCand.style.opacity = '1';
                    updateModel(cardCand, scoreCand, decCand, verCand, metCand, last.cand_prob, last.cand_decision, last.cand_version, last.cand_metrics);
                }
            }
        } else {
            // New live transaction
            processTransaction(data);
        }
    };
}

async function processTransaction(data) {
    totalTransactions = data.total_count;
    txCounter.innerText = totalTransactions;

    incomingAmount.innerText = `$${data.amount.toFixed(2)}`;
    incomingNode.classList.add('active');
    
    setTimeout(() => {
        updateModel(cardProd, scoreProd, decProd, verProd, metProd, data.prod_prob, data.prod_decision, data.prod_version, data.prod_metrics);
        
        if (data.cand_prob !== null) {
            cardCand.style.opacity = '1';
            updateModel(cardCand, scoreCand, decCand, verCand, metCand, data.cand_prob, data.cand_decision, data.cand_version, data.cand_metrics);
        } else {
            cardCand.style.opacity = '0.3';
            decCand.innerText = 'OFFLINE';
            metCand.innerText = `Precision: --% | Recall: --%`;
        }
        
        logTerminalTx(data);
        
        setTimeout(() => {
            dbNode.classList.add('active');
            setTimeout(() => {
                incomingNode.classList.remove('active');
                dbNode.classList.remove('active');
            }, 500);
        }, 300);
    }, 200);
}

function updateModel(card, scoreEl, decEl, verEl, metEl, prob, decision, version, metrics) {
    verEl.innerText = version ? `v${version}` : 'v?';
    
    let score = Math.round(prob * 100);
    if (score < 1) score = 1;
    if (score > 99) score = 99;
    scoreEl.innerText = score;
    
    if (metrics) {
        metEl.innerText = `Precision: ${(metrics.precision * 100).toFixed(1)}% | Recall: ${(metrics.recall * 100).toFixed(1)}%`;
    } else {
        metEl.innerText = `Precision: --% | Recall: --%`;
    }
    
    card.classList.remove('fraud', 'normal');
    
    if (decision === 1) {
        card.classList.add('fraud');
        decEl.innerText = 'FRAUD';
    } else {
        card.classList.add('normal');
        decEl.innerText = 'NORMAL';
    }
}

function logTerminal(type, msg) {
    const time = new Date().toISOString().split('T')[1].substring(0, 12);
    const div = document.createElement('div');
    div.className = 'log-line';
    div.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-id">[${type}]</span> ${msg}`;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
    
    if (terminal.childElementCount > 100) {
        terminal.removeChild(terminal.firstChild);
    }
}

function logTerminalTx(data) {
    const time = new Date().toISOString().split('T')[1].substring(0, 12);
    const id = data.transaction_id.substring(0, 8);
    
    let prodResult = data.prod_decision === 1 ? '<span class="log-fraud">FRAUD</span>' : '<span class="log-normal">OK</span>';
    let candResult = data.cand_prob === null ? 'N/A' : (data.cand_decision === 1 ? '<span class="log-fraud">FRAUD</span>' : '<span class="log-normal">OK</span>');
    
    let msg = `TX_${id} | Amt: $${data.amount.toFixed(2).padStart(8, ' ')} | Prod: ${prodResult} | Cand: ${candResult}`;
    
    const div = document.createElement('div');
    div.className = 'log-line';
    div.innerHTML = `<span class="log-time">[${time}]</span> ${msg}`;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
    
    if (terminal.childElementCount > 100) {
        terminal.removeChild(terminal.firstChild);
    }
}

connect();

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import json
from fastapi.responses import HTMLResponse

app = FastAPI()

class Entry(BaseModel):
    category: str  
    value: str     
    note: str      

@app.get("/")
def home():
    return {"message": "NeuroTrack Life OS is active"}

@app.get("/mobile", response_class=HTMLResponse)
def mobile_interface():
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: 'Courier New', monospace; 
                    background: #f0f0f0; /* Slight grey background to make the card pop on desktop */
                    color: black; 
                    padding: 0; 
                    margin: 0; 
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    min-height: 100vh;
                }
                .container { 
                    width: 100%;
                    max-width: 500px; /* Keeps it 'app-sized' on desktop */
                    background: white;
                    border: 2px solid black; 
                    padding: 30px; 
                    box-sizing: border-box;
                    margin-top: 20px;
                    margin-bottom: 20px;
                    box-shadow: 10px 10px 0px black; /* Brutalist design shadow */
                }
                h2 { 
                    border-bottom: 2px solid black; 
                    padding-bottom: 10px; 
                    text-transform: uppercase; 
                    letter-spacing: 2px; 
                    margin-top: 0; 
                }
                label { display: block; margin: 15px 0 5px; font-weight: bold; text-transform: uppercase; font-size: 0.8rem; }
                input, textarea { 
                    width: 100%; 
                    padding: 12px; 
                    background: white; 
                    color: black; 
                    border: 1px solid black; 
                    border-radius: 0; 
                    box-sizing: border-box; 
                    font-family: 'Courier New', monospace; 
                    margin-bottom: 10px;
                }
                .btn-group { margin-top: 10px; }
                button { 
                    width: 100%; 
                    padding: 15px; 
                    font-size: 1rem; 
                    font-weight: bold; 
                    border: 2px solid black; 
                    cursor: pointer; 
                    margin-bottom: 10px; 
                    text-transform: uppercase; 
                    transition: 0.1s; 
                    font-family: 'Courier New', monospace; 
                }
                .btn-save { background: black; color: white; }
                .btn-history { background: white; color: black; }
                button:active { transform: translate(2px, 2px); }
                
                #history-display { 
                    margin-top: 20px; 
                    font-size: 0.8rem; 
                    border-top: 1px dashed black; 
                    padding-top: 10px; 
                    display: none; 
                }
                .log-item { border-bottom: 1px dotted #ccc; padding: 10px 0; line-height: 1.4; }

                /* Desktop Adjustments */
                @media (min-width: 768px) {
                    body { align-items: center; } /* Centers the app vertically on desktop */
                    .container { margin-top: 0; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>NeuroTrack</h2>
                
                <label>Category</label>
                <input id="cat" placeholder="HYBRID FIT / TRADE / HABIT">
                
                <label>Value</label>
                <input id="val" placeholder="ACTIVITY OR ASSET">
                
                <label>Notes</label>
                <textarea id="note" rows="3" placeholder="INTERNAL WORLD OBSERVATIONS..."></textarea>
                
                <div class="btn-group">
                    <button class="btn-save" onclick="log()">Save Entry</button>
                    <button class="btn-history" onclick="toggleHistory()">View History</button>
                </div>

                <div id="history-display"></div>
            </div>

            <script>
                async function log() {
                    const data = {
                        category: document.getElementById('cat').value,
                        value: document.getElementById('val').value,
                        note: document.getElementById('note').value
                    };
                    const response = await fetch('/log', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    if (response.ok) {
                        alert('LOGGED.');
                        document.getElementById('val').value = '';
                        document.getElementById('note').value = '';
                        if(document.getElementById('history-display').style.display === 'block') loadHistory();
                    }
                }

                async function loadHistory() {
                    const res = await fetch('/history');
                    const json = await res.json();
                    const display = document.getElementById('history-display');
                    display.innerHTML = '<strong>RECENT LOGS:</strong><br>';
                    json.data.slice(-5).reverse().forEach(item => {
                        display.innerHTML += `<div class="log-item"><strong>${item.time}</strong><br>${item.category}: ${item.value}<br><em>${item.note}</em></div>`;
                    });
                }

                function toggleHistory() {
                    const display = document.getElementById('history-display');
                    if (display.style.display === 'none' || display.style.display === '') {
                        display.style.display = 'block';
                        loadHistory();
                    } else {
                        display.style.display = 'none';
                    }
                }
            </script>
        </body>
    </html>
    """

@app.post("/log")
def log_entry(entry: Entry):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_data = {
        "time": timestamp,
        "category": entry.category,
        "value": entry.value,
        "note": entry.note
    }

    with open("neuro_track_master.json", "a") as f:
        f.write(json.dumps(log_data) + "\n")
    
    return {"status": "Logged successfully", "entry": log_data}

@app.get("/history")
def get_history():
    history = []
    try:
        with open("neuro_track_master.json", "r") as f:
            for line in f:
                history.append(json.loads(line))
    except FileNotFoundError:
        return {"message": "No logs yet. Start tracking your journey!"}
    
    return {"total_logs": len(history), "data": history}
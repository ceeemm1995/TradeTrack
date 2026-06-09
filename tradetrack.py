import os
import sys
import json
from fastapi import FastAPI, Response, Cookie, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from google import genai
from dotenv import load_dotenv
from google.api_core import exceptions
from fastapi import Request
from fastapi.staticfiles import StaticFiles

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
USERS_FILE = "users.json"
TRADES_FILE = "trade_track.json"

load_dotenv()

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

static_dir = os.path.join(base_path, "static")

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app = FastAPI()

app.mount("/static", StaticFiles(directory=static_dir), name="static")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY is missing from your environment setup!")

ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) if GEMINI_API_KEY else None

class UserSignup(BaseModel):
    username: str
    password: str
    nickname: str
    birth: str
    email: str
    capital: float

class CapitalUpdate(BaseModel):
    amount: float

class UserLogin(BaseModel):
    username: str
    password: str

class Entry(BaseModel):
    date: str
    pnl: float
    note: str

class ChatRequest(BaseModel):
    message: str


def get_users():
    if not os.path.exists(USERS_FILE): return {}
    with open(USERS_FILE, "r") as f: return json.load(f)

def get_trades():
    if not os.path.exists(TRADES_FILE): return []
    with open(TRADES_FILE, "r") as f:
        try: return json.load(f)
        except: return []

@app.get("/", response_class=HTMLResponse)
def auth_page():
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Courier New', monospace; background: #e7e7e7; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
                .card { background: white; border: 2px solid black; padding: 30px; box-shadow: 8px 8px 0px black; width: 320px; }
                input { width: 100%; padding: 10px; margin: 5px 0 15px 0; border: 2px solid black; box-sizing: border-box; font-family: inherit; }
                button { width: 100%; padding: 12px; background: black; color: white; border: none; cursor: pointer; font-weight: bold; margin-bottom: 10px; }
                label { font-size: 0.7rem; font-weight: bold; display: block; }
                .toggle-link { text-align: center; font-size: 0.8rem; cursor: pointer; text-decoration: underline; margin-top: 10px; }
                h2 { margin-top: 0; text-align: center; }
            </style>
        </head>
        <body>
            <div class="card">
                <div style="text-align: center; margin-bottom: 20px;">
                <img src="/static/tradetrack_logo.png" alt="TradeTrack Logo" style="width: 100px; height: auto; border-radius: 8px;">
            </div>
                <label>USERNAME</label><input id="u" placeholder="Required">
                <label>PASSWORD</label><input id="p" type="password" placeholder="Required">
                <div id="signup-fields" style="display:none;">
                    <label>NICKNAME</label><input id="nickname" placeholder="What should we call you?">
                    <label>BIRTH DATE</label><input id="birth" type="date">
                    <label>EMAIL</label><input id="email" type="email" placeholder="email@example.com">
                    <label>INITIAL CAPITAL ($)</label><input id="capital" type="number" placeholder="e.g. 1000">
                </div>
                <button onclick="submitAuth()">GO</button>
                <p class="toggle-link" onclick="toggleMode()" id="toggle-text">Need an account? Sign Up</p>
            </div>
            <script>
                let isSignup = false;
                function toggleMode() {
                    isSignup = !isSignup;
                    document.getElementById('title').innerText = isSignup ? "SIGN UP" : "LOG IN";
                    document.getElementById('signup-fields').style.display = isSignup ? "block" : "none";
                    document.getElementById('toggle-text').innerText = isSignup ? "Already have an account? Log In" : "Need an account? Sign Up";
                }
                async function submitAuth() {
                    const type = isSignup ? 'signup' : 'login';
                    const payload = {
                        username: document.getElementById('u').value,
                        password: document.getElementById('p').value
                    };
                    if (isSignup) {
                        payload.nickname = document.getElementById('nickname').value;
                        payload.birth = document.getElementById('birth').value;
                        payload.email = document.getElementById('email').value;
                        payload.capital = parseFloat(document.getElementById('capital').value) || 0;
                    }
                    const res = await fetch('/' + type, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) { window.location.href = "/mobile"; } 
                    else { const err = await res.json(); alert(err.detail); }
                }
            </script>
        </body>
    </html>
    """

@app.post("/signup")
def signup(user: UserSignup, response: Response):
    users = get_users()
    if user.username in users: raise HTTPException(status_code=400, detail="Username exists")
    users[user.username] = {
        "hashed_password": pwd_context.hash(user.password[:72]),
        "nickname": user.nickname,
        "birth": user.birth,
        "email": user.email,
        "initial_capital": user.capital
    }
    with open(USERS_FILE, "w") as f: json.dump(users, f)
    response.set_cookie(key="session_user", value=user.username)
    return {"status": "Created"}

@app.post("/login")
def login(user: UserLogin, response: Response):
    users = get_users()
    u_data = users.get(user.username)
    if u_data and pwd_context.verify(user.password, u_data["hashed_password"]):
        response.set_cookie(key="session_user", value=user.username)
        return {"status": "OK"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_user")
    return response

@app.get("/mobile", response_class=HTMLResponse)
def mobile_interface(session_user: str = Cookie(None)):
    if not session_user: return RedirectResponse(url="/")
    users = get_users()
    user_info = users.get(session_user, {})
    nickname = user_info.get("nickname", session_user)

    return f"""
    <html>
    <head>
        <title>Trade Track</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Courier New', monospace; background: #e7e7e7; margin: 0; padding: 10px; }}
            .container {{ max-width: 500px; margin: auto; background: white; border: 2px solid black; padding: 20px; box-shadow: 8px 8px 0px black; }}
            header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid black; margin-bottom: 15px; padding-bottom: 10px; }}
            .card {{ border: 2px solid black; padding: 15px; margin-bottom: 15px; background: #fff; }}
            input, textarea {{ width: 100%; padding: 10px; margin: 5px 0 10px 0; border: 2px solid black; box-sizing: border-box; font-family: inherit; }}
            button {{ width: 100%; padding: 12px; background: black; color: white; border: none; font-weight: bold; cursor: pointer; }}
            .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; background: black; border: 1px solid black; }}
            .day-header {{ background: black; color: white; text-align: center; padding: 5px 0; font-size: 0.6rem; }}
            .day-cell {{ background: white; aspect-ratio: 1 / 1; padding: 2px; font-size: 0.7rem; min-height: 50px; overflow-y: auto; }}
            .pnl-tag {{ font-size: 0.5rem; padding: 1px; margin-top: 1px; text-align: center; font-weight: bold; }}
            .win {{ background: #d4edda; color: #155724; }}
            .loss {{ background: #f8d7da; color: #721c24; }}
            .history-item {{ border-bottom: 1px dashed black; padding: 10px 0; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center; }}
            .chat-messages {{ height: 180px; overflow-y: auto; border: 2px solid black; padding: 8px; background: #fafafa; margin-bottom: 10px; font-size: 0.8rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <strong>{nickname.upper()}</strong>
                <a href="/logout" style="color:red; text-decoration:none; font-size:0.8rem;">LOGOUT</a>
            </header>

            <div class="card">
                <label style="font-size: 0.7rem; font-weight: bold;">ADJUST INITIAL CAPITAL ($)</label>
                <div style="display: flex; gap: 5px;">
                    <input id="cap-input" type="number" placeholder="New Capital">
                    <button style="width: 80px;" onclick="updateCapital()">SET</button>
                </div>
            </div>

            <div id="summary" class="card" style="text-align: center; background: #ffff00;">Loading Summary...</div>

            <div class="card">
                <strong style="font-size: 0.8rem;">ASK TRADETRACK AI</strong>
                <div class="chat-messages" id="chat-box">
                    <div><span style="color:#555;">AI: Ask me anything about your logic, symmetry patterns, or code.</span></div>
                </div>
                <div style="display: flex; gap: 5px;">
                    <input id="chat-input" placeholder="Type a message..." onkeydown="if(event.key==='Enter') askAI()">
                    <button style="width: 80px;" onclick="askAI()">ASK</button>
                </div>
            </div>

            <div class="card">
                <strong style="font-size: 0.8rem;">LOG TRADE</strong>
                <input type="date" id="log-date">
                <input type="number" id="log-pnl" placeholder="PnL (e.g. 50 or -20)">
                <textarea id="log-note" placeholder="Insights..."></textarea>
                <button onclick="saveLog()">POST LOG</button>
            </div>

            <div class="calendar-grid" id="calendar"></div>

            <div class="card" style="margin-top: 20px;">
                <strong style="font-size: 0.8rem;">RECENT LOGS</strong>
                <div id="log-list"></div>
            </div>
        </div>

        <script>
            document.getElementById('log-date').valueAsDate = new Date();

            async function askAI() {{
                const input = document.getElementById('chat-input');
                const box = document.getElementById('chat-box');
                const text = input.value.trim();
                if(!text) return;

                box.innerHTML += `<div style="margin-top:4px;"><strong>YOU:</strong> ${{text}}</div>`;
                input.value = '';
                box.scrollTop = box.scrollHeight;

                try {{
                    const res = await fetch('/chat', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ message: text }})
                    }});
                    const data = await res.json();
                    if(res.ok) {{
                        // FIXED: Changed data.reply to data.reply to match updated backend key
                        box.innerHTML += `<div style="margin-top:4px; color:#0055ff;"><strong>AI:</strong> ${{data.reply}}</div>`;
                    }} else {{
                        box.innerHTML += `<div style="margin-top:4px; color:red;"><strong>AI:</strong> ${{data.detail || 'Error processing request.'}}</div>`;
                    }}
                }} catch(e) {{
                    box.innerHTML += `<div style="margin-top:4px; color:red;"><strong>AI:</strong> Connection lost.</div>`;
                }}
                box.scrollTop = box.scrollHeight;
            }}

            async function updateCapital() {{
                const amount = document.getElementById('cap-input').value;
                if(!amount) return;
                await fetch('/update_capital', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ amount: parseFloat(amount) }})
                }});
                loadDashboard();
            }}

            async function saveLog() {{
                const data = {{
                    date: document.getElementById('log-date').value,
                    pnl: parseFloat(document.getElementById('log-pnl').value) || 0,
                    note: document.getElementById('log-note').value
                }};
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                document.getElementById('log-pnl').value = '';
                document.getElementById('log-note').value = '';
                loadDashboard();
            }}

            async function deleteLog(index) {{
                if(confirm("Delete this log?")) {{
                    await fetch('/delete_log/' + index, {{ method: 'DELETE' }});
                    loadDashboard();
                }}
            }}

            async function loadDashboard() {{
                const res = await fetch('/history');
                const history = await res.json();
                const trades = history.data || [];
                const initialCapital = history.initial_capital || 0;

                let totalPnl = 0;
                trades.forEach(t => totalPnl += t.pnl);
                const currentBalance = initialCapital + totalPnl;
                
                document.getElementById('summary').innerHTML = `
                    <div style="font-size: 0.7rem;">ACCOUNT BALANCE</div>
                    <div style="font-size: 1.5rem; font-weight: bold;">$${{currentBalance.toFixed(2)}}</div>
                    <div style="font-size: 0.7rem; margin-top: 5px;">
                        START: $${{initialCapital.toFixed(2)}} | 
                        <span style="color: ${{totalPnl >= 0 ? 'green' : 'red'}}">
                            ${{totalPnl >= 0 ? '+$' : '-$'}}${{Math.abs(totalPnl).toFixed(2)}}
                        </span>
                    </div>
                `;

                const calendar = document.getElementById('calendar');
                calendar.innerHTML = '';
                ['S','M','T','W','T','F','S'].forEach(d => calendar.innerHTML += `<div class="day-header">${{d}}</div>`);

                const now = new Date();
                const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
                const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).getDay();

                for(let i=0; i<firstDay; i++) calendar.innerHTML += '<div class="day-cell"></div>';
                
                for(let d=1; d<=daysInMonth; d++) {{
                    const dateStr = `${{now.getFullYear()}}-${{String(now.getMonth()+1).padStart(2,'0')}}-${{String(d).padStart(2,'0')}}`;
                    const dayTrades = trades.filter(t => t.date === dateStr);
                    let dayHtml = '';
                    dayTrades.forEach(t => {{
                        dayHtml += `<div class="pnl-tag ${{t.pnl >= 0 ? 'win' : 'loss'}}">${{t.pnl >= 0 ? '+' : ''}}${{t.pnl}}</div>`;
                    }});
                    calendar.innerHTML += `<div class="day-cell"><div>${{d}}</div>${{dayHtml}}</div>`;
                }}

                const list = document.getElementById('log-list');
                list.innerHTML = '';
                trades.slice().reverse().forEach((t, idx) => {{
                    const realIdx = trades.length - 1 - idx;
                    list.innerHTML += `
                        <div class="history-item">
                            <div>
                                <strong>${{t.date}}</strong>: ${{t.pnl >= 0 ? '+$' : '-$'}}${{Math.abs(t.pnl)}}<br>
                                <small>${{t.note || 'No insights'}}</small>
                            </div>
                            <button onclick="deleteLog(${{realIdx}})" style="width: 35px; height: 35px; background: red; padding: 0;">X</button>
                        </div>
                    `;
                }});
            }}
            loadDashboard();
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: Request):
    
    try:
        data = await request.json()
        user_message = data.get("message", "")
        
        username = data.get("username", "Guest")
    except Exception:
        try:
            
            body = await request.body()
            user_message = body.decode("utf-8").strip()
            username = "Guest"
        except Exception:
            return {"reply": "I didn't catch that. Could you try retyping your message?"}

    if not user_message:
        return {"reply": "The message appears to be empty. What's on your mind?"}

    if not ai_client:
        return {"reply": "AI Service is currently unconfigured on this host."}

    user_trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f:
                all_trades = json.load(f)
                if isinstance(all_trades, list):
                    user_trades = [t for t in all_trades if t.get("user") == username]
                elif isinstance(all_trades, dict):
                    user_trades = all_trades.get(username, [])
        except Exception as e:
            print(f"File read fallback error: {e}")
            user_trades = []

    history_context = f"User History: {json.dumps(user_trades)}" if user_trades else "No trades recorded yet."
    full_prompt = (
        f"You are TradeTrack AI. An assistant for an independent market trader. "
        f"Review their logged history metrics if available and answer concisely.\n\n"
        f"{history_context}\n\n"
        f"User Question: {user_message}"
    )

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=full_prompt
        )
        return {"reply": response.text}
        
    except exceptions.ResourceExhausted as e:
        print(f"Gemini API Quota Exceeded: {e}")
        return {"reply": "The AI service is currently rate-limited or out of API quota. Please wait a bit before trying again."}
    except Exception as e:
        print(f"Gemini API Exception: {e}")
        return {"reply": "Connected, but Gemini encountered an error processing this request."}
    
@app.post("/log")
def log_entry(entry: Entry, session_user: str = Cookie(None)):
    if not session_user: raise HTTPException(status_code=401)
    history = get_trades()
    history.append({
        "user": session_user,
        "date": entry.date,
        "pnl": entry.pnl,
        "note": entry.note
    })
    with open(TRADES_FILE, "w") as f: json.dump(history, f)
    return {"status": "ok"}

@app.get("/history")
def get_history(session_user: str = Cookie(None)):
    if not session_user: return {"data": [], "initial_capital": 0}
    users = get_users()
    user_data = users.get(session_user, {})
    initial_cap = user_data.get("initial_capital", 0)
    
    trades = get_trades()
    user_trades = [t for t in trades if t.get("user") == session_user]
    return {"data": user_trades, "initial_capital": initial_cap}

@app.post("/update_capital")
def update_capital(data: CapitalUpdate, session_user: str = Cookie(None)):
    if not session_user: raise HTTPException(status_code=401)
    users = get_users()
    if session_user in users:
        users[session_user]["initial_capital"] = data.amount
        with open(USERS_FILE, "w") as f: json.dump(users, f)
    return {"status": "ok"}

@app.delete("/delete_log/{index}")
def delete_log(index: int, session_user: str = Cookie(None)):
    if not session_user: raise HTTPException(status_code=401)
    trades = get_trades()
    user_trade_indices = [i for i, t in enumerate(trades) if t.get("user") == session_user]
    
    if index < len(user_trade_indices):
        actual_list_index = user_trade_indices[index]
        trades.pop(actual_list_index)
        with open(TRADES_FILE, "w") as f: json.dump(trades, f)
    return {"status": "ok"}
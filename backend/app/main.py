from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, json, logging
from datetime import datetime
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="LLM LeakGuard Enterprise")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dev frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Config ----------
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "logs.jsonl"

BLOCK_THRESHOLD = float(os.getenv("BLOCK_THRESHOLD", "0.75"))

# ---------- Logging ----------
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(message)s"
)

# ---------- Threat Patterns (single source of truth) ----------
THREAT_PATTERNS = {
    # Phishing-ish
    "phishing": r"(?=.*\b(bank|paypal|upi|wallet|pan|aadhaar|kyc)\b)(?=.*\b(login|sign\s?in|verify|click|download|reset|update)\b)",

    #govt ids (demo)
    "gov_id_bait": r"\b(pan\s*card|aadhaar|kyc)\b.*\b(download|click|verify|update)\b",

    # Secrets/credentials (covers: password=123, password:123, password is 123)
    "secrets": r"\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*(?:[:=]|is)\s*([^\s,;]+)",

    #PAN Cards
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    # Common tokens (demo)
    "github_token": r"\bghp_[A-Za-z0-9]{30,}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",

    # AWS Access Key ID (AKIA/ASIA etc) demo
    "aws_key": r"\b(AKI|ASIA)[A-Z0-9]{16}\b",

    # Email addresses
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

    # Aadhaar-ish (12 digits spaced/not) demo
    "aadhaar_like": r"\b\d{4}\s?\d{4}\s?\d{4}\b",

    # Card-ish (13-19 digits) demo (false positives possible)
    "card_like": r"\b(?:\d[ -]*?){13,19}\b",

    # OTP/PIN/CVV with digits (covers: OTP=123456, otp is 252584)
    "otp": r"\b(otp|one[-\s]?time\s?password|cvv|pin)\b\s*(?:[:=]|is)?\s*\d{4,8}\b",

    # Malware-ish commands
    "malware": r"(bash\s+-i)|(curl\s+.*\|\s*bash)|(powershell\s+-enc)",

    # SQLi-ish
    "sql": r"(\bunion\b\s+\bselect\b)|(\bOR\b\s+1=1)|('?\s*OR\s*'?\d'?\s*=\s*'?\d)",

    # Tor-ish indicators
    "tor": r"(\.onion\b)|(185\.220\.)",

    # Weak brute-force patterns (demo)
    "brute": r"\b(admin|password123|qwerty|letmein)\b",
}

SEVERITY = {
    "gov_id_bait": 0.8,   # make it block (threshold 0.75)
    "pan": 0.9,
    "phishing": 0.8,      # make phishing block too
    "secrets": 0.9,
    "github_token": 0.95,
    "jwt": 0.85,
    "aws_key": 0.95,
    "email": 0.5,
    "aadhaar_like": 0.95,
    "card_like": 0.95,
    "otp": 0.8,
    "malware": 0.95,
    "sql": 0.85,
    "tor": 0.6,
    "brute": 0.6,
}


# ---------- Middleware ----------
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip_raw = request.headers.get("x-forwarded-for") or request.client.host
        ip = ip_raw.split(",")[0].strip()

        geo_risk = 0.1
        geo = {
            "ip": ip,
            "country": "Unknown",
            "tor": False,
            "risk": geo_risk,
        }

        request.state.security = {"threats": [], "geo": geo, "risk": geo_risk}
        return await call_next(request)

app.add_middleware(SecurityMiddleware)

# ---------- Models ----------
class ChatRequest(BaseModel):
    prompt: str

# ---------- Helpers ----------
def log_event(event: dict):
    logging.info(json.dumps(event))

def detect_threats(text: str):
    threats = []
    evidence = {}

    for name, pattern in THREAT_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            threats.append(name)
            evidence[name] = extract_matches(text, name, pattern)

    return threats, evidence

def score_risk(threats, base=0.1):
    if not threats:
        return base
    mx = max(SEVERITY.get(t, 0.6) for t in threats)
    return max(base, mx)

#Helper functions
import uuid
import time

def extract_matches(text: str, name: str, pattern: str, max_matches: int = 3):
    out = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        s = m.group(0)
        # keep a short safe snippet
        if len(s) > 40:
            s = s[:18] + "…" + s[-8:]
        out.append(s)
        if len(out) >= max_matches:
            break
    return out

REDACT_RULES = [
    # password/token style
    (re.compile(r"\b(password|passwd|pwd|token|secret|api[_-]?key)\b\s*(?:[:=]|is)\s*([^\s,;]+)", re.I),
     r"\1=<REDACTED>"),
    # OTP digits
    (re.compile(r"\b(otp|one[-\s]?time\s?password|cvv|pin)\b\s*(?:[:=]|is)?\s*\d{4,8}\b", re.I),
     r"\1=<REDACTED>"),
    # PAN format
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
     "<PAN_REDACTED>"),
    # Aadhaar-ish
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "<AADHAAR_REDACTED>"),
    # Email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL_REDACTED>"),
]

def redact_text(text: str) -> str:
    out = text
    for rgx, repl in REDACT_RULES:
        out = rgx.sub(repl, out)
    return out


# ---------- Routes ----------
@app.post("/chat")
async def chat(payload: ChatRequest, req: Request):
    security = getattr(req.state, "security", {"threats": [], "geo": {}, "risk": 0.1})

    req_id = str(uuid.uuid4())[:8]
    t0 = time.time()

    text = payload.prompt
    redacted = redact_text(text)

    threats, evidence = detect_threats(text)
    risk = score_risk(threats, security.get("risk", 0.1))

    latency_ms = int((time.time() - t0) * 1000)

    event_base = {
        "timestamp": datetime.now().isoformat(),
        "request_id": req_id,
        "ip": security.get("geo", {}).get("ip"),
        "risk": risk,
        "threats": threats,
        "evidence": evidence,
        "latency_ms": latency_ms,
        "prompt_preview": redacted[:80],  # IMPORTANT: log redacted
    }

    if risk > BLOCK_THRESHOLD:
        log_event({**event_base, "action": "BLOCKED"})
        raise HTTPException(403, f"Threats detected: {threats}")

    log_event({**event_base, "action": "ALLOWED"})

    return {
        "response": f"Safe response to: {redacted[:30]}...",
        "risk": risk,
        "geo": security.get("geo", {}),
        "threats": threats,
        "evidence": evidence,
        "redacted_prompt": redacted,
        "request_id": req_id,
        "latency_ms": latency_ms,
    }


@app.get("/logs")
async def get_logs():
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[-10:]
    return [json.loads(line) for line in lines]

@app.get("/health")
async def health(req: Request):
    security = getattr(req.state, "security", {"status": "no-security-context"})
    return {"status": "healthy", "security": security, "block_threshold": BLOCK_THRESHOLD}

@app.get("/policy")
async def policy():
    return {
        "block_threshold": BLOCK_THRESHOLD,
        "detectors": list(THREAT_PATTERNS.keys()),
        "severity": SEVERITY,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

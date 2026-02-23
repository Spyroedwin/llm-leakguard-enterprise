from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, json, logging, asyncio, os
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

load_dotenv()

app = FastAPI(title="LLM LeakGuard Enterprise - Phase 1-4 COMPLETE")

# -----------------------------
# CORS (for dashboard frontend)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Logging setup (JSONL)
# -----------------------------
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "leakguard.jsonl")

logger = logging.getLogger("leakguard")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers if hot-reload / multiple imports happen
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == LOG_PATH for h in logger.handlers):
    _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)


def _now_iso() -> str:
    return datetime.now().isoformat()


def send_alert(subject: str, message: dict):
    """Log security alerts (ALERT type lines in JSONL)"""
    alert_log = {
        "timestamp": _now_iso(),
        "type": "ALERT",
        "subject": subject,
        "details": message
    }
    logger.info(json.dumps(alert_log))
    print(f"🚨 {subject}: {message}")


def log_event(entry: dict):
    """Helper to log dashboard-friendly event rows"""
    try:
        logger.info(json.dumps(entry))
    except Exception:
        # Don't crash core pipeline if logging fails
        pass


# ✅ NEW: dashboard-friendly honeypot event row (no behavior change, only logging)
def log_honeypot_hit(ip: str, path: str, geo: dict, tarpit_seconds: float):
    entry = {
        "timestamp": _now_iso(),
        "action": "HONEYPOT",
        "ip": ip,
        "path": path,
        "country": geo.get("country", "Unknown") if isinstance(geo, dict) else "Unknown",
        "tor": bool(geo.get("tor", False)) if isinstance(geo, dict) else False,
        "risk_breakdown": {
            "phase1": 0.0,
            "geo": round(float(geo.get("risk_score", 0.1)), 2) if isinstance(geo, dict) else 0.1,
            "phase2_llm": 0.0,
            "total": 0.99,  # honeypot hit = “uh oh”
        },
        "details": {
            "tarpit_seconds": tarpit_seconds,
        },
    }
    log_event(entry)


# -----------------------------
# PHASE 1: TOR + GEO middleware
# -----------------------------
VPNAPI_KEY = os.getenv("VPNAPI_KEY", "demo")  # put real key in .env

class GeolocMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.headers.get("x-forwarded-for", str(request.client.host)).split(",")[0].strip()
        geo = {"ip": ip, "country": "Unknown", "tor": False, "risk_score": 0.1}

        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"https://vpnapi.io/api/{ip}?key={VPNAPI_KEY}")
                data = resp.json()

                geo["country"] = data.get("country", "Unknown")
                security = data.get("security", {}) or {}
                geo["tor"] = bool(security.get("tor", False))
                geo["risk_score"] = 0.95 if geo["tor"] else 0.3
        except Exception:
            # keep defaults
            pass

        request.state.geo = geo
        return await call_next(request)

app.add_middleware(GeolocMiddleware)


# -----------------------------
# PHASE 4: Honeypot middleware
# -----------------------------
HONEYPOT_PATH_FRAGMENTS = ["/admin", "/honeypot", "/pentbox"]
HONEYPOT_TARPIT_SECONDS = float(os.getenv("HONEYPOT_TARPIT_SECONDS", "10"))

@app.middleware("http")
async def honeypot_middleware(request: Request, call_next):
    path = request.url.path

    # ✅ Do NOT treat reading honeypot logs as a honeypot hit
    if path.startswith("/api/honeypot-logs"):
        return await call_next(request)

    geo = request.state.geo if hasattr(request.state, "geo") else {"ip": "unknown", "country": "Unknown", "tor": False, "risk_score": 0.1}
    client_ip = geo.get("ip", "unknown")

    # Honeypot trap paths + tarpit
    if any(h in path for h in HONEYPOT_PATH_FRAGMENTS):
        # Existing alert line (kept)
        send_alert("HONEYPOT_HIT", {"ip": client_ip, "path": path})

        # ✅ NEW: dashboard-friendly honeypot event row (kept separate from ALERT)
        log_honeypot_hit(
            ip=client_ip,
            path=path,
            geo=geo,
            tarpit_seconds=HONEYPOT_TARPIT_SECONDS
        )

        # Existing tarpit (kept)
        await asyncio.sleep(int(os.getenv("HONEYPOT_TARPIT_SECONDS", "10")))

    return await call_next(request)


# -----------------------------
# PHASE 1: Traditional threats
# -----------------------------
threat_patterns = {
    "phishing": r"(bank|paypal|amazon|netflix).*?(login|click|verify|update)",
    "malware": r"bash -i.*tcp|curl \| bash|wget -O- \| sh|nc.*-e /bin/sh",
    "sql_injection": r"1' OR '1'='1|union select|'; DROP.*--",
    "tor_c2": r"\.onion|185\.220\.|hidden service|tor.*c2",
    "brute_force": r"admin|root|test|password123|user:pass"
}

class Phase1ThreatScanner:
    def scan(self, text: str) -> List[str]:
        threats = []
        for threat, pattern in threat_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(threat)
        return threats


# -----------------------------
# PHASE 2: OWASP LLM Top risks
# -----------------------------
class Phase2OWASLLMScanner:
    OWASP_PATTERNS = {
        "LLM01_PromptInjection": [
            r"ignore previous.*instructions",
            r"forget.*rules|you are now.*(DAN|evil|hacker)",
            r"act as.*(hacker|malicious|ignore safety)"
        ],
        "LLM02_OutputHandling": [
            r"<script>.*</script>", r"javascript:.*alert", r"onerror=",
            r"data:.*text/html"
        ],
        "LLM03_SupplyChain": [
            r"pip install.*(backdoor|evil|malware)",
            r"npm.*(malicious|backdoor)"
        ],
        "LLM04_DoS": [
            r"repeat.*10000|infinite loop|token limit",
            r"generate.*100000"
        ],
        "LLM05_Poisoning": [
            r"train data.*poison|fine-tune.*malicious",
            r"inject.*training data"
        ]
    }

    def scan(self, text: str) -> Dict[str, Any]:
        detections = {}
        for vuln, patterns in self.OWASP_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detections[vuln] = True
                    break
        risk_score = len(detections) / max(1, len(self.OWASP_PATTERNS))
        return {"detections": detections, "risk_score": risk_score}


phase1_scanner = Phase1ThreatScanner()
phase2_scanner = Phase2OWASLLMScanner()


class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o-mini"


# -----------------------------
# Helper: read JSONL robustly
# -----------------------------
def _read_jsonl(path: str) -> List[dict]:
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []
    return rows


# -----------------------------
# MAIN: /chat (Phase 1 + 2 + Geo)
# -----------------------------
@app.post("/chat")
async def secure_chat(chat_req: ChatRequest, request: Request):
    geo = getattr(request.state, "geo", {"ip": "unknown", "country": "Unknown", "tor": False, "risk_score": 0.1})
    prompt = chat_req.prompt

    # Phase 1
    phase1_threats = phase1_scanner.scan(prompt)
    phase1_risk = 0.95 if phase1_threats else 0.15

    # Phase 2
    phase2_results = phase2_scanner.scan(prompt)
    phase2_risk = phase2_results["risk_score"]

    # Combined risk
    total_risk = (
        phase1_risk * 0.4 +
        float(geo.get("risk_score", 0.1)) * 0.3 +
        phase2_risk * 0.3
    )

    risk_breakdown = {
        "phase1": round(phase1_risk, 2),
        "geo": round(float(geo.get("risk_score", 0.1)), 2),
        "phase2_llm": round(phase2_risk, 2),
        "total": round(total_risk, 2),
    }

    # Block high risk
    if total_risk > 0.75:
        alert_data = {
            "ip": geo.get("ip"),
            "country": geo.get("country"),
            "tor": geo.get("tor"),
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "total_risk": round(total_risk, 2),
            "prompt_snippet": prompt[:100],
        }

        # Existing alert line (kept)
        send_alert("🚨 ENTERPRISE THREAT BLOCKED", alert_data)

        # ✅ NEW: dashboard-friendly BLOCK row (so /logs can compute blocks/risk)
        block_entry = {
            "timestamp": _now_iso(),
            "action": "BLOCK",
            "ip": geo.get("ip"),
            "country": geo.get("country"),
            "tor": geo.get("tor"),
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "risk_breakdown": risk_breakdown,
            "prompt": prompt[:100],
        }
        log_event(block_entry)

        raise HTTPException(
            status_code=403,
            detail=f"BLOCKED: P1={phase1_threats}, P2={list(phase2_results['detections'].keys())}, Risk={total_risk:.2f}"
        )

    # Success logging
    log_entry = {
        "timestamp": _now_iso(),
        # ✅ Standardize action to match dashboard enums
        "action": "ALLOW",
        "ip": geo.get("ip"),
        "country": geo.get("country"),
        "tor": geo.get("tor"),
        "phase1_threats": phase1_threats,
        "phase2_owasp": list(phase2_results["detections"].keys()),
        "risk_breakdown": risk_breakdown,
        "prompt": prompt[:100],
    }
    log_event(log_entry)

    return {
        "response": f"✅ Safe response processed (Total Risk: {total_risk:.2f})",
        "security_report": {
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "geo": geo,
            "risk_breakdown": risk_breakdown,
        },
    }


# -----------------------------
# Manual scan endpoint
# -----------------------------
@app.post("/scan/llm-vuln")
async def llm_vuln_scan(prompt: str):
    p1_threats = phase1_scanner.scan(prompt)
    p2_results = phase2_scanner.scan(prompt)

    combined_risk = max(
        0.9 if p1_threats else 0.1,
        p2_results["risk_score"]
    )

    return {
        "phase1_threats": p1_threats,
        "phase2_owasp": p2_results["detections"],
        "risk_score": combined_risk,
        "recommendation": "🚫 BLOCK" if combined_risk > 0.7 else "✅ ALLOW",
        "confidence": round(combined_risk * 100, 1),
    }


# -----------------------------
# Health
# -----------------------------
@app.get("/health")
async def health(request: Request):
    return {
        "status": "healthy",
        "version": "Phase1-4 COMPLETE",
        "geo": getattr(request.state, "geo", {}),
        "log_path": LOG_PATH,
    }


# -----------------------------
# Logs (dashboard)
# -----------------------------
@app.get("/logs")
async def get_logs(limit: int = 50):
    logs = _read_jsonl(LOG_PATH)
    return logs[-limit:]


# -----------------------------
# Threat leaderboard (dashboard charts)
# -----------------------------
@app.get("/threat-leaderboard")
async def threat_leaderboard(limit: int = 10):
    logs = _read_jsonl(LOG_PATH)
    threat_counts: Dict[str, int] = {}

    for log in logs:
        p1 = log.get("phase1_threats", []) or []
        p2 = log.get("phase2_owasp", []) or []
        for threat in p1 + p2:
            threat_counts[threat] = threat_counts.get(threat, 0) + 1

    return sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)[:limit]


# -----------------------------
# PHASE 4: PentBox honeypot log sync
# -----------------------------
@app.get("/api/honeypot-logs")
async def pentbox_logs(tail: int = 50):
    # keep same relative structure as homie's code
    pentbox_log = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "honeypot-logs", "pentbox.log"))
    logs = []

    if os.path.exists(pentbox_log):
        try:
            with open(pentbox_log, "r", encoding="utf-8") as f:
                lines = f.readlines()

            logs = [{"timestamp": _now_iso(), "line": line.strip()}
                    for line in lines[-tail:] if line.strip()]

            # Auto-add critical alerts into main log
            for entry in logs:
                up = entry["line"].upper()
                if any(k in up for k in ["INTRUSION", "DETECTED", "ATTACK"]):
                    alert_data = {
                        "ip": "pentbox_honeypot",
                        "threat_type": "PENTBOX_ALERT",
                        "severity": "CRITICAL",
                        "details": entry["line"][:200],
                    }
                    send_alert("🚨 PENTBOX HONEYPOT HIT", alert_data)

        except Exception as e:
            logs = [{"timestamp": _now_iso(), "line": f"PentBox log read error: {str(e)}"}]

    total_alerts = sum(1 for l in logs if "INTRUSION" in l["line"].upper())
    return {"honeypot_logs": logs, "total_alerts": total_alerts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
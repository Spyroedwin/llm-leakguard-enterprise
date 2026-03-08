from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, json, logging, asyncio, os
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple

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
if not any(
    isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == LOG_PATH
    for h in logger.handlers
):
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
        "details": message,
    }
    logger.info(json.dumps(alert_log))
    print(f"🚨 {subject}: {message}")


def log_event(entry: dict):
    """Helper to log dashboard-friendly event rows"""
    try:
        logger.info(json.dumps(entry))
    except Exception:
        pass


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
# GEO helper (NO KEY REQUIRED)
# -----------------------------
def _is_private_or_local_ip(ip: str) -> bool:
    # super light check (good enough for demo/dev)
    return (
        ip.startswith("127.")
        or ip == "localhost"
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("172.16.")
        or ip.startswith("172.17.")
        or ip.startswith("172.18.")
        or ip.startswith("172.19.")
        or ip.startswith("172.2")
        or ip.startswith("172.3")
    )


async def _geo_lookup(ip: str) -> dict:
    """
    Best-effort geo lookup without keys.
    - Local/private IPs can't be geo-located -> stable fallback.
    - Public IPs: try ipapi.co (no key).
    """
    # Default fallback (India center-ish so your map isn't empty)
    geo = {
        "ip": ip,
        "country": "Unknown",
        "city": "Unknown",
        "lat": 20.5937,
        "lng": 78.9629,
        "tor": False,
        "risk_score": 0.3,  # normal-ish baseline
        "source": "fallback",
    }

    if _is_private_or_local_ip(ip):
        geo["country"] = "Local"
        geo["city"] = "Localhost"
        geo["risk_score"] = 0.2
        geo["source"] = "local"
        return geo

    try:
        async with httpx.AsyncClient(timeout=2) as client:
            # ipapi.co is free for basic usage (no key)
            resp = await client.get(f"https://ipapi.co/{ip}/json/")
            data = resp.json() if resp.status_code == 200 else {}

        # ipapi sometimes returns {"error": true, ...}
        if data and not data.get("error"):
            geo["country"] = data.get("country_name") or data.get("country") or "Unknown"
            geo["city"] = data.get("city") or "Unknown"
            lat = data.get("latitude")
            lng = data.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                geo["lat"] = float(lat)
                geo["lng"] = float(lng)
            geo["source"] = "ipapi"
            # no tor signal here; leave tor False
            geo["risk_score"] = 0.3
    except Exception:
        pass

    return geo


# -----------------------------
# PHASE 1: TOR + GEO middleware
# -----------------------------
# If you ever get a real VPN/TOR API key later, you can re-add it.
# For now: no keys required, stable behavior.
class GeolocMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.headers.get("x-forwarded-for", str(request.client.host)).split(",")[0].strip()
        geo = await _geo_lookup(ip)
        request.state.geo = geo
        return await call_next(request)


app.add_middleware(GeolocMiddleware)


# -----------------------------
# PHASE 4: Honeypot middleware
# -----------------------------
HONEYPOT_PATH_FRAGMENTS = ["/admin", "/honeypot", "/pentbox"]
HONEYPOT_TARPIT_SECONDS = float(os.getenv("HONEYPOT_TARPIT_SECONDS", "10"))


def log_honeypot_hit(ip: str, path: str, geo: dict, tarpit_seconds: float):
    entry = {
        "timestamp": _now_iso(),
        "action": "HONEYPOT",
        "ip": ip,
        "path": path,
        "country": geo.get("country", "Unknown") if isinstance(geo, dict) else "Unknown",
        "city": geo.get("city", "Unknown") if isinstance(geo, dict) else "Unknown",
        "lat": geo.get("lat", 20.5937) if isinstance(geo, dict) else 20.5937,
        "lng": geo.get("lng", 78.9629) if isinstance(geo, dict) else 78.9629,
        "tor": bool(geo.get("tor", False)) if isinstance(geo, dict) else False,
        "risk_breakdown": {
            "phase1": 0.0,
            "geo": round(float(geo.get("risk_score", 0.1)), 2) if isinstance(geo, dict) else 0.1,
            "phase2_llm": 0.0,
            "total": 0.99,
        },
        "details": {"tarpit_seconds": tarpit_seconds},
    }
    log_event(entry)


@app.middleware("http")
async def honeypot_middleware(request: Request, call_next):
    path = request.url.path

    # Do NOT treat reading honeypot logs / geo / health / logs as honeypot hits
    if path.startswith("/api/honeypot-logs") or path.startswith("/geo") or path.startswith("/logs") or path.startswith("/health"):
        return await call_next(request)

    geo = getattr(request.state, "geo", {"ip": "unknown", "country": "Unknown", "tor": False, "risk_score": 0.1})
    client_ip = geo.get("ip", "unknown")

    if any(h in path for h in HONEYPOT_PATH_FRAGMENTS):
        send_alert("HONEYPOT_HIT", {"ip": client_ip, "path": path})
        log_honeypot_hit(client_ip, path, geo, HONEYPOT_TARPIT_SECONDS)
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
    "brute_force": r"admin|root|test|password123|user:pass",
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
            r"act as.*(hacker|malicious|ignore safety)",
        ],
        "LLM02_OutputHandling": [
            r"<script>.*</script>",
            r"javascript:.*alert",
            r"onerror=",
            r"data:.*text/html",
        ],
        "LLM03_SupplyChain": [
            r"pip install.*(backdoor|evil|malware)",
            r"npm.*(malicious|backdoor)",
        ],
        "LLM04_DoS": [
            r"repeat.*10000|infinite loop|token limit",
            r"generate.*100000",
        ],
        "LLM05_Poisoning": [
            r"train data.*poison|fine-tune.*malicious",
            r"inject.*training data",
        ],
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
# MAIN: /chat (Phase 1 + 2 + Geo)
# -----------------------------
@app.post("/chat")
async def secure_chat(chat_req: ChatRequest, request: Request):
    geo = getattr(request.state, "geo", {"ip": "unknown", "country": "Unknown", "tor": False, "risk_score": 0.1})
    prompt = chat_req.prompt

    phase1_threats = phase1_scanner.scan(prompt)
    phase1_risk = 0.95 if phase1_threats else 0.15

    phase2_results = phase2_scanner.scan(prompt)
    phase2_risk = phase2_results["risk_score"]

    total_risk = (phase1_risk * 0.4 + float(geo.get("risk_score", 0.1)) * 0.3 + phase2_risk * 0.3)

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
            "city": geo.get("city"),
            "tor": geo.get("tor"),
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "total_risk": round(total_risk, 2),
            "prompt_snippet": prompt[:100],
        }

        send_alert("🚨 ENTERPRISE THREAT BLOCKED", alert_data)

        block_entry = {
            "timestamp": _now_iso(),
            "action": "BLOCK",
            "ip": geo.get("ip"),
            "country": geo.get("country"),
            "city": geo.get("city"),
            "lat": geo.get("lat"),
            "lng": geo.get("lng"),
            "tor": geo.get("tor"),
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "risk_breakdown": risk_breakdown,
            "prompt": prompt[:100],
        }
        log_event(block_entry)

        raise HTTPException(
            status_code=403,
            detail=f"BLOCKED: P1={phase1_threats}, P2={list(phase2_results['detections'].keys())}, Risk={total_risk:.2f}",
        )

    # Success logging
    log_entry = {
        "timestamp": _now_iso(),
        "action": "ALLOW",
        "ip": geo.get("ip"),
        "country": geo.get("country"),
        "city": geo.get("city"),
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
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

    combined_risk = max(0.9 if p1_threats else 0.1, p2_results["risk_score"])

    return {
        "phase1_threats": p1_threats,
        "phase2_owasp": p2_results["detections"],
        "risk_score": combined_risk,
        "recommendation": "🚫 BLOCK" if combined_risk > 0.7 else "✅ ALLOW",
        "confidence": round(combined_risk * 100, 1),
    }


# -----------------------------
# Health (dashboard)
# -----------------------------
def _compute_dashboard_summary(logs: List[dict]) -> Tuple[float, int]:
    # rolling risk + blocks from last 50 rows
    recent = logs[-50:] if len(logs) > 50 else logs
    blocks = sum(1 for l in recent if l.get("action") == "BLOCK")
    risks = []
    for l in recent:
        rb = l.get("risk_breakdown") or {}
        if isinstance(rb, dict) and isinstance(rb.get("total"), (int, float)):
            risks.append(float(rb["total"]))
    avg_risk = sum(risks) / len(risks) if risks else 0.0
    return round(avg_risk, 2), int(blocks)


@app.get("/health")
async def health(request: Request):
    logs = _read_jsonl(LOG_PATH)
    avg_risk, blocks = _compute_dashboard_summary(logs)

    return {
        "status": "healthy",
        "engine_version": "Phase1-4 COMPLETE",
        "policy_mode": "LIVE",
        "risk_score": avg_risk,
        "blocks": blocks,
        "geo": getattr(request.state, "geo", {}),
        "log_path": LOG_PATH,
    }


# Optional: a compact summary endpoint (some UIs like this)
@app.get("/summary")
async def summary():
    logs = _read_jsonl(LOG_PATH)
    avg_risk, blocks = _compute_dashboard_summary(logs)
    return {"status": "ONLINE", "risk": avg_risk, "blocks": blocks}


# -----------------------------
# Logs
# -----------------------------
@app.get("/logs")
async def get_logs(limit: int = 50):
    logs = _read_jsonl(LOG_PATH)
    return logs[-limit:]


# -----------------------------
# Geo markers for the map
# -----------------------------
@app.get("/geo")
async def geo_markers(limit: int = 200):
    logs = _read_jsonl(LOG_PATH)

    markers = []
    for log in reversed(logs):  # newest first
        ip = log.get("ip")
        if not ip:
            continue

        lat = log.get("lat")
        lng = log.get("lng")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            # fallback if older logs didn't store lat/lng
            lat, lng = 20.5937, 78.9629

        p1 = log.get("phase1_threats") or []
        p2 = log.get("phase2_owasp") or []
        threat = (p1 + p2)[0] if (p1 + p2) else "unknown"

        rb = log.get("risk_breakdown") or {}
        risk = rb.get("total", 0)

        markers.append(
            {
                "lat": float(lat),
                "lng": float(lng),
                "label": ip,
                "threat": threat,
                "risk": risk,
                "tor": bool(log.get("tor", False)),
            }
        )

        if len(markers) >= limit:
            break

    return markers


# -----------------------------
# Threat leaderboard
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

    # return array of pairs (threat, count)
    return sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)[:limit]


# -----------------------------
# PHASE 4: PentBox honeypot log sync
# -----------------------------
@app.get("/api/honeypot-logs")
async def pentbox_logs(tail: int = 50):
    pentbox_log = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "honeypot-logs", "pentbox.log")
    )
    logs = []

    if os.path.exists(pentbox_log):
        try:
            with open(pentbox_log, "r", encoding="utf-8") as f:
                lines = f.readlines()

            logs = [{"timestamp": _now_iso(), "line": line.strip()} for line in lines[-tail:] if line.strip()]

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
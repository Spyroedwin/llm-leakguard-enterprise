from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import re, json, logging
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="LLM LeakGuard Enterprise - Phase 1+2")

# ===== PHASE 1: TOR + GEO MIDDLEWARE =====
class GeolocMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.headers.get("x-forwarded-for", str(request.client.host)).split(",")[0].strip()
        geo = {"ip": ip, "country": "Unknown", "tor": False, "risk_score": 0.1}
        
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"https://vpnapi.io/api/{ip}?key=demo")
                data = resp.json()
                geo["country"] = data.get("country", "Unknown")
                security = data.get("security", {})
                geo["tor"] = security.get("tor", False)
                geo["risk_score"] = 0.95 if geo["tor"] else 0.3
        except:
            pass
            
        request.state.geo = geo
        response = await call_next(request)
        return response

app.add_middleware(GeolocMiddleware)

# ===== PHASE 1: TRADITIONAL THREAT SCANNER =====
threat_patterns = {
    "phishing": r"(bank|paypal|amazon|netflix).*?(login|click|verify|update)",
    "malware": r"bash -i.*tcp|curl \| bash|wget -O- \| sh|nc.*-e /bin/sh",
    "sql_injection": r"1' OR '1'='1|union select|'; DROP.*--",
    "tor_c2": r"\.onion|185\.220\.|hidden service|tor.*c2",
    "brute_force": r"admin|root|test|password123|user:pass"
}

class Phase1ThreatScanner:
    def scan(self, text: str):
        threats = []
        for threat, pattern in threat_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(threat)
        return threats

# ===== PHASE 2: OWASP LLM TOP 10 SCANNER =====
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
    
    def scan(self, text: str):
        detections = {}
        for vuln, patterns in self.OWASP_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detections[vuln] = True
                    break
        risk_score = len(detections) / len(self.OWASP_PATTERNS)
        return {"detections": detections, "risk_score": risk_score}

# Initialize scanners
phase1_scanner = Phase1ThreatScanner()
phase2_scanner = Phase2OWASLLMScanner()

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o-mini"

# Logging setup
logging.basicConfig(filename="../logs.jsonl", level=logging.INFO, format="%(message)s")

def send_alert(subject: str, message: dict):
    """Log security alerts"""
    alert_log = {
        "timestamp": datetime.now().isoformat(),
        "type": "ALERT",
        "subject": subject,
        "details": message
    }
    logging.info(json.dumps(alert_log))
    print(f"🚨 {subject}: {message}")

# ===== MAIN /chat ENDPOINT - PHASE 1 + 2 =====
@app.post("/chat")
async def secure_chat(chat_req: ChatRequest, request: Request):
    geo = request.state.geo
    prompt = chat_req.prompt
    
    # PHASE 1: Traditional cyber threats
    phase1_threats = phase1_scanner.scan(prompt)
    phase1_risk = 0.95 if phase1_threats else 0.15
    
    # PHASE 2: LLM-specific vulnerabilities (OWASP Top 10)
    phase2_results = phase2_scanner.scan(prompt)
    phase2_risk = phase2_results["risk_score"]
    
    # COMBINED ENTERPRISE RISK SCORE
    total_risk = (
        phase1_risk * 0.4 + 
        geo["risk_score"] * 0.3 + 
        phase2_risk * 0.3
    )
    
    # BLOCK HIGH RISK
    if total_risk > 0.75:
        alert_data = {
            "ip": geo["ip"],
            "country": geo["country"],
            "tor": geo["tor"],
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "total_risk": round(total_risk, 2),
            "prompt_snippet": prompt[:100]
        }
        send_alert("🚨 ENTERPRISE THREAT BLOCKED", alert_data)
        raise HTTPException(
            status_code=403,
            detail=f"BLOCKED: P1={phase1_threats}, P2={list(phase2_results['detections'].keys())}, Risk={total_risk:.2f}"
        )
    
    # SUCCESS LOGGING
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "ALLOWED",
        "ip": geo["ip"],
        "country": geo["country"],
        "tor": geo["tor"],
        "phase1_threats": phase1_threats,
        "phase2_owasp": list(phase2_results["detections"].keys()),
        "risk_breakdown": {
            "phase1": round(phase1_risk, 2),
            "geo": round(geo["risk_score"], 2),
            "phase2_llm": round(phase2_risk, 2),
            "total": round(total_risk, 2)
        },
        "prompt": prompt[:100]
    }
    logging.info(json.dumps(log_entry))
    
    return {
        "response": f"✅ Safe response processed (Total Risk: {total_risk:.2f})",
        "security_report": {
            "phase1_threats": phase1_threats,
            "phase2_owasp": list(phase2_results["detections"].keys()),
            "geo": geo,
            "risk_breakdown": {
                "phase1": round(phase1_risk, 2),
                "geo": round(geo["risk_score"], 2),
                "phase2_llm": round(phase2_risk, 2),
                "total": round(total_risk, 2)
            }
        }
    }

# ===== PHASE 2: LLM VULN SCANNER ENDPOINT =====
@app.post("/scan/llm-vuln")
async def llm_vuln_scan(prompt: str):
    """Manual Phase 2 vulnerability scan"""
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
        "confidence": round(combined_risk * 100, 1)
    }

# ===== HEALTH + LOGS ENDPOINTS =====
@app.get("/health")
async def health(request: Request):
    return {
        "status": "healthy", 
        "version": "Phase1+2",
        "geo": request.state.geo
    }

@app.get("/logs")
async def get_logs():
    try:
        with open("../logs.jsonl", "r") as f:
            logs = [json.loads(line) for line in f.readlines()[-20:]]
        return logs
    except FileNotFoundError:
        return []

@app.get("/threat-leaderboard")
async def threat_leaderboard():
    """Phase 2: Top threats dashboard data"""
    try:
        with open("../logs.jsonl", "r") as f:
            logs = [json.loads(line) for line in f.readlines()]
        
        threat_counts = {}
        for log in logs:
            p1 = log.get("phase1_threats", [])
            p2 = log.get("phase2_owasp", [])
            for threat in p1 + p2:
                threat_counts[threat] = threat_counts.get(threat, 0) + 1
        
        return sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    except:
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

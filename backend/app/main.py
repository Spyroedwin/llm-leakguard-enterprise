from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import re, json, logging
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="LLM LeakGuard Enterprise")

# TOR + Threat Detection Middleware
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get real IP (Tor-proof)
        ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
        
        # Threat patterns
        threat_patterns = {
            'phishing': r'(bank|paypal).*?(login|click)',
            'malware': r'bash -i|curl \| bash',
            'sql': r"1' OR '1|union select",
            'tor': r'\.onion|185\.220',
            'brute': r'admin|password123'
        }
        
        threats = []
        geo_risk = 0.1
        for threat, pattern in threat_patterns.items():
            if re.search(pattern, request.url.query + str(request.headers), re.IGNORECASE):
                threats.append(threat)
        
        # Mock geo (real vpnapi.io in production)
        geo = {"ip": ip, "country": "Unknown", "tor": ".onion" in str(request.headers), "risk": geo_risk}
        
        request.state.security = {"threats": threats, "geo": geo, "risk": 0.8 if threats else geo_risk}
        response = await call_next(request)
        return response

app.add_middleware(SecurityMiddleware)

class ChatRequest(BaseModel):
    prompt: str

# Logging setup
logging.basicConfig(filename='logs.jsonl', level=logging.INFO, format='%(message)s')

@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    security = req.state.security
    
    # Block high-risk
    if security["risk"] > 0.75:
        log = {
            "timestamp": datetime.now().isoformat(),
            "action": "BLOCKED",
            "threats": security["threats"],
            "ip": security["geo"]["ip"],
            "prompt": request.prompt[:50]
        }
        logging.info(json.dumps(log))
        raise HTTPException(403, f"Threats detected: {security['threats']}")
    
    # Safe response + log
    log = {
        "timestamp": datetime.now().isoformat(),
        "action": "ALLOWED",
        "ip": security["geo"]["ip"],
        "prompt": request.prompt[:50],
        "risk": security["risk"]
    }
    logging.info(json.dumps(log))
    
    return {
        "response": f"Safe response to: {request.prompt[:30]}...",
        "risk": security["risk"],
        "geo": security["geo"]
    }

@app.get("/logs")
async def get_logs():
    try:
        with open('logs.jsonl', 'r') as f:
            return [json.loads(line) for line in f.readlines()[-10:]]
    except FileNotFoundError:
        return []

@app.get("/health")
async def health(req: Request):
    return {"status": "healthy", "security": req.state.security}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

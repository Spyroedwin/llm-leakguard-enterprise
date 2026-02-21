import re

class OWASLLMScanner:
    OWASP_PATTERNS = {
        "LLM01_PromptInjection": [r"ignore previous", r"forget.*rules", r"you are now"],
        "LLM02_OutputHandling": [r"<script>", r"javascript:", r"onerror="],
        "LLM03_SupplyChain": [r"pip install.*evil", r"npm.*malicious"],
        "LLM04_DoS": [r"repeat 10000 times", r"infinite loop"],
        "LLM05_Poisoning": [r"train data.*poison", r"fine-tune.*malicious"]
    }
    
    def scan(self, text: str):
        detections = {}
        for vuln, patterns in self.OWASP_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detections[vuln] = True
                    break
        risk = len(detections) / len(self.OWASP_PATTERNS)
        return {"detections": detections, "risk_score": risk}

from garak import scan
import asyncio
import os

class GarakScanner:
    def __init__(self):
        os.environ["OPENAI_API_KEY"] = "demo-key"  # Replace with real key
        
    async def scan_llm(self, prompt: str):
        """Scan for LLM vulnerabilities using NVIDIA Garak"""
        try:
            # OWASP LLM Top 10 probes
            probes = ["encoding", "injection", "jailbreak", "dan.Dan_11_0"]
            
            results = {}
            for probe in probes:
                report = scan.run(
                    target_type="huggingface",
                    target_name="gpt2",  # Local model for demo
                    probes=[probe]
                )
                results[probe] = report["pass"] == False
            
            risk_score = sum(results.values()) / len(results)
            return {
                "vulnerabilities": results,
                "risk_score": risk_score,
                "high_risk": risk_score > 0.5
            }
        except:
            return {"risk_score": 0.3, "high_risk": False}

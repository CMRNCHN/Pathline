import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class ReportGenerator:
    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path

    def generate(self, 
                 metadata: Dict[str, Any],
                 qa_score: Dict[str, Any],
                 failure_info: Dict[str, Any],
                 benchmarks: Dict[str, Any],
                 integrity_hash: str) -> Dict[str, str]:
        
        report_data = {
            "metadata": metadata,
            "qa_score": qa_score,
            "failure_classification": failure_info,
            "benchmarks": benchmarks,
            "integrity": {
                "manifest_sha256": integrity_hash,
                "verified_at": datetime.now().isoformat()
            },
            "recommendations": self._generate_recommendations(qa_score, failure_info, benchmarks)
        }

        # Write JSON report
        json_path = self.bundle_path / "report.json"
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=2)

        # Write Markdown report
        md_path = self.bundle_path / "report.md"
        with open(md_path, "w") as f:
            f.write(self._generate_markdown(report_data))

        return {
            "json": str(json_path),
            "md": str(md_path)
        }

    def _generate_recommendations(self, qa_score: Dict[str, Any], failure_info: Dict[str, Any], benchmarks: Dict[str, Any]) -> List[str]:
        recs = []
        if qa_score["session_score"] < 70:
            recs.append("Review session stability and routing logic due to low overall score.")
        
        if failure_info["primary_category"] == "LOOP_DETECTED":
            recs.append("Investigate IVR menu for potential infinite loops or missing exit conditions.")
        
        if benchmarks["average_latency_ms"] > 2000:
            recs.append("Optimize backend response time or check network conditions to reduce latency.")
            
        if not qa_score["factors"]["evidence_completeness"]["has_recording"]:
            recs.append("Enable recording for future runs to ensure full evidence auditability.")

        if not recs:
            recs.append("No immediate actions required. Session performed within expected parameters.")
            
        return recs

    def _generate_markdown(self, data: Dict[str, Any]) -> str:
        m = "# Telecom Validation Report\n\n"
        m += f"**Bundle ID:** `{data['metadata']['bundle_id']}`  \n"
        m += f"**Session ID:** `{data['metadata']['session_id']}`  \n"
        m += f"**Created At:** {data['metadata']['created_at']}\n\n"
        
        m += "## QA Summary\n"
        m += f"**Overall Score:** {data['qa_score']['session_score']}/100\n"
        m += f"**Classification:** {data['failure_classification']['primary_category']}\n"
        m += f"**Explanation:** {data['failure_classification']['explanation']}\n\n"
        
        m += "### Scoring Factors\n"
        for factor, details in data['qa_score']['factors'].items():
            m += f"- **{factor.replace('_', ' ').title()}:** {details['score']}/100\n"
        
        m += "\n## Benchmark Metrics\n"
        for k, v in data['benchmarks'].items():
            m += f"- {k.replace('_', ' ').title()}: {v}\n"
            
        m += "\n## Recommendations\n"
        for rec in data['recommendations']:
            m += f"- {rec}\n"
            
        m += "\n## Integrity\n"
        m += f"**SHA-256:** `{data['integrity']['manifest_sha256']}`\n"
        
        return m
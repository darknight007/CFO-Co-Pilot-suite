from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
from enum import Enum

class MetricType(Enum):
    TAX_FILING = "tax_filing"
    COMPLIANCE = "compliance"
    RISK = "risk"
    RECONCILIATION = "reconciliation"

@dataclass
class DashboardMetric:
    type: MetricType
    timestamp: datetime
    data: Dict
    metadata: Optional[Dict] = None

class DashboardAPI:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def push_metric(self, metric: DashboardMetric) -> bool:
        """Push a metric to the dashboard"""
        try:
            async with self.session.post(
                f"{self.base_url}/v1/metrics",
                json={
                    "type": metric.type.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "data": metric.data,
                    "metadata": metric.metadata or {}
                }
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def push_metrics(self, metrics: List[DashboardMetric]) -> Dict:
        """Push multiple metrics to the dashboard"""
        try:
            async with self.session.post(
                f"{self.base_url}/v1/metrics/batch",
                json=[{
                    "type": m.type.value,
                    "timestamp": m.timestamp.isoformat(),
                    "data": m.data,
                    "metadata": m.metadata or {}
                } for m in metrics]
            ) as response:
                return await response.json()
        except Exception as e:
            return {"error": str(e), "failed_count": len(metrics)}

class DashboardReporter:
    def __init__(self, dashboard_api: DashboardAPI):
        self.api = dashboard_api

    async def report_tax_filing(self, filing_result: Dict) -> bool:
        """Report tax filing status to dashboard"""
        metric = DashboardMetric(
            type=MetricType.TAX_FILING,
            timestamp=datetime.now(),
            data={
                "status": filing_result["status"],
                "jurisdiction": filing_result["jurisdiction"],
                "form_type": filing_result["form_type"],
                "submission_id": filing_result["submission_id"],
                "amount": filing_result.get("amount", 0),
                "currency": filing_result.get("currency", "USD")
            },
            metadata={
                "acknowledgment": filing_result.get("acknowledgment_number"),
                "due_date": filing_result.get("due_date")
            }
        )
        
        async with self.api:
            return await self.api.push_metric(metric)

    async def report_compliance_status(self, compliance_data: Dict) -> bool:
        """Report compliance status to dashboard"""
        metric = DashboardMetric(
            type=MetricType.COMPLIANCE,
            timestamp=datetime.now(),
            data={
                "total_vendors": compliance_data["total_vendors"],
                "compliant_vendors": compliance_data["compliant_vendors"],
                "pending_actions": compliance_data["pending_actions"],
                "overdue_actions": compliance_data["overdue_actions"]
            },
            metadata={
                "risk_distribution": compliance_data.get("risk_distribution"),
                "action_categories": compliance_data.get("action_categories")
            }
        )
        
        async with self.api:
            return await self.api.push_metric(metric)

    async def report_risk_metrics(self, risk_data: Dict) -> bool:
        """Report risk metrics to dashboard"""
        metric = DashboardMetric(
            type=MetricType.RISK,
            timestamp=datetime.now(),
            data={
                "high_risk_count": risk_data["high_risk_count"],
                "medium_risk_count": risk_data["medium_risk_count"],
                "low_risk_count": risk_data["low_risk_count"],
                "total_risk_amount": risk_data["total_risk_amount"]
            },
            metadata={
                "risk_categories": risk_data.get("risk_categories"),
                "top_risk_factors": risk_data.get("top_risk_factors")
            }
        )
        
        async with self.api:
            return await self.api.push_metric(metric)

    async def report_reconciliation(self, reconciliation_data: Dict) -> bool:
        """Report reconciliation status to dashboard"""
        metric = DashboardMetric(
            type=MetricType.RECONCILIATION,
            timestamp=datetime.now(),
            data={
                "total_transactions": reconciliation_data["total_transactions"],
                "reconciled_count": reconciliation_data["reconciled_count"],
                "unreconciled_count": reconciliation_data["unreconciled_count"],
                "total_discrepancy": reconciliation_data["total_discrepancy"]
            },
            metadata={
                "discrepancy_types": reconciliation_data.get("discrepancy_types"),
                "affected_accounts": reconciliation_data.get("affected_accounts")
            }
        )
        
        async with self.api:
            return await self.api.push_metric(metric)

class DashboardWebhook:
    def __init__(self, webhook_url: str, secret_key: str):
        self.webhook_url = webhook_url
        self.secret_key = secret_key

    async def send_event(self, event_type: str, event_data: Dict) -> bool:
        """Send event to webhook endpoint"""
        payload = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": event_data,
            "signature": self._generate_signature(event_data)
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    return response.status == 200
            except Exception:
                return False

    def _generate_signature(self, data: Dict) -> str:
        """Generate signature for webhook payload"""
        message = json.dumps(data, sort_keys=True).encode()
        return hmac.new(
            self.secret_key.encode(),
            message,
            hashlib.sha256
        ).hexdigest()

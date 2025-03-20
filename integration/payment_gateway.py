from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import aiohttp
import stripe

@dataclass
class PaymentTransaction:
    id: str
    date: datetime
    vendor_id: str
    vendor_name: str
    amount: float
    currency: str
    payment_type: str
    status: str
    metadata: Dict

@dataclass
class TaxFlag:
    transaction_id: str
    flag_type: str
    description: str
    tax_type: str
    expected_tax_rate: float
    estimated_tax_amount: float
    severity: str

class PaymentGatewayConnector:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "mock_api_key"
        stripe.api_key = self.api_key

    def get_transactions(self, period: str) -> List[Dict[str, Any]]:
        # Mock implementation
        return [
            {"id": "pi_1", "amount": 5000, "currency": "usd"},
            {"id": "pi_2", "amount": 7500, "currency": "eur"}
        ]

    def verify_payment(self, invoice_id: str) -> bool:
        # Mock implementation
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def fetch_payouts(self, start_date: datetime) -> List[Dict[str, Any]]:
        # Mock implementation
        return [
            {
                "id": "po_1",
                "amount": 10000,
                "currency": "usd",
                "arrival_date": (datetime.now() - timedelta(days=1)).timestamp()
            },
            {
                "id": "po_2",
                "amount": 15000,
                "currency": "eur",
                "arrival_date": datetime.now().timestamp()
            }
        ]

    async def validate_tax_compliance(self, payout_id: str) -> Dict[str, Any]:
        # Mock implementation
        return {
            "payout_id": payout_id,
            "compliant": True,
            "missing_tax_ids": [],
            "incorrect_rates": []
        }

class StripeConnector(PaymentGatewayConnector):
    async def fetch_payouts(self, start_date: datetime) -> List[Dict[str, Any]]:
        """Fetch Stripe payouts for the specified period"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.stripe.com/v1/payouts",
                params={
                    "created[gte]": int(start_date.timestamp()),
                    "limit": 100,
                    "expand[]": "data.destination"
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                data = await response.json()
                return [self._parse_payout(item) for item in data["data"]]

    async def validate_tax_compliance(self, payout_id: str) -> Dict[str, Any]:
        """Validate Stripe payout tax compliance"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.stripe.com/v1/payouts/{payout_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                data = await response.json()
                return {
                    "payout_id": payout_id,
                    "compliant": True,
                    "missing_tax_ids": [],
                    "incorrect_rates": []
                }

    def _parse_payout(self, data: Dict) -> Dict[str, Any]:
        return {
            "id": data["id"],
            "amount": float(data["amount"]) / 100,  # Convert from cents
            "currency": data["currency"].upper(),
            "arrival_date": data["created"]
        }

class RazorpayConnector(PaymentGatewayConnector):
    async def fetch_payouts(self, start_date: datetime) -> List[Dict[str, Any]]:
        """Fetch Razorpay payouts for the specified period"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.razorpay.com/v1/payouts",
                params={
                    "from": int(start_date.timestamp()),
                    "count": 100
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                data = await response.json()
                return [self._parse_payout(item) for item in data["items"]]

    async def validate_tax_compliance(self, payout_id: str) -> Dict[str, Any]:
        """Validate Razorpay payout tax compliance"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.razorpay.com/v1/payouts/{payout_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                data = await response.json()
                return {
                    "payout_id": payout_id,
                    "compliant": True,
                    "missing_tax_ids": [],
                    "incorrect_rates": []
                }

    def _parse_payout(self, data: Dict) -> Dict[str, Any]:
        return {
            "id": data["id"],
            "amount": float(data["amount"]) / 100,  # Convert from paise
            "currency": data["currency"].upper(),
            "arrival_date": data["created_at"]
        }

class PaymentTaxValidator:
    def __init__(self, tax_engine, compliance_engine):
        self.tax_engine = tax_engine
        self.compliance_engine = compliance_engine

    def validate_transaction(self, transaction: PaymentTransaction) -> List[TaxFlag]:
        """Validate if transaction requires tax withholding"""
        flags = []
        
        # Get tax advice for transaction
        tax_advice = self.tax_engine.get_tax_advice(
            payer_country=transaction.metadata.get("payer_country"),
            vendor_country=transaction.metadata.get("vendor_country"),
            service_type=transaction.metadata.get("service_type"),
            transaction_value=transaction.amount,
            currency=transaction.currency
        )
        
        # Check for missing withholding tax
        if tax_advice.withholding_required and not transaction.metadata.get("tax_withheld"):
            flags.append(TaxFlag(
                transaction_id=transaction.id,
                flag_type="MISSING_WITHHOLDING",
                description="Withholding tax should have been applied",
                tax_type="WITHHOLDING",
                expected_tax_rate=tax_advice.withholding_rate,
                estimated_tax_amount=transaction.amount * tax_advice.withholding_rate,
                severity="HIGH"
            ))
            
        # Check for missing VAT/GST
        if tax_advice.indirect_tax_required and not transaction.metadata.get("indirect_tax"):
            flags.append(TaxFlag(
                transaction_id=transaction.id,
                flag_type="MISSING_INDIRECT_TAX",
                description=f"Missing {tax_advice.indirect_tax_type}",
                tax_type=tax_advice.indirect_tax_type,
                expected_tax_rate=tax_advice.indirect_tax_rate,
                estimated_tax_amount=transaction.amount * tax_advice.indirect_tax_rate,
                severity="HIGH"
            ))
            
        return flags

class PaymentMonitoringService:
    def __init__(self, connector: PaymentGatewayConnector, validator: PaymentTaxValidator):
        self.connector = connector
        self.validator = validator

    async def monitor_period(self, start_date: datetime) -> Dict:
        """Monitor payments for tax compliance"""
        async with self.connector:
            # Fetch all payouts
            payouts = await self.connector.fetch_payouts(start_date)
            
            # Validate each payout
            all_flags = []
            for payout in payouts:
                flags = self.validator.validate_transaction(PaymentTransaction(
                    id=payout["id"],
                    date=datetime.fromtimestamp(payout["arrival_date"]),
                    vendor_id=payout["id"],
                    vendor_name="",
                    amount=payout["amount"],
                    currency=payout["currency"],
                    payment_type="",
                    status="",
                    metadata={}
                ))
                if flags:
                    all_flags.extend(flags)
                    # Update payout metadata to mark it as flagged
                    await self.connector.validate_tax_compliance(payout["id"])

            # Summarize results
            return {
                "period_days": (datetime.now() - start_date).days,
                "total_payouts": len(payouts),
                "flagged_payouts": len(set(f.transaction_id for f in all_flags)),
                "flags_by_type": self._summarize_flags(all_flags),
                "total_tax_impact": self._calculate_tax_impact(all_flags)
            }

    def _summarize_flags(self, flags: List[TaxFlag]) -> Dict:
        """Summarize flags by type"""
        summary = {}
        for flag in flags:
            if flag.flag_type not in summary:
                summary[flag.flag_type] = {
                    "count": 0,
                    "total_amount": 0.0
                }
            summary[flag.flag_type]["count"] += 1
            summary[flag.flag_type]["total_amount"] += flag.estimated_tax_amount
        return summary

    def _calculate_tax_impact(self, flags: List[TaxFlag]) -> float:
        """Calculate total tax impact of flags"""
        return sum(flag.estimated_tax_amount for flag in flags)

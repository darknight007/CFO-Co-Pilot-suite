from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
import aiohttp
import asyncio

@dataclass
class ERPTransaction:
    id: str
    date: datetime
    vendor_id: str
    vendor_name: str
    amount: float
    currency: str
    description: str
    ledger_account: str
    tax_details: Dict[str, float]
    invoice_reference: str
    payment_status: str

class ERPSystem(Enum):
    ORACLE = "oracle"
    SAP = "sap"
    NETSUITE = "netsuite"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"

class ERPConnector:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "mock_api_key"
        self.base_url = "https://api.erp.com"

    def get_transaction_details(self, invoice_id: str) -> Dict[str, Any]:
        # Mock implementation
        return {
            "invoice_id": invoice_id,
            "amount": 50000,
            "vendor": "Test Corp",
            "country": "India"
        }

    async def fetch_ledger_entries(self, days: int) -> List[Dict[str, Any]]:
        # Mock implementation
        return [
            {"id": "L1", "amount": 10000, "tax_code": "GST"},
            {"id": "L2", "amount": 20000, "tax_code": "WHT"}
        ]

    async def validate_tax_entries(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        # Mock implementation
        return {
            "valid": True,
            "issues": []
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class NetSuiteConnector(ERPConnector):
    async def fetch_ledger_entries(self, days: int) -> List[ERPTransaction]:
        """Fetch NetSuite ledger entries for specified days"""
        start_date = datetime.now() - timedelta(days=days)
        
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as session:
            async with session.get(
                f"{self.base_url}/suitetalk/rest/transactions",
                params={
                    "start_date": start_date.isoformat(),
                    "type": ["vendorbill", "vendorpayment"]
                }
            ) as response:
                data = await response.json()
                return [self._parse_transaction(item) for item in data["items"]]

    async def validate_tax_entries(self, transaction: ERPTransaction) -> Dict:
        """Validate tax entries in NetSuite"""
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as session:
            async with session.get(
                f"{self.base_url}/suitetalk/rest/transactions/{transaction.id}/tax"
            ) as response:
                tax_data = await response.json()
                
                expected_taxes = self._calculate_expected_taxes(transaction)
                actual_taxes = self._parse_tax_entries(tax_data)
                
                return {
                    "transaction_id": transaction.id,
                    "expected_taxes": expected_taxes,
                    "actual_taxes": actual_taxes,
                    "discrepancies": self._find_discrepancies(
                        expected_taxes, actual_taxes
                    )
                }

    def _parse_transaction(self, data: Dict) -> ERPTransaction:
        """Parse NetSuite transaction data"""
        return ERPTransaction(
            id=data["id"],
            date=datetime.fromisoformat(data["tranDate"]),
            vendor_id=data["entity"]["id"],
            vendor_name=data["entity"]["name"],
            amount=float(data["amount"]),
            currency=data["currency"]["symbol"],
            description=data.get("memo", ""),
            ledger_account=data["account"]["name"],
            tax_details={},  # Will be populated by validate_tax_entries
            invoice_reference=data.get("refNumber", ""),
            payment_status=data["status"]
        )

    def _calculate_expected_taxes(self, transaction: ERPTransaction) -> Dict:
        """Calculate expected taxes based on transaction details"""
        # This would integrate with the tax_engine to calculate expected taxes
        return {
            "withholding_tax": 0.0,
            "vat": 0.0,
            "gst": 0.0
        }

    def _parse_tax_entries(self, tax_data: Dict) -> Dict:
        """Parse actual tax entries from NetSuite"""
        taxes = {}
        for entry in tax_data.get("taxDetails", []):
            tax_type = entry["taxType"]["name"].lower()
            taxes[tax_type] = float(entry["taxAmount"])
        return taxes

    def _find_discrepancies(self, expected: Dict, actual: Dict) -> List[Dict]:
        """Find discrepancies between expected and actual taxes"""
        discrepancies = []
        for tax_type, expected_amount in expected.items():
            actual_amount = actual.get(tax_type, 0.0)
            if abs(expected_amount - actual_amount) > 0.01:  # Account for floating point
                discrepancies.append({
                    "tax_type": tax_type,
                    "expected": expected_amount,
                    "actual": actual_amount,
                    "difference": expected_amount - actual_amount
                })
        return discrepancies

class ERPReconciliationService:
    def __init__(self, connector: ERPConnector):
        self.connector = connector

    async def reconcile_period(self, days: int) -> Dict:
        """Reconcile tax entries for specified period"""
        async with self.connector:
            # Fetch all transactions
            transactions = await self.connector.fetch_ledger_entries(days)
            
            # Validate each transaction
            results = []
            for transaction in transactions:
                validation = await self.connector.validate_tax_entries(transaction)
                if validation["discrepancies"]:
                    results.append(validation)

            # Summarize results
            return {
                "period_days": days,
                "total_transactions": len(transactions),
                "transactions_with_discrepancies": len(results),
                "discrepancy_details": results,
                "total_tax_impact": self._calculate_total_impact(results)
            }

    def _calculate_total_impact(self, results: List[Dict]) -> Dict:
        """Calculate total tax impact of discrepancies"""
        total_impact = {}
        for result in results:
            for discrepancy in result["discrepancies"]:
                tax_type = discrepancy["tax_type"]
                difference = discrepancy["difference"]
                total_impact[tax_type] = total_impact.get(tax_type, 0.0) + difference
        return total_impact

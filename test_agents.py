import json
import asyncio
from datetime import datetime
from tax_engine import TaxEngine
from compliance_engine import ComplianceEngine
from compliance_validator import ComplianceValidator
from cfo_automation import CFOAutomationOrchestrator
from integration.erp_connector import ERPConnector
from integration.payment_gateway import PaymentGatewayConnector
from integration.document_manager import DocumentManager
from integration.gov_portal import GovPortalSubmitter, FilingOrchestrator

async def test_invoice_processing():
    # Load sample invoice
    with open('sample_data/sample_invoice.json', 'r') as f:
        invoice_data = json.load(f)

    print("\n=== Testing Tax Engine ===")
    tax_engine = TaxEngine()
    tax_advice = tax_engine.analyze_transaction(
        source_country=invoice_data['vendor']['country'],
        destination_country=invoice_data['customer']['country'],
        transaction_type="Digital Services",
        amount=invoice_data['payment']['subtotal']
    )
    print("Tax Engine Output:", json.dumps(tax_advice, indent=2))

    print("\n=== Testing Compliance Engine ===")
    compliance_engine = ComplianceEngine()
    checklist = compliance_engine.generate_checklist({
        "country": invoice_data['vendor']['country'],
        "amount": invoice_data['payment']['subtotal'],
        "date": datetime.now()
    })
    print("Compliance Checklist:", json.dumps(checklist, indent=2))

    print("\n=== Testing Compliance Validator ===")
    validator = ComplianceValidator()
    validation_result = validator.validate_requirements({
        "tax_registration": True,
        "valid_tax_id": invoice_data['vendor']['tax_id'],
        "filing_history": ["2024Q4", "2025Q1"]
    })
    print("Validation Result:", json.dumps(validation_result, indent=2))

    print("\n=== Testing CFO Automation ===")
    cfo = CFOAutomationOrchestrator()
    transaction_result = await cfo.process_transaction(invoice_data['invoice_id'])
    print("Transaction Processing Result:", json.dumps(transaction_result, indent=2))

    print("\n=== Testing ERP Integration ===")
    erp = ERPConnector()
    ledger_entries = await erp.fetch_ledger_entries(30)  # Last 30 days
    print("ERP Ledger Entries:", json.dumps(ledger_entries, indent=2))

    print("\n=== Testing Payment Gateway ===")
    payment = PaymentGatewayConnector()
    payment_status = payment.verify_payment(invoice_data['invoice_id'])
    print("Payment Verification:", payment_status)

    print("\n=== Testing Document Management ===")
    docs = DocumentManager()
    vendor_docs = await docs.fetch_documents(invoice_data['vendor']['id'])
    print("Vendor Documents:", json.dumps(vendor_docs, indent=2))

    print("\n=== Testing Government Portal Integration ===")
    gov_portal = GovPortalSubmitter()
    filing_result = gov_portal.submit_filing({
        "form_type": "GST",
        "period": "2025Q1",
        "amount": invoice_data['payment']['tax']['gst'],
        "invoice_id": invoice_data['invoice_id']
    })
    print("Filing Result:", json.dumps(filing_result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_invoice_processing())

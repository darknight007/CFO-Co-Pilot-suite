import json
from tax_engine import TaxEngine, ServiceCategory, TaxJurisdiction
from invoice_analyzer import InvoiceAnalyzer

def test_tax_engine():
    # First analyze the invoice
    analyzer = InvoiceAnalyzer()
    with open('invoice.pdf', 'rb') as f:
        text, images = analyzer.extract_text_from_pdf('invoice.pdf')
    analysis = analyzer.analyze_invoice(text)
    
    # Initialize tax engine
    tax_engine = TaxEngine()
    
    # Get tax advice based on invoice analysis
    tax_advice = tax_engine.get_tax_advice(
        payer_country="India",
        vendor_country="India",
        service_type="Printing",
        transaction_value=analysis.total_amount,
        currency="INR",
        has_permanent_establishment=True,  # Since both entities are Indian
        tax_residency_certificate=True  # Not really needed for domestic transaction
    )
    
    # Print the results
    print("\n=== Invoice Analysis ===")
    print(f"Service Type: {analysis.service_classification.service_type}")
    print(f"Transaction Value: ₹{analysis.total_amount}")
    print(f"GST Details: CGST={analysis.total_cgst}, SGST={analysis.total_sgst}, IGST={analysis.total_igst}")
    
    print("\n=== Tax Advice ===")
    tax_advice_dict = tax_advice.to_dict()
    print(json.dumps(tax_advice_dict, indent=2))

if __name__ == "__main__":
    test_tax_engine()

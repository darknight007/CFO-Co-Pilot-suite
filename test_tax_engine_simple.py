import json
from tax_engine import TaxEngine, ServiceCategory, TaxJurisdiction

def test_tax_engine():
    # Initialize tax engine
    tax_engine = TaxEngine()
    
    # Test case 1: Domestic Indian transaction (Printing Services)
    print("\n=== Test Case 1: Domestic Indian Transaction ===")
    print("Scenario: Printing services between two Indian entities")
    print("Invoice Details:")
    print("- Service: Printing")
    print("- Value: ₹11,000.00")
    print("- CGST: ₹990.00 (9%)")
    print("- SGST: ₹990.00 (9%)")
    
    tax_advice = tax_engine.get_tax_advice(
        payer_country="India",
        vendor_country="India",
        service_type=ServiceCategory.PRINTING.value,
        transaction_value=11000.0,
        currency="INR",
        has_permanent_establishment=True,
        tax_residency_certificate=True
    )
    
    print("\nTax Analysis Results:")
    print(json.dumps(tax_advice.to_dict(), indent=2))
    
    # Test case 2: Cross-border transaction (US-India)
    print("\n=== Test Case 2: Cross-Border Transaction ===")
    print("Scenario: Technical services provided by US entity to Indian entity")
    print("Invoice Details:")
    print("- Service: Technical Services")
    print("- Value: $10,000.00")
    
    tax_advice = tax_engine.get_tax_advice(
        payer_country="India",
        vendor_country="United States",
        service_type=ServiceCategory.TECHNICAL.value,
        transaction_value=10000.0,
        currency="USD",
        has_permanent_establishment=False,
        tax_residency_certificate=True
    )
    
    print("\nTax Analysis Results:")
    print(json.dumps(tax_advice.to_dict(), indent=2))

if __name__ == "__main__":
    test_tax_engine()

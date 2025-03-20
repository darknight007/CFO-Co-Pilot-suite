import json
from tax_engine import TaxEngine, ServiceCategory, TaxJurisdiction

def test_international_scenarios():
    tax_engine = TaxEngine()
    
    # Test scenarios
    scenarios = [
        {
            "name": "UK Company Providing Technical Services to German Client",
            "payer_country": "Germany",
            "vendor_country": "United Kingdom",
            "service_type": ServiceCategory.TECHNICAL.value,
            "value": 50000.0,
            "currency": "EUR"
        },
        {
            "name": "Singapore Company Providing SaaS to French Client",
            "payer_country": "France",
            "vendor_country": "Singapore",
            "service_type": ServiceCategory.SAAS.value,
            "value": 75000.0,
            "currency": "EUR"
        },
        {
            "name": "Indian Company Providing IT Services to UK Client",
            "payer_country": "United Kingdom",
            "vendor_country": "India",
            "service_type": ServiceCategory.TECHNICAL.value,
            "value": 40000.0,
            "currency": "GBP"
        },
        {
            "name": "Singapore Company Providing Cloud Services to Indian Client",
            "payer_country": "India",
            "vendor_country": "Singapore",
            "service_type": ServiceCategory.CLOUD_SERVICES.value,
            "value": 100000.0,
            "currency": "USD"
        },
        {
            "name": "French Company Providing Financial Services to Singapore Client",
            "payer_country": "Singapore",
            "vendor_country": "France",
            "service_type": ServiceCategory.FINANCIAL.value,
            "value": 50000.0,
            "currency": "EUR"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n=== {scenario['name']} ===")
        print(f"Details:")
        print(f"- Payer Country: {scenario['payer_country']}")
        print(f"- Vendor Country: {scenario['vendor_country']}")
        print(f"- Service Type: {scenario['service_type']}")
        print(f"- Value: {scenario['value']} {scenario['currency']}")
        
        tax_advice = tax_engine.get_tax_advice(
            payer_country=scenario['payer_country'],
            vendor_country=scenario['vendor_country'],
            service_type=scenario['service_type'],
            transaction_value=scenario['value'],
            currency=scenario['currency'],
            has_permanent_establishment=False,
            tax_residency_certificate=True
        )
        
        print("\nTax Analysis Results:")
        print(json.dumps(tax_advice.to_dict(), indent=2))

if __name__ == "__main__":
    test_international_scenarios()

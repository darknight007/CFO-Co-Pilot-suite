from invoice_analyzer import InvoiceAnalyzer

# Replace this sample data with your actual invoice information
your_invoice = {
    "payer_country": "United States",      # Replace with actual payer country
    "payer_entity_type": "Company",        # Options: Company, Freelancer, Individual, Partnership, Corporation
    "vendor_country": "India",             # Replace with actual vendor country
    "vendor_entity_type": "Freelancer",    # Options: Company, Freelancer, Individual, Partnership, Corporation
    "industry": "Software Development",     # Replace with actual industry
    "service_location": "Remote delivery"   # Options: Onsite, Offshore, Remote delivery
}

# Analyze the invoice
analyzer = InvoiceAnalyzer()
result = analyzer.analyze_invoice(your_invoice)

# Print the results
print(result.to_json())

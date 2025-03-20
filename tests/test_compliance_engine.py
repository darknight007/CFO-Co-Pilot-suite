import unittest
from datetime import datetime, timedelta
from compliance_engine import ComplianceEngine

class TestComplianceEngine(unittest.TestCase):
    def setUp(self):
        self.compliance_engine = ComplianceEngine()

    def test_generate_compliance_checklist(self):
        tax_data = {
            "country": "Singapore",
            "transaction_type": "Service",
            "amount": 100000,
            "date": datetime.now()
        }
        checklist = self.compliance_engine.generate_checklist(tax_data)
        self.assertIsNotNone(checklist)
        self.assertTrue(any(item for item in checklist if "GST registration" in item["action"]))
        self.assertTrue(any(item for item in checklist if "IRAS filing" in item["action"]))

    def test_calculate_due_dates(self):
        filing_type = "GST"
        transaction_date = datetime.now()
        due_date = self.compliance_engine.calculate_due_date(filing_type, transaction_date)
        self.assertIsInstance(due_date, datetime)
        self.assertTrue(due_date > transaction_date)

    def test_validate_compliance_requirements(self):
        requirements = {
            "tax_registration": True,
            "valid_tax_id": "T12345678",
            "filing_history": ["2023Q1", "2023Q2"]
        }
        validation = self.compliance_engine.validate_requirements(requirements)
        self.assertTrue(validation["is_compliant"])
        self.assertEqual(len(validation["missing_requirements"]), 0)

if __name__ == '__main__':
    unittest.main()

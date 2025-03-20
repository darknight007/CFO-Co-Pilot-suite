import unittest
from unittest.mock import Mock, patch
from cfo_automation import CFOAutomationOrchestrator

class TestCFOAutomation(unittest.TestCase):
    def setUp(self):
        self.orchestrator = CFOAutomationOrchestrator()

    @patch('cfo_automation.ERPConnector')
    @patch('cfo_automation.PaymentGatewayConnector')
    def test_process_transaction_workflow(self, mock_pg, mock_erp):
        mock_erp.get_transaction_details.return_value = {
            "invoice_id": "INV-001",
            "amount": 50000,
            "vendor": "Test Corp",
            "country": "India"
        }
        mock_pg.verify_payment.return_value = True

        result = self.orchestrator.process_transaction("INV-001")
        self.assertTrue(result["success"])
        self.assertIn("compliance_status", result)
        self.assertIn("required_actions", result)

    def test_generate_compliance_report(self):
        test_data = {
            "period": "2023Q3",
            "transactions": [
                {"id": "TX1", "status": "compliant"},
                {"id": "TX2", "status": "pending_review"}
            ]
        }
        report = self.orchestrator.generate_compliance_report(test_data)
        self.assertIn("summary", report)
        self.assertIn("risk_metrics", report)
        self.assertIn("action_items", report)

    @patch('cfo_automation.DocumentManager')
    def test_validate_documentation(self, mock_doc_manager):
        mock_doc_manager.get_documents.return_value = ["tax_cert.pdf", "registration.pdf"]
        validation = self.orchestrator.validate_documentation("vendor123")
        self.assertTrue(validation["documents_complete"])
        self.assertEqual(len(validation["missing_documents"]), 0)

if __name__ == '__main__':
    unittest.main()

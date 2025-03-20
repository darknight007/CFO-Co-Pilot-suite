import unittest
from unittest.mock import Mock, patch
from integration.erp_connector import ERPConnector
from integration.payment_gateway import PaymentGatewayConnector
from integration.document_manager import DocumentManager
from integration.gov_portal import GovPortalSubmitter

class TestIntegrations(unittest.TestCase):
    def setUp(self):
        self.erp = ERPConnector()
        self.payment = PaymentGatewayConnector()
        self.docs = DocumentManager()
        self.gov_portal = GovPortalSubmitter()

    @patch('integration.erp_connector.requests')
    def test_erp_ledger_fetch(self, mock_requests):
        mock_requests.get.return_value.json.return_value = {
            "entries": [
                {"id": "L1", "amount": 10000, "tax_code": "GST"},
                {"id": "L2", "amount": 20000, "tax_code": "WHT"}
            ]
        }
        ledger = self.erp.fetch_ledger_entries("2023Q3")
        self.assertEqual(len(ledger), 2)
        self.assertEqual(ledger[0]["tax_code"], "GST")

    @patch('integration.payment_gateway.stripe')
    def test_payment_gateway_transactions(self, mock_stripe):
        mock_stripe.PaymentIntent.list.return_value = {
            "data": [
                {"id": "pi_1", "amount": 5000, "currency": "usd"},
                {"id": "pi_2", "amount": 7500, "currency": "eur"}
            ]
        }
        transactions = self.payment.get_transactions("2023-09")
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]["currency"], "usd")

    @patch('integration.document_manager.GoogleDrive')
    def test_document_validation(self, mock_drive):
        mock_drive.list_files.return_value = [
            {"name": "tax_cert_2023.pdf", "id": "1"},
            {"name": "registration_doc.pdf", "id": "2"}
        ]
        docs = self.docs.validate_documents("vendor123", ["tax_cert", "registration"])
        self.assertTrue(docs["valid"])
        self.assertEqual(len(docs["found_documents"]), 2)

    @patch('integration.gov_portal.requests')
    def test_gov_portal_submission(self, mock_requests):
        mock_requests.post.return_value.status_code = 200
        mock_requests.post.return_value.json.return_value = {"submission_id": "S123"}
        
        result = self.gov_portal.submit_filing({
            "form_type": "GST",
            "period": "2023Q3",
            "amount": 15000
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["submission_id"], "S123")

if __name__ == '__main__':
    unittest.main()

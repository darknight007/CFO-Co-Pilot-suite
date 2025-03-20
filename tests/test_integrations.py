import pytest
import aiohttp
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from integration.erp_connector import (
    ERPTransaction, NetSuiteConnector, ERPReconciliationService
)
from integration.payment_gateway import (
    PaymentTransaction, StripeConnector, RazorpayConnector,
    PaymentTaxValidator, PaymentMonitoringService
)
from integration.document_manager import (
    Document, DocumentType, GoogleDriveManager,
    DocumentValidationService
)
from integration.gov_portal import (
    SubmissionResult, GSTNPortal, IRSPortal, HMRCPortal,
    FilingOrchestrator
)

@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession"""
    session = Mock()
    session.__aenter__ = Mock()
    session.__aexit__ = Mock()
    return session

@pytest.fixture
def mock_response():
    """Mock aiohttp response"""
    response = Mock()
    response.__aenter__ = Mock()
    response.__aexit__ = Mock()
    return response

@pytest.fixture
def sample_erp_transaction():
    """Sample ERP transaction data"""
    return ERPTransaction(
        id="TX123",
        date=datetime.now(),
        vendor_id="V456",
        vendor_name="Test Vendor",
        amount=1000.0,
        currency="USD",
        description="Technical Services",
        ledger_account="Expenses",
        tax_details={"withholding": 100.0},
        invoice_reference="INV789",
        payment_status="Paid"
    )

@pytest.fixture
def sample_payment_transaction():
    """Sample payment gateway transaction"""
    return PaymentTransaction(
        id="PY123",
        date=datetime.now(),
        vendor_id="V456",
        vendor_name="Test Vendor",
        amount=1000.0,
        currency="USD",
        payment_type="bank_transfer",
        status="completed",
        metadata={
            "service_type": "Technical Services",
            "payer_country": "US",
            "vendor_country": "India"
        }
    )

class TestERPIntegration:
    @pytest.mark.asyncio
    async def test_fetch_ledger_entries(self, mock_session, mock_response):
        """Test fetching ledger entries from NetSuite"""
        # Mock response data
        mock_response.json.return_value = {
            "items": [{
                "id": "TX123",
                "tranDate": "2025-03-20T00:00:00",
                "entity": {"id": "V456", "name": "Test Vendor"},
                "amount": 1000.0,
                "currency": {"symbol": "USD"},
                "memo": "Technical Services",
                "account": {"name": "Expenses"},
                "status": "Paid"
            }]
        }
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        connector = NetSuiteConnector("test_key", "http://test.com")
        connector.session = mock_session

        entries = await connector.fetch_ledger_entries(30)
        
        assert len(entries) == 1
        assert entries[0].id == "TX123"
        assert entries[0].amount == 1000.0
        assert entries[0].vendor_name == "Test Vendor"

    @pytest.mark.asyncio
    async def test_validate_tax_entries(self, mock_session, mock_response, sample_erp_transaction):
        """Test tax entry validation"""
        # Mock tax data response
        mock_response.json.return_value = {
            "taxDetails": [{
                "taxType": {"name": "withholding"},
                "taxAmount": 100.0
            }]
        }
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        connector = NetSuiteConnector("test_key", "http://test.com")
        connector.session = mock_session

        validation = await connector.validate_tax_entries(sample_erp_transaction)
        
        assert validation["transaction_id"] == "TX123"
        assert "withholding" in validation["actual_taxes"]
        assert validation["actual_taxes"]["withholding"] == 100.0

class TestPaymentGateway:
    @pytest.mark.asyncio
    async def test_fetch_stripe_payouts(self, mock_session, mock_response):
        """Test fetching payouts from Stripe"""
        # Mock Stripe response
        mock_response.json.return_value = {
            "data": [{
                "id": "py_123",
                "created": int(datetime.now().timestamp()),
                "amount": 100000,  # $1000.00
                "currency": "usd",
                "destination": {
                    "id": "acct_123",
                    "name": "Test Vendor"
                },
                "type": "bank_transfer",
                "status": "paid",
                "metadata": {}
            }]
        }
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        connector = StripeConnector("test_key", "http://test.com")
        connector.session = mock_session

        payouts = await connector.fetch_payouts(30)
        
        assert len(payouts) == 1
        assert payouts[0].id == "py_123"
        assert payouts[0].amount == 1000.00  # Converted from cents
        assert payouts[0].currency == "USD"

    @pytest.mark.asyncio
    async def test_payment_tax_validation(self, sample_payment_transaction):
        """Test payment tax validation"""
        # Mock tax engine
        mock_tax_engine = Mock()
        mock_tax_engine.get_tax_advice.return_value = Mock(
            withholding_required=True,
            withholding_rate=0.1,
            indirect_tax_required=True,
            indirect_tax_type="GST",
            indirect_tax_rate=0.18
        )

        validator = PaymentTaxValidator(mock_tax_engine, Mock())
        flags = validator.validate_transaction(sample_payment_transaction)
        
        assert len(flags) == 2  # Should flag missing withholding and GST
        assert flags[0].flag_type == "MISSING_WITHHOLDING"
        assert flags[1].flag_type == "MISSING_INDIRECT_TAX"

class TestDocumentManagement:
    @pytest.mark.asyncio
    async def test_fetch_documents(self, mock_session, mock_response):
        """Test fetching documents from Google Drive"""
        # Mock Drive response
        mock_response.json.return_value = {
            "files": [{
                "id": "doc123",
                "name": "Service Agreement.pdf",
                "mimeType": "application/pdf",
                "modifiedTime": "2025-03-20T00:00:00Z",
                "webViewLink": "http://drive.google.com/doc123",
                "properties": {
                    "vendor_id": "V456",
                    "doc_type": "service_agreement",
                    "valid_from": "2025-01-01T00:00:00Z",
                    "valid_until": "2025-12-31T00:00:00Z"
                }
            }]
        }
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        manager = GoogleDriveManager("test_key", "http://test.com")
        manager.session = mock_session

        docs = await manager.fetch_documents("V456", DocumentType.SERVICE_AGREEMENT)
        
        assert len(docs) == 1
        assert docs[0].id == "doc123"
        assert docs[0].type == "service_agreement"
        assert docs[0].vendor_id == "V456"

class TestGovernmentPortals:
    @pytest.mark.asyncio
    async def test_gstn_submission(self, mock_session, mock_response):
        """Test GSTN portal submission"""
        # Mock GSTN response
        mock_response.json.return_value = {
            "reference_id": "GST123",
            "ack_num": "ACK456",
            "status": "SUBMITTED"
        }
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value = mock_response

        portal = GSTNPortal("test_key", "test_secret", "http://test.com")
        portal.session = mock_session

        result = await portal.submit_filing({"test": "data"})
        
        assert result.portal == "GSTN"
        assert result.submission_id == "GST123"
        assert result.acknowledgment_number == "ACK456"
        assert result.status == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_filing_orchestrator(self):
        """Test filing orchestrator with multiple portals"""
        orchestrator = FilingOrchestrator()
        
        # Mock portals
        mock_gstn = Mock()
        mock_gstn.submit_filing.return_value = SubmissionResult(
            portal="GSTN",
            submission_id="GST123",
            timestamp=datetime.now(),
            status="SUBMITTED",
            acknowledgment_number="ACK456",
            errors=[],
            raw_response={}
        )
        
        orchestrator.register_portal("INDIA", mock_gstn)
        
        result = await orchestrator.submit_filing("INDIA", {"test": "data"})
        
        assert result.portal == "GSTN"
        assert result.status == "SUBMITTED"
        assert result.submission_id == "GST123"

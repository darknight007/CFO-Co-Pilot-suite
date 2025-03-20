from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
import aiohttp
from abc import ABC, abstractmethod
from enum import Enum
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

@dataclass
class Document:
    id: str
    name: str
    type: str
    vendor_id: str
    valid_from: datetime
    valid_until: Optional[datetime]
    metadata: Dict
    content_url: str

class DocumentType(Enum):
    SERVICE_AGREEMENT = "service_agreement"
    SOW = "statement_of_work"
    TAX_RESIDENCY = "tax_residency_certificate"
    PE_CERTIFICATE = "pe_certificate"
    INVOICE = "invoice"
    TAX_FORM = "tax_form"
    TAX_CERTIFICATE = "tax_certificate"
    REGISTRATION = "registration"
    CONTRACT = "contract"

class DocumentManager(ABC):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "mock_api_key"
        self.required_documents = {
            "invoice": ["pdf", "xml"],
            "tax_certificate": ["pdf"],
            "registration": ["pdf", "jpg"]
        }

    async def fetch_documents(self, entity_id: str) -> List[Dict[str, Any]]:
        """Mock implementation of document fetching"""
        # In a real implementation, this would call the document management API
        mock_docs = [
            {
                "id": "DOC001",
                "type": "invoice",
                "format": "pdf",
                "url": "https://example.com/docs/invoice.pdf",
                "uploaded_at": "2025-03-20T10:30:00Z",
                "status": "verified"
            },
            {
                "id": "DOC002",
                "type": "tax_certificate",
                "format": "pdf",
                "url": "https://example.com/docs/tax_cert.pdf",
                "uploaded_at": "2025-01-15T09:00:00Z",
                "status": "verified"
            }
        ]
        return mock_docs

    async def validate_document_set(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock implementation of document validation"""
        result = {
            "valid": True,
            "missing_documents": [],
            "invalid_formats": [],
            "expired_documents": []
        }

        # Check for required document types
        doc_types = {doc["type"]: doc for doc in documents}
        for required_type in self.required_documents:
            if required_type not in doc_types:
                result["valid"] = False
                result["missing_documents"].append(required_type)
            else:
                doc = doc_types[required_type]
                if doc["format"] not in self.required_documents[required_type]:
                    result["valid"] = False
                    result["invalid_formats"].append({
                        "type": required_type,
                        "current_format": doc["format"],
                        "allowed_formats": self.required_documents[required_type]
                    })

        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class GoogleDriveManager(DocumentManager):
    async def fetch_documents(self, vendor_id: str, doc_type: DocumentType) -> List[Document]:
        """Fetch documents from Google Drive"""
        query = self._build_drive_query(vendor_id, doc_type)
        
        async with self.session.get(
            f"{self.base_url}/drive/v3/files",
            params={
                "q": query,
                "fields": "files(id,name,mimeType,modifiedTime,webViewLink,properties)"
            }
        ) as response:
            data = await response.json()
            return [self._parse_document(item) for item in data.get("files", [])]

    async def validate_document_set(self, vendor_id: str, required_docs: List[DocumentType]) -> Dict:
        """Validate if all required documents are present and valid"""
        validation_results = {
            "vendor_id": vendor_id,
            "timestamp": datetime.now().isoformat(),
            "missing_documents": [],
            "expired_documents": [],
            "valid_documents": []
        }

        for doc_type in required_docs:
            docs = await self.fetch_documents(vendor_id, doc_type)
            
            if not docs:
                validation_results["missing_documents"].append(doc_type.value)
                continue
                
            # Get the most recent document
            latest_doc = max(docs, key=lambda d: d.valid_from)
            
            # Check if document is expired
            if latest_doc.valid_until and latest_doc.valid_until < datetime.now():
                validation_results["expired_documents"].append({
                    "type": doc_type.value,
                    "id": latest_doc.id,
                    "expired_on": latest_doc.valid_until.isoformat()
                })
            else:
                validation_results["valid_documents"].append({
                    "type": doc_type.value,
                    "id": latest_doc.id,
                    "valid_until": latest_doc.valid_until.isoformat() if latest_doc.valid_until else None
                })

        return validation_results

    def _build_drive_query(self, vendor_id: str, doc_type: DocumentType) -> str:
        """Build Google Drive search query"""
        return f"properties has {{ key='vendor_id' and value='{vendor_id}' }} and " \
               f"properties has {{ key='doc_type' and value='{doc_type.value}' }}"

    def _parse_document(self, data: Dict) -> Document:
        """Parse Google Drive file metadata into Document"""
        properties = data.get("properties", {})
        return Document(
            id=data["id"],
            name=data["name"],
            type=properties.get("doc_type"),
            vendor_id=properties.get("vendor_id"),
            valid_from=datetime.fromisoformat(properties.get("valid_from", data["modifiedTime"])),
            valid_until=datetime.fromisoformat(properties["valid_until"]) if "valid_until" in properties else None,
            metadata=properties,
            content_url=data["webViewLink"]
        )

class ProperDocumentManager(DocumentManager):
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key, base_url)
        self.credentials = None
        self.service = None

    async def fetch_documents(self, vendor_id: str, doc_type: DocumentType) -> List[Document]:
        # Mock implementation
        return [
            Document(
                id="1",
                name="tax_cert_2023.pdf",
                type=doc_type.value,
                vendor_id=vendor_id,
                valid_from=datetime.now(),
                valid_until=None,
                metadata={},
                content_url="https://example.com/document1"
            ),
            Document(
                id="2",
                name="registration_doc.pdf",
                type=doc_type.value,
                vendor_id=vendor_id,
                valid_from=datetime.now(),
                valid_until=None,
                metadata={},
                content_url="https://example.com/document2"
            )
        ]

    async def validate_document_set(self, vendor_id: str, required_docs: List[DocumentType]) -> Dict:
        validation_results = {
            "vendor_id": vendor_id,
            "timestamp": datetime.now().isoformat(),
            "missing_documents": [],
            "expired_documents": [],
            "valid_documents": []
        }

        for doc_type in required_docs:
            docs = await self.fetch_documents(vendor_id, doc_type)
            
            if not docs:
                validation_results["missing_documents"].append(doc_type.value)
                continue
                
            # Get the most recent document
            latest_doc = max(docs, key=lambda d: d.valid_from)
            
            # Check if document is expired
            if latest_doc.valid_until and latest_doc.valid_until < datetime.now():
                validation_results["expired_documents"].append({
                    "type": doc_type.value,
                    "id": latest_doc.id,
                    "expired_on": latest_doc.valid_until.isoformat()
                })
            else:
                validation_results["valid_documents"].append({
                    "type": doc_type.value,
                    "id": latest_doc.id,
                    "valid_until": latest_doc.valid_until.isoformat() if latest_doc.valid_until else None
                })

        return validation_results

class DocumentValidationService:
    def __init__(self, document_manager: DocumentManager):
        self.document_manager = document_manager

    async def validate_vendor_compliance(self, vendor_id: str, tax_advice: Dict) -> Dict:
        """Validate vendor's document compliance based on tax advice"""
        required_docs = self._determine_required_documents(tax_advice)
        
        async with self.document_manager:
            validation_results = await self.document_manager.validate_document_set(
                vendor_id, required_docs
            )
            
            return {
                "vendor_id": vendor_id,
                "compliance_status": self._determine_compliance_status(validation_results),
                "validation_details": validation_results,
                "risk_level": self._assess_risk_level(validation_results),
                "action_items": self._generate_action_items(validation_results)
            }

    def _determine_required_documents(self, tax_advice: Dict) -> List[DocumentType]:
        """Determine required documents based on tax advice"""
        required_docs = [DocumentType.SERVICE_AGREEMENT, DocumentType.INVOICE]
        
        if tax_advice.get("dtaa_applicable"):
            required_docs.append(DocumentType.TAX_RESIDENCY)
            
        if tax_advice.get("pe_risk"):
            required_docs.append(DocumentType.PE_CERTIFICATE)
            
        return required_docs

    def _determine_compliance_status(self, validation_results: Dict) -> str:
        """Determine overall compliance status"""
        if validation_results["missing_documents"]:
            return "NON_COMPLIANT"
        if validation_results["expired_documents"]:
            return "PARTIALLY_COMPLIANT"
        return "COMPLIANT"

    def _assess_risk_level(self, validation_results: Dict) -> str:
        """Assess risk level based on validation results"""
        if len(validation_results["missing_documents"]) > 1:
            return "HIGH"
        if validation_results["missing_documents"] or validation_results["expired_documents"]:
            return "MEDIUM"
        return "LOW"

    def _generate_action_items(self, validation_results: Dict) -> List[Dict]:
        """Generate action items based on validation results"""
        actions = []
        
        for doc_type in validation_results["missing_documents"]:
            actions.append({
                "type": "OBTAIN_DOCUMENT",
                "document_type": doc_type,
                "priority": "HIGH",
                "deadline": (datetime.now() + timedelta(days=7)).isoformat()
            })
            
        for doc in validation_results["expired_documents"]:
            actions.append({
                "type": "RENEW_DOCUMENT",
                "document_type": doc["type"],
                "document_id": doc["id"],
                "priority": "HIGH",
                "deadline": (datetime.now() + timedelta(days=7)).isoformat()
            })
            
        return actions

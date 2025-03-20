from datetime import datetime
from typing import Dict, List, Optional, Any
import json

from tax_engine import TaxEngine
from compliance_engine import ComplianceEngine, FormGenerator
from compliance_validator import ComplianceValidator
from service_classifier import ServiceClassifier
from integration.erp_connector import ERPConnector
from integration.payment_gateway import PaymentGatewayConnector
from integration.document_manager import DocumentManager

class AutomationOrchestrator:
    def __init__(self):
        self.tax_engine = TaxEngine()
        self.compliance_engine = ComplianceEngine()
        self.form_generator = FormGenerator()
        self.compliance_validator = ComplianceValidator()
        self.service_classifier = ServiceClassifier()
        
    async def process_transaction(self, transaction_data: dict) -> dict:
        """Process a transaction through the entire compliance workflow"""
        try:
            # Step 1: Extract and classify
            entities = self._extract_entities(transaction_data)
            service_type = self.service_classifier.classify_service(
                transaction_data.get("description", "")
            )
            
            # Step 2: Get tax advice
            tax_advice = self.tax_engine.get_tax_advice(
                payer_country=entities["payer_country"],
                vendor_country=entities["vendor_country"],
                service_type=service_type,
                transaction_value=transaction_data.get("amount", 0),
                currency=transaction_data.get("currency", "USD"),
                has_permanent_establishment=entities.get("has_pe", False),
                tax_residency_certificate=entities.get("has_trc", False)
            )
            
            # Step 3: Generate compliance checklist
            compliance_actions = self.compliance_engine.generate_compliance_checklist(
                tax_advice=tax_advice.to_dict(),
                transaction_date=datetime.now()
            )
            
            # Step 4: Generate draft filings
            filing_drafts = self._generate_filing_drafts(
                tax_advice=tax_advice.to_dict(),
                transaction_data=transaction_data,
                entities=entities
            )
            
            # Step 5: Validate filings
            validation_results = []
            for filing in filing_drafts:
                result = self.compliance_validator.validate_filing(
                    tax_data=tax_advice.to_dict(),
                    compliance_data=filing
                )
                validation_results.append(result)
            
            # Step 6: Prepare response
            response = {
                "transaction_id": transaction_data.get("id"),
                "status": "processed",
                "tax_advice": tax_advice.to_dict(),
                "compliance_actions": [action.__dict__ for action in compliance_actions],
                "filing_drafts": filing_drafts,
                "validation_results": [result.__dict__ for result in validation_results],
                "dashboard_metrics": self._generate_dashboard_metrics(
                    tax_advice, compliance_actions, validation_results
                )
            }
            
            # Step 7: Handle escalations
            if self._requires_escalation(validation_results):
                response["status"] = "escalated"
                await self._notify_compliance_officer(response)
            
            return response
            
        except Exception as e:
            error_response = {
                "transaction_id": transaction_data.get("id"),
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._notify_compliance_officer(error_response)
            return error_response

    def _extract_entities(self, transaction_data: dict) -> dict:
        """Extract relevant entities from transaction data"""
        return {
            "payer_name": transaction_data.get("payer", {}).get("name"),
            "payer_country": transaction_data.get("payer", {}).get("country"),
            "payer_tax_id": transaction_data.get("payer", {}).get("tax_id"),
            "vendor_name": transaction_data.get("vendor", {}).get("name"),
            "vendor_country": transaction_data.get("vendor", {}).get("country"),
            "vendor_tax_id": transaction_data.get("vendor", {}).get("tax_id"),
            "has_pe": transaction_data.get("vendor", {}).get("has_pe", False),
            "has_trc": transaction_data.get("vendor", {}).get("has_trc", False)
        }

    def _generate_filing_drafts(self, tax_advice: dict, 
                              transaction_data: dict, 
                              entities: dict) -> List[dict]:
        """Generate all required filing drafts"""
        drafts = []
        
        # Combine data for form generation
        form_data = {
            **transaction_data,
            **entities,
            **tax_advice
        }
        
        # Generate jurisdiction-specific forms
        if tax_advice.get("jurisdiction") == "INDIA":
            if tax_advice.get("foreign_remittance"):
                drafts.append(
                    self.form_generator.generate_form_15ca(form_data)
                )
                
        elif tax_advice.get("jurisdiction") == "USA":
            if tax_advice.get("withholding_applicable"):
                drafts.append(
                    self.form_generator.generate_1042s(form_data)
                )
                
        elif tax_advice.get("jurisdiction") in ["EU_FR", "EU_DE", "UK"]:
            drafts.append(
                self.form_generator.generate_vat_invoice(form_data)
            )
            
        return drafts

    def _generate_dashboard_metrics(self, tax_advice: dict,
                                 compliance_actions: List,
                                 validation_results: List) -> dict:
        """Generate metrics for CFO dashboard"""
        return {
            "tax_impact": {
                "total_tax": sum(tax.get("amount", 0) 
                               for tax in tax_advice.get("applicable_taxes", {}).values()),
                "currency": tax_advice.get("currency", "USD")
            },
            "compliance_status": {
                "pending": len([a for a in compliance_actions 
                              if a.status == "PENDING"]),
                "completed": len([a for a in compliance_actions 
                                if a.status == "COMPLETED"]),
                "escalated": len([a for a in compliance_actions 
                                if a.status == "ESCALATED"])
            },
            "risk_metrics": {
                "high_risk_issues": len([r for r in validation_results 
                                       if any(i.risk_level == "HIGH" 
                                            for i in r.issues)]),
                "total_issues": sum(len(r.issues) for r in validation_results)
            }
        }

    def _requires_escalation(self, validation_results: List) -> bool:
        """Check if results require escalation"""
        return any(
            any(issue.requires_escalation for issue in result.issues)
            for result in validation_results
        )

    async def _notify_compliance_officer(self, data: dict):
        """Notify compliance officer of issues requiring attention"""
        # Implementation would depend on notification system
        # Could be email, Slack, or internal ticketing system
        pass


class CFOAutomationOrchestrator:
    def __init__(self):
        self.erp = ERPConnector()
        self.payment = PaymentGatewayConnector()
        self.docs = DocumentManager()
        self.compliance = ComplianceEngine()
        self.validator = ComplianceValidator()

    async def process_transaction(self, invoice_id: str) -> Dict[str, Any]:
        """Process a transaction through all compliance checks"""
        result = {
            "invoice_id": invoice_id,
            "status": "processing",
            "steps": [],
            "issues": []
        }

        # Step 1: Get transaction details from ERP
        try:
            transaction = self.erp.get_transaction_details(invoice_id)
            result["steps"].append({
                "step": "ERP Verification",
                "status": "completed",
                "data": transaction
            })
        except Exception as e:
            result["issues"].append(f"ERP verification failed: {str(e)}")
            result["status"] = "failed"
            return result

        # Step 2: Verify payment status
        try:
            payment_verified = self.payment.verify_payment(invoice_id)
            result["steps"].append({
                "step": "Payment Verification",
                "status": "completed" if payment_verified else "failed",
                "data": {"verified": payment_verified}
            })
            if not payment_verified:
                result["issues"].append("Payment verification failed")
                result["status"] = "failed"
                return result
        except Exception as e:
            result["issues"].append(f"Payment verification failed: {str(e)}")
            result["status"] = "failed"
            return result

        # Step 3: Generate compliance checklist
        try:
            checklist = self.compliance.generate_checklist({
                "country": transaction["country"],
                "amount": transaction["amount"],
                "date": datetime.now()
            })
            result["steps"].append({
                "step": "Compliance Checklist",
                "status": "completed",
                "data": checklist
            })
        except Exception as e:
            result["issues"].append(f"Compliance checklist generation failed: {str(e)}")
            result["status"] = "failed"
            return result

        # Step 4: Validate compliance
        try:
            # Mock filing history for testing
            filing_history = ["2024Q4", "2025Q1"] if transaction["country"] == "India" else []
            
            validation = self.validator.validate_requirements({
                "tax_registration": True,  # Mock value
                "valid_tax_id": transaction.get("tax_id", ""),
                "filing_history": filing_history
            })
            
            if validation and isinstance(validation, dict):
                result["steps"].append({
                    "step": "Compliance Validation",
                    "status": "completed" if validation.get("valid", False) else "failed",
                    "data": validation
                })
                if not validation.get("valid", False):
                    result["issues"].extend(validation.get("issues", []))
                    result["status"] = "failed"
                    return result
            else:
                raise ValueError("Invalid validation result")
                
        except Exception as e:
            result["issues"].append(f"Compliance validation failed: {str(e)}")
            result["status"] = "failed"
            return result

        result["status"] = "completed"
        return result

    async def generate_compliance_report(self, invoice_id: str) -> Dict[str, Any]:
        """Generate a comprehensive compliance report"""
        report = {
            "invoice_id": invoice_id,
            "timestamp": datetime.now().isoformat(),
            "sections": []
        }

        # Add transaction processing results
        process_result = await self.process_transaction(invoice_id)
        report["sections"].append({
            "title": "Transaction Processing",
            "data": process_result
        })

        # Add document validation
        try:
            docs = await self.docs.fetch_documents(invoice_id)
            if docs:
                doc_validation = await self.docs.validate_document_set(docs)
                report["sections"].append({
                    "title": "Document Validation",
                    "data": doc_validation
                })
            else:
                report["sections"].append({
                    "title": "Document Validation",
                    "error": "No documents found"
                })
        except Exception as e:
            report["sections"].append({
                "title": "Document Validation",
                "error": str(e)
            })

        return report

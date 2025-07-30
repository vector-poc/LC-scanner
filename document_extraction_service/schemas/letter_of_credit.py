"""Letter of Credit specific analysis schema based on MT700 message format."""

from typing import Dict, List, Optional, Type
from pydantic import BaseModel, Field
from .base import BaseDocumentSchema

class DocumentRequirement(BaseModel):
    """A specific document required for LC compliance."""
    name: str = Field(description="The exact name/type of the document as stated in the LC")
    description: Optional[str] = Field(default=None, description="Detailed requirements, conditions, and specifications for this document")
    quantity: int = Field(default=1, description="Number of copies required, default is 1 if not specified")
    validation_criteria: Optional[List[str]] = Field(default=None, description="List of specific validation criteria that must be met for this document to be considered valid")


class LetterOfCreditAnalysis(BaseModel):
    """Letter of Credit analysis structure based on MT700 fields and extraction map."""
    
    # Reference & scope
    LC_REFERENCE: Optional[str] = Field(default=None, description="Unique number that identifies the letter of credit (MT700 tag 20)")
    SEQUENCE_OF_TOTAL: Optional[str] = Field(default=None, description="Indicates message sequence when an LC is split over several MT700s (tag 27)")
    DATE_OF_ISSUE: Optional[str] = Field(default=None, description="Date on which the issuing bank generated the LC (tag 31C)")
    APPLICABLE_RULES: Optional[str] = Field(default=None, description="Rulebooks the LC is subject to, e.g. UCP 600, ISBP 821, Incoterms 2020 (tag 40E)")
    
    # Parties
    APPLICANT: Optional[str] = Field(default=None, description="Importer / buyer who requests the LC (tag 50)")
    APPLICANT_BANK: Optional[str] = Field(default=None, description="Bank acting for the applicant if different from the issuer (tag 51A)")
    BENEFICIARY: Optional[str] = Field(default=None, description="Exporter / seller named to receive payment (tag 59)")
    AVAILABLE_WITH_BANK: Optional[str] = Field(default=None, description="Bank with which the credit is available for payment / negotiation (tag 41A)")
    REIMBURSING_BANK: Optional[str] = Field(default=None, description="Bank that reimburses the paying bank (tag 53A)")
    ADVISING_BANK: Optional[str] = Field(default=None, description="Bank that advises or confirms the LC to the beneficiary (tag 57A)")
    INSTRUCTIONS_TO_BANK: Optional[str] = Field(default=None, description="Any special banking instructions (tag 78)")
    
    # Amounts & tolerances
    CREDIT_AMOUNT: Optional[str] = Field(default=None, description="Face value and currency of the LC (tag 32B)")
    PERCENT_TOLERANCE: Optional[str] = Field(default=None, description="±% tolerance allowed on credit amount or quantity (tag 39A)")
    MAX_CREDIT_AMOUNT: Optional[str] = Field(default=None, description="Absolute ceiling amount if stated instead of a % (tag 39B)")
    ADDITIONAL_AMOUNTS: Optional[str] = Field(default=None, description="Whether freight, insurance, etc. may be added (tag 39C)")
    
    # Availability & payment
    FORM_OF_CREDIT: Optional[str] = Field(default=None, description="Irrevocable, transferable, standby, etc. (tag 40A)")
    AVAILABILITY: Optional[str] = Field(default=None, description="Means of payment—sight, deferred, acceptance, negotiation (tag 41A)")
    DRAFT_TENOR: Optional[str] = Field(default=None, description="Sight / 30 days / 60 days, etc., for draft presentation (tag 42C)")
    DRAWEE: Optional[str] = Field(default=None, description="Party on whom drafts are to be drawn (tag 42A)")
    MIXED_PAYMENT_DETAILS: Optional[str] = Field(default=None, description="Details when payment is partly at sight, partly deferred (tag 42M)")
    DEFERRED_PAYMENT_DETAILS: Optional[str] = Field(default=None, description="Pure deferred-payment schedule (tag 42P)")
    CONFIRMATION_INSTRUCTIONS: Optional[str] = Field(default=None, description="Whether confirmation is requested or allowed (tag 49)")
    
    # Presentation & expiry
    EXPIRY_DATE_AND_PLACE: Optional[str] = Field(default=None, description="Final date and place for document presentation (tag 31D)")
    PERIOD_FOR_PRESENTATION: Optional[str] = Field(default=None, description="Maximum days after shipment to present docs (tag 48)")
    PARTIAL_SHIPMENTS: Optional[str] = Field(default=None, description="Whether splits are allowed (tag 43P)")
    TRANSSHIPMENT: Optional[str] = Field(default=None, description="Whether trans-shipment is allowed (tag 43T)")
    
    # Shipment & delivery
    LATEST_SHIPMENT_DATE: Optional[str] = Field(default=None, description="Last permissible shipment date (tag 44C)")
    SHIPMENT_PERIOD: Optional[str] = Field(default=None, description="Permitted shipment window if expressed as a period (tag 44D)")
    DISPATCH_PLACE: Optional[str] = Field(default=None, description="Place goods are taken in charge / dispatched (tag 44A)")
    PORT_OF_LOADING: Optional[str] = Field(default=None, description="Port where goods are loaded on the main carriage (tag 44E)")
    PORT_OF_DISCHARGE: Optional[str] = Field(default=None, description="Port where goods are unloaded (tag 44F)")
    FINAL_DESTINATION: Optional[str] = Field(default=None, description="Ultimate place of delivery named in the LC (tag 44B)")
    
    # Merchandise & documents
    GOODS_DESCRIPTION: Optional[str] = Field(default=None, description="Official description of goods or services (tag 45A)")
    DOCUMENTS_REQUIRED: Optional[List[DocumentRequirement]] = Field(default=None, description="List of documents the exporter must present (tag 46A)")
    ADDITIONAL_CONDITIONS: Optional[str] = Field(default=None, description="Extra clauses or conditions (tag 47A)")
    
    # Charges
    CHARGES: Optional[str] = Field(default=None, description="Who pays which banking/handling fees (tag 71B)")
    
    # Rule-related meta-fields (derived, not in MT700 proper)
    INCOTERM_RULE: Optional[str] = Field(default=None, description="Incoterms code such as CIF, FOB, DDP, etc.")
    INCOTERM_YEAR: Optional[str] = Field(default=None, description="Incoterms publication year (e.g. 2020)")
    INCOTERM_NAMED_PLACE: Optional[str] = Field(default=None, description="Named place or port that completes the Incoterm")
    RULEBOOK_VERSIONS: Optional[Dict[str, Optional[str]]] = Field(default=None, description="Dictionary of rulebook → version numbers, e.g. {'UCP': '600', 'ISBP': '821'}")


class LetterOfCreditSchema(BaseDocumentSchema):
    """Schema for Letter of Credit analysis based on MT700 message format."""
    
    @property
    def schema_class(self) -> Type[BaseModel]:
        return LetterOfCreditAnalysis
    
    @property
    def prompt_template(self) -> str:
        return """This appears to be a Letter of Credit (LC) document. Extract information into the MT700-based structure below.
For each field, look for the corresponding information in the document. If a field is not present or unclear, set it to null.

EXTRACTION GUIDELINES:
- Reference & Scope: LC number, issue date, applicable rules (UCP, ISBP, etc.)
- Parties: All banks and trading parties involved
- Amounts: Credit amounts, tolerances, additional amounts
- Payment: Form of credit, availability, draft terms, confirmation
- Expiry: Expiry dates, presentation periods, shipment restrictions
- Shipment: Loading/discharge ports, destinations, shipment dates
- Goods: Description of merchandise or services
- Documents: For DOCUMENTS_REQUIRED, create a list where each document has:
  * name: The exact document name as stated (e.g. "Commercial Invoice", "Bill of Lading")
  * description: All specific requirements, conditions, and details for that document
  * quantity: Extract the actual number of copies required from phrases like "four fold" = 4, "two fold" = 2, "duplicate" = 2, "triplicate" = 3, "in [X] copies" = X. If no quantity is specified, use 1.
  * validation_criteria: A comprehensive list of specific, actionable validation criteria extracted from the document description. Analyze EVERY requirement, condition, specification, and restriction mentioned for each document. Include criteria about:
    - Document authenticity (original, certified, laminated, etc.)
    - Required signatures, stamps, seals
    - Content requirements (what must be stated/shown)
    - Format/presentation requirements
    - Issuing authority requirements
    - Compliance with regulations/standards
    - Age/date restrictions
    - Specific wordings or certifications required
    - Bank stamps or endorsements needed
    - Prohibited alternatives (e.g. "short form not acceptable")
    DO NOT include quantity/copy requirements as those are captured in the quantity field. Extract EVERY validation requirement from the description text.
- Charges: Fee allocation between parties
- Incoterms: Trade terms if specified (CIF, FOB, etc.)

Extract exactly as the fields appear in the document. Preserve original wording and formatting.
For documents, separate each distinct document type into its own object with precise name and detailed description."""
    
    @property
    def json_example(self) -> str:
        return """{
  "LC_REFERENCE": "string or null",
  "SEQUENCE_OF_TOTAL": "string or null",
  "DATE_OF_ISSUE": "string or null",
  "APPLICABLE_RULES": "string or null",
  "APPLICANT": "string or null",
  "APPLICANT_BANK": "string or null",
  "BENEFICIARY": "string or null",
  "AVAILABLE_WITH_BANK": "string or null",
  "REIMBURSING_BANK": "string or null",
  "ADVISING_BANK": "string or null",
  "INSTRUCTIONS_TO_BANK": "string or null",
  "CREDIT_AMOUNT": "string or null",
  "PERCENT_TOLERANCE": "string or null",
  "MAX_CREDIT_AMOUNT": "string or null",
  "ADDITIONAL_AMOUNTS": "string or null",
  "FORM_OF_CREDIT": "string or null",
  "AVAILABILITY": "string or null",
  "DRAFT_TENOR": "string or null",
  "DRAWEE": "string or null",
  "MIXED_PAYMENT_DETAILS": "string or null",
  "DEFERRED_PAYMENT_DETAILS": "string or null",
  "CONFIRMATION_INSTRUCTIONS": "string or null",
  "EXPIRY_DATE_AND_PLACE": "string or null",
  "PERIOD_FOR_PRESENTATION": "string or null",
  "PARTIAL_SHIPMENTS": "string or null",
  "TRANSSHIPMENT": "string or null",
  "LATEST_SHIPMENT_DATE": "string or null",
  "SHIPMENT_PERIOD": "string or null",
  "DISPATCH_PLACE": "string or null",
  "PORT_OF_LOADING": "string or null",
  "PORT_OF_DISCHARGE": "string or null",
  "FINAL_DESTINATION": "string or null",
  "GOODS_DESCRIPTION": "string or null",
  "DOCUMENTS_REQUIRED": [
    {
      "name": "Commercial Invoice",
      "description": "Signed in duplicate stating goods, quantity, unit price, total amount, etc.",
      "quantity": 2,
      "validation_criteria": [
        "Must be manually signed",
        "Must state goods, quantity, unit price, total amount",
        "Must quote LC number and date",
        "Must show FOB value, freight and insurance separately"
      ]
    },
    {
      "name": "Bill of Lading",
      "description": "Full set of clean on-board marine bills of lading marked freight prepaid, made out to order of issuing bank, showing applicant as notify party. Short form not acceptable.",
      "quantity": 2,
      "validation_criteria": [
        "Must be clean (no adverse remarks)",
        "Must be on-board type (not received for shipment)",
        "Must be marked freight prepaid",
        "Must be made out to order of issuing bank", 
        "Must show applicant as notify party with full address",
        "Short form bills of lading not acceptable",
        "Must state vessel's local agent name, address and telephone in Sri Lanka"
      ]
    }
  ] or null,
  "ADDITIONAL_CONDITIONS": "string or null",
  "CHARGES": "string or null",
  "INCOTERM_RULE": "string or null",
  "INCOTERM_YEAR": "string or null",
  "INCOTERM_NAMED_PLACE": "string or null",
  "RULEBOOK_VERSIONS": {"UCP": "600", "ISBP": "821"} or null
}"""
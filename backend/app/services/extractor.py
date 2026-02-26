import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.llm import get_llm
from app.models.schemas import Intent


class ExtractionResult(BaseModel):
    intents: list[Intent] = Field(
        default_factory=list,
        description="All customer intents detected in the email.",
    )
    contract_number: Optional[str] = Field(
        None,
        description="Customer contract or customer number. Note: Customers often use 'meter number' to refer to their contract number.",
    )
    full_name: Optional[str] = Field(
        None, description="Full name of the customer if present."
    )
    postal_code: Optional[str] = Field(
        None, description="5-digit postal code if present."
    )
    meter_number: Optional[str] = Field(
        None,
        description="Specific meter ID if provided separately from the contract number identification.",
    )
    meter_reading_kwh: Optional[int] = Field(
        None, description="Electricity meter reading value in kWh if present."
    )


def normalize_contract_number(value: str | None) -> str | None:
    if not value:
        return None
    # Remove whitespace, normalize case
    normalized = value.strip().upper()
    # Ensure LB- prefix if it looks like a number
    if re.match(r"^\d{4,10}$", normalized):
        normalized = f"LB-{normalized}"
    # Standardize LBXXXXX to LB-XXXXX
    match = re.match(r"^LB\s*-?\s*(\d+)$", normalized)
    if match:
        normalized = f"LB-{match.group(1)}"
    return normalized


def normalize_postal_code(value: str | None) -> str | None:
    if not value:
        return None
    # Extract digits only
    digits = "".join(filter(str.isdigit, str(value)))
    # Zero-pad to 5 digits if it's 4 digits (common in Germany)
    if len(digits) == 4:
        digits = "0" + digits
    if len(digits) == 5:
        return digits
    return None


def normalize_full_name(value: str | None) -> str | None:
    if not value:
        return None
    # Normalize whitespace
    normalized = " ".join(value.split())
    # Basic check for at least first + last name
    if len(normalized.split()) < 2:
        return None
    return normalized.title()


_SYSTEM_PROMPT = f"""You are an information extraction assistant for a German energy utility.

Extract the following from the customer email and return a JSON object matching the schema:

**Intents** — detect all that apply (use exact enum values):
- {Intent.METER_READING_SUBMISSION.value}: submitting or correcting a meter reading
- {Intent.PERSONAL_DATA_CHANGE.value}: changing name, address, or payment info
- {Intent.CONTRACT_ISSUES.value}: questions about contract termination, duration, or switching
- {Intent.PRODUCT_INFO_REQUEST.value}: questions about tariffs, pricing, or green energy
- {Intent.GENERAL_FEEDBACK.value}: compliments, complaints, or open comments

Only return one of the above intents when the message is clearly about energy-utility customer service.
If the message is mainly about unrelated topics (e.g., tax advice, legal advice, accounting, medical topics),
return an empty intents list.

**Entities** — extract if present, otherwise return null:
- contract_number: The primary identification number (usually starts with 'LB-'). Note that customers frequently refer to this as their 'meter number' or 'customer number'. If an identification number like 'LB-XXXXXX' is provided, prioritize extracting it as the contract_number.
- full_name: full name of the sender
- postal_code: 5-digit German postal code
- meter_number: Only extract if specifically mentioned as a separate entity from the main contract/identification number.
- meter_reading_kwh: numeric kWh reading value

Return only valid JSON. Do not add explanations.

EXAMPLES:
Input: "I'd like to submit my meter reading 1234. My contract is LB-123456."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-123456", "meter_reading_kwh": 1234}}

Input: "My meter number is LB-999 and the reading is 500."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-999", "meter_reading_kwh": 500}}"""


def extract(text: str) -> ExtractionResult:
    llm = get_llm()
    structured = llm.with_structured_output(ExtractionResult)
    try:
        result = structured.invoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=text),
            ]
        )
        return result  # type: ignore[return-value]
    except Exception:
        # Fallback to empty result if LLM fails completely
        return ExtractionResult()


def regex_fallback_extract(text: str, current_result: ExtractionResult) -> ExtractionResult:
    """Attempt to find missing auth entities using regex if LLM missed them."""
    if not current_result.contract_number:
        # Look for LB-XXXXX or just XXXXX near 'contract' or 'meter' keywords
        contract_match = re.search(r"(?:contract|customer|meter|vertrag|kundennummer|zähler)\s*(?:number|no|nr|num)?[:\s\-]*([A-Z]{0,2}-?\s*\d{4,10})", text, re.I)
        if contract_match:
            current_result.contract_number = normalize_contract_number(contract_match.group(1))

    if not current_result.postal_code:
        # Look for 5-digit codes that look like German PLZ
        postal_match = re.search(r"\b(\d{5})\b", text)
        if not postal_match:
            # Also try 4-digit codes
            postal_match = re.search(r"\b(\d{4})\b", text)
        if postal_match:
            current_result.postal_code = normalize_postal_code(postal_match.group(1))

    return current_result


def detect_intents(text: str) -> list[Intent]:
    return extract(text).intents


def extract_entities(text: str) -> dict[str, str | int]:
    result = extract(text)
    # Apply regex fallback for auth fields if missing
    result = regex_fallback_extract(text, result)
    
    # Apply normalization
    result.contract_number = normalize_contract_number(result.contract_number)
    result.postal_code = normalize_postal_code(result.postal_code)
    result.full_name = normalize_full_name(result.full_name)

    entities: dict[str, str | int] = {}
    if result.contract_number:
        entities["contract_number"] = result.contract_number
    if result.full_name:
        entities["full_name"] = result.full_name
    if result.postal_code:
        entities["postal_code"] = result.postal_code
    if result.meter_number:
        entities["meter_number"] = result.meter_number
    if result.meter_reading_kwh is not None:
        entities["meter_reading_kwh"] = result.meter_reading_kwh
    return entities

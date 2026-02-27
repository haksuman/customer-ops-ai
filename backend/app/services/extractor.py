import logging
import re
import time
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.llm import get_llm
from app.models.schemas import Intent

logger = logging.getLogger(__name__)


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
- contract_number: The primary identification number (usually starts with 'LB-'). Note that customers frequently refer to this as their 'meter number' or 'customer number'. If any identifier like 'LB-XXXXXX' or 'LB XXXXX' is provided anywhere in the email, treat it as the contract_number unless the text clearly says it is a different ID type.
- full_name: Full personal name of the customer (first + last name). Extract from self-introductions ("I am X", "My name is X", "My full name is X"), email signatures (name at the end), or direct identification. Extract ONLY the person's name — not job titles, company names, or contract numbers.
- postal_code: 5-digit German postal code (PLZ)
- meter_number: Only extract if specifically mentioned as a separate entity from the main contract/identification number.
- meter_reading_kwh: Numeric electricity meter reading value in kWh

Return only valid JSON. Do not add explanations.

EXAMPLES:
Input: "I'd like to submit my meter reading 1234. My contract is LB-123456."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-123456", "meter_reading_kwh": 1234}}

Input: "Dear Team, I'm Anna Schmidt (80331). My contract number is LB-5566778 and my meter reading is 4500 kWh."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-5566778", "full_name": "Anna Schmidt", "postal_code": "80331", "meter_reading_kwh": 4500}}

Input: "Hi! Can you tell me more about your dynamic tariff? How does it work and what are the benefits?"
Output: {{"intents": ["ProductInfoRequest"]}}

Input: "I'm interested in your green energy tariffs and pricing."
Output: {{"intents": ["ProductInfoRequest"]}}

Input: "My full name is Hans Mueller and postal code 10115."
Output: {{"intents": [], "full_name": "Hans Mueller", "postal_code": "10115"}}

Input: "My meter number is LB-999 and the reading is 500."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-999", "meter_reading_kwh": 500}}

Input: "Here is my latest reading for LB-9876543: 3000 kWh."
Output: {{"intents": ["MeterReadingSubmission"], "contract_number": "LB-9876543", "meter_reading_kwh": 3000}}"""


def extract(text: str) -> ExtractionResult:
    llm = get_llm()
    structured = llm.with_structured_output(ExtractionResult)
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            result = structured.invoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=text),
                ]
            )
            return result  # type: ignore[return-value]
        except Exception as exc:
            last_exc = exc
            logger.warning("LLM extraction attempt %d failed: %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1 s, then 2 s
    logger.error("LLM extraction failed after 3 attempts: %s", last_exc)
    return ExtractionResult()


def _infer_intents_fallback(result: ExtractionResult, text: str = "") -> ExtractionResult:
    """If the LLM returned no intents, infer from extracted entities first,
    then fall back to keyword matching against the raw text."""
    if result.intents:
        return result

    # 1. Entity-based inference — unambiguous: a kWh value means meter reading submission
    if result.meter_reading_kwh is not None:
        result.intents = [Intent.METER_READING_SUBMISSION]
        logger.info("Intent inferred from meter_reading_kwh entity: MeterReadingSubmission")
        return result

    # 2. Keyword-based inference — last resort when LLM and regex both miss
    if not text:
        return result
    text_lower = text.lower()

    if any(w in text_lower for w in ("meter reading", "kwh", "zählerstand", "ablesung", "stromzähler")):
        result.intents = [Intent.METER_READING_SUBMISSION]
        logger.info("Intent inferred via keyword: MeterReadingSubmission")
    elif any(
        w in text_lower
        for w in (
            "name change",
            "change my name",
            "new name",
            "namensänderung",
            "address change",
            "change my address",
            "adressänderung",
            "new address",
        )
    ):
        result.intents = [Intent.PERSONAL_DATA_CHANGE]
        logger.info("Intent inferred via keyword: PersonalDataChange")
    elif any(
        w in text_lower
        for w in (
            "tariff",
            "tariffs",
            "dynamic tariff",
            "fixed tariff",
            "variable tariff",
            "dynamic pricing",
            "price",
            "prices",
            "pricing",
            "plan",
            "plans",
            "green energy",
            "renewable",
            "eco tariff",
            "ökotarif",
            "how does it work",
            "benefits",
            "vorteile",
            "tarifoptionen",
        )
    ):
        result.intents = [Intent.PRODUCT_INFO_REQUEST]
        logger.info("Intent inferred via keyword: ProductInfoRequest")
    elif any(
        w in text_lower
        for w in (
            "cancel",
            "terminate",
            "end my contract",
            "kündigen",
            "kündigung",
            "vertrag beenden",
        )
    ):
        result.intents = [Intent.CONTRACT_ISSUES]
        logger.info("Intent inferred via keyword: ContractIssues")

    return result


def regex_fallback_extract(text: str, current_result: ExtractionResult) -> ExtractionResult:
    """Attempt to find missing entities using regex when the LLM missed them."""
    if not current_result.contract_number:
        # Stage A: look for explicit LB-style identifiers anywhere (LB-XXXXX, LB XXXXX, LBXXXXX).
        lb_match = re.search(r"\bLB\s*-?\s*\d{4,10}\b", text, re.I)
        if lb_match:
            current_result.contract_number = normalize_contract_number(lb_match.group(0))
        else:
            # Stage B: look for an ID near contract/customer/meter keywords, allowing simple connectors.
            contract_match = re.search(
                r"(?:contract|customer|meter|vertrag|kundennummer|zähler)\s*"
                r"(?:number|no\.?|nr\.?|num)?\s*(?:is|=)?\s*[:\-]?\s*"
                r"([A-Z]{0,2}\s*-?\s*\d{4,10})",
                text,
                re.I,
            )
            if contract_match:
                current_result.contract_number = normalize_contract_number(contract_match.group(1))

    if not current_result.full_name:
        # Match "I am X", "My (full) name is X", "Ich bin X", "Mein Name ist X"
        # then grab consecutive Capitalized words (stops at lowercase-starting words)
        _CAP_WORD = r"[A-ZÄÖÜ][a-zA-Zäöüß]+"
        _NAME_RUN = rf"{_CAP_WORD}(?:\s+{_CAP_WORD})+"  # at least 2 capitalized words
        name_prefixes = [
            r"my\s+(?:full\s+)?name\s+is\s+",
            r"i\s+am\s+",
            r"i'm\s+",
            r"ich\s+bin\s+",
            r"mein\s+(?:voller\s+)?name\s+ist\s+",
        ]
        for prefix in name_prefixes:
            prefix_m = re.search(prefix, text, re.I)
            if prefix_m:
                rest = text[prefix_m.end():]
                name_m = re.match(_NAME_RUN, rest)
                if name_m:
                    validated = normalize_full_name(name_m.group(0))
                    if validated:
                        current_result.full_name = validated
                        break

    if not current_result.postal_code:
        # Look for standalone 5-digit German PLZ
        postal_match = re.search(r"\b(\d{5})\b", text)
        if not postal_match:
            postal_match = re.search(r"\b(\d{4})\b", text)
        if postal_match:
            current_result.postal_code = normalize_postal_code(postal_match.group(1))

    if current_result.meter_reading_kwh is None:
        # Match patterns like "950 kWh", "950kWh", "1.234 kWh", "1,234kWh"
        kwh_match = re.search(r"(\d[\d.,]*)\s*kwh", text, re.I)
        if kwh_match:
            value_str = kwh_match.group(1).replace(" ", "").replace(",", ".")
            try:
                current_result.meter_reading_kwh = int(float(value_str))
            except ValueError:
                pass

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

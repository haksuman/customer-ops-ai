from __future__ import annotations

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
        None, description="Customer contract or customer number if present."
    )
    full_name: Optional[str] = Field(
        None, description="Full name of the customer if present."
    )
    postal_code: Optional[str] = Field(
        None, description="5-digit postal code if present."
    )
    meter_number: Optional[str] = Field(
        None, description="Meter number (e.g. LB-9876543) if present."
    )
    meter_reading_kwh: Optional[int] = Field(
        None, description="Electricity meter reading value in kWh if present."
    )


_SYSTEM_PROMPT = f"""You are an information extraction assistant for a German energy utility.

Extract the following from the customer email and return a JSON object matching the schema:

**Intents** — detect all that apply (use exact enum values):
- {Intent.METER_READING_SUBMISSION.value}: submitting or correcting a meter reading
- {Intent.PERSONAL_DATA_CHANGE.value}: changing name, address, or payment info
- {Intent.CONTRACT_ISSUES.value}: questions about contract termination, duration, or switching
- {Intent.PRODUCT_INFO_REQUEST.value}: questions about tariffs, pricing, or green energy
- {Intent.GENERAL_FEEDBACK.value}: compliments, complaints, or open comments

**Entities** — extract if present, otherwise return null:
- contract_number: contract or customer number
- full_name: full name of the sender
- postal_code: 5-digit German postal code
- meter_number: meter ID (e.g. LB-9876543)
- meter_reading_kwh: numeric kWh reading value

Return only valid JSON. Do not add explanations."""


def extract(text: str) -> ExtractionResult:
    llm = get_llm()
    structured = llm.with_structured_output(ExtractionResult)
    result = structured.invoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=text),
        ]
    )
    return result  # type: ignore[return-value]


def detect_intents(text: str) -> list[Intent]:
    return extract(text).intents


def extract_entities(text: str) -> dict[str, str | int]:
    result = extract(text)
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

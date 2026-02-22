from __future__ import annotations

import re

from app.models.schemas import Intent


INTENT_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.METER_READING_SUBMISSION: ("meter", "reading", "kwh"),
    Intent.PERSONAL_DATA_CHANGE: ("address", "name change", "payment", "bank"),
    Intent.CONTRACT_ISSUES: ("contract", "termination", "switch", "cancel"),
    Intent.PRODUCT_INFO_REQUEST: ("tariff", "dynamic", "price", "product"),
    Intent.GENERAL_FEEDBACK: ("feedback", "complaint", "thanks", "praise"),
}


def detect_intents(text: str) -> list[Intent]:
    lowered = text.lower()
    detected: list[Intent] = []
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            detected.append(intent)
    return detected


def extract_entities(text: str) -> dict[str, str | int]:
    entities: dict[str, str | int] = {}

    contract_match = re.search(r"\b(?:contract(?: number)?|customer number)\s*[:#-]?\s*([A-Za-z0-9-]{5,})\b", text, re.I)
    if contract_match:
        entities["contract_number"] = contract_match.group(1).strip()

    meter_number_match = re.search(r"\b(?:meter(?: number)?)\s*[:#-]?\s*([A-Za-z]{1,3}-\d{5,})\b", text, re.I)
    if meter_number_match:
        entities["meter_number"] = meter_number_match.group(1).strip()

    reading_match = re.search(r"\b(\d{2,5})\s*kwh\b", text, re.I)
    if reading_match:
        entities["meter_reading_kwh"] = int(reading_match.group(1))

    postal_match = re.search(r"\b(\d{5})\b", text)
    if postal_match:
        entities["postal_code"] = postal_match.group(1)

    explicit_name = re.search(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
    if explicit_name:
        entities["full_name"] = explicit_name.group(1).strip()

    # Best-effort signature extraction for demo purposes.
    signature_match = re.search(r"(?:thanks|best|regards|kind regards|sincerely)[,\s]*\n?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.I)
    if signature_match:
        entities["full_name"] = signature_match.group(1).strip()

    return entities

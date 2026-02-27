import pytest
from app.services.extractor import (
    normalize_contract_number,
    normalize_postal_code,
    normalize_full_name,
    regex_fallback_extract,
    _infer_intents_fallback,
    ExtractionResult,
)
from app.models.schemas import Intent

def test_normalization_contract_number():
    assert normalize_contract_number("LB-12345") == "LB-12345"
    assert normalize_contract_number("lb-12345") == "LB-12345"
    assert normalize_contract_number("  LB 12345  ") == "LB-12345"
    assert normalize_contract_number("LB12345") == "LB-12345"
    assert normalize_contract_number("12345") == "LB-12345"

def test_normalization_postal_code():
    assert normalize_postal_code("20097") == "20097"
    assert normalize_postal_code("PLZ: 20097") == "20097"
    assert normalize_postal_code("2009") == "02009"
    assert normalize_postal_code("abc 12345 def") == "12345"

def test_normalization_full_name():
    assert normalize_full_name("julia meyer") == "Julia Meyer"
    assert normalize_full_name("  julia   meyer  ") == "Julia Meyer"
    assert normalize_full_name("julia") is None

def test_regex_fallback():
    text = "My customer number is 9876543 and I live in 20097."
    res = ExtractionResult()
    res = regex_fallback_extract(text, res)
    assert res.contract_number == "LB-9876543"
    assert res.postal_code == "20097"

    text2 = "Zählernummer: LB-1122334"
    res2 = ExtractionResult()
    res2 = regex_fallback_extract(text2, res2)
    assert res2.contract_number == "LB-1122334"

    # Additional variants for contract number phrasing
    text3 = "My contract number is LB-5566778."
    res3 = ExtractionResult()
    res3 = regex_fallback_extract(text3, res3)
    assert res3.contract_number == "LB-5566778"

    text4 = "Contract no. LB5566778"
    res4 = ExtractionResult()
    res4 = regex_fallback_extract(text4, res4)
    assert res4.contract_number == "LB-5566778"

    text5 = "Customer number = LB 5566778"
    res5 = ExtractionResult()
    res5 = regex_fallback_extract(text5, res5)
    assert res5.contract_number == "LB-5566778"

    # Full sample-style message: name, PLZ, contract, meter reading
    text6 = (
        "Dear Team, I'm Anna Schmidt, living in 80331. "
        "My contract number is LB-5566778. I want to report my meter reading as 4500 kWh."
    )
    res6 = ExtractionResult()
    res6 = regex_fallback_extract(text6, res6)
    assert res6.contract_number == "LB-5566778"
    assert res6.postal_code == "80331"
    assert res6.meter_reading_kwh == 4500


def test_infer_intents_fallback_product_info():
    # LLM returns no intents, but text clearly asks about dynamic tariffs
    res = ExtractionResult()
    text = "Hi! Can you tell me more about your dynamic tariff? How does it work and what are the benefits?"
    res = _infer_intents_fallback(res, text)
    assert res.intents == [Intent.PRODUCT_INFO_REQUEST]

    # Another variant focusing on green tariffs and pricing
    res2 = ExtractionResult()
    text2 = "I'm interested in your green energy tariffs and pricing."
    res2 = _infer_intents_fallback(res2, text2)
    assert res2.intents == [Intent.PRODUCT_INFO_REQUEST]

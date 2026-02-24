import pytest
from app.services.extractor import (
    normalize_contract_number,
    normalize_postal_code,
    normalize_full_name,
    regex_fallback_extract,
    ExtractionResult
)

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

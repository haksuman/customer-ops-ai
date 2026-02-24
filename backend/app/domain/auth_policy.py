from __future__ import annotations

from app.models.schemas import AUTH_REQUIRED_INTENTS, Intent
from app.services.mock_repos import MockCustomerRepository


REQUIRED_AUTH_FIELDS = ("contract_number", "full_name", "postal_code")

AUTH_FIELD_LABELS: dict[str, str] = {
    "contract_number": "Contract Number",
    "full_name": "Full Name",
    "postal_code": "Postal Code",
}


def is_valid_contract_number(value: object) -> bool:
    if not value:
        return False
    import re
    return bool(re.match(r"^LB-\d{4,10}$", str(value).strip().upper()))


def is_valid_postal_code(value: object) -> bool:
    if not value:
        return False
    digits = "".join(filter(str.isdigit, str(value)))
    return len(digits) == 5


def is_valid_full_name(value: object) -> bool:
    if not value:
        return False
    name = str(value).strip()
    return len(name.split()) >= 2


def needs_auth(intents: list[Intent]) -> bool:
    return any(intent in AUTH_REQUIRED_INTENTS for intent in intents)


def get_missing_auth_fields(entities: dict[str, object]) -> list[str]:
    missing: list[str] = []
    validators = {
        "contract_number": is_valid_contract_number,
        "full_name": is_valid_full_name,
        "postal_code": is_valid_postal_code,
    }
    for field in REQUIRED_AUTH_FIELDS:
        value = entities.get(field)
        if not validators[field](value):
            missing.append(field)
    return missing


def get_missing_auth_labels(entities: dict[str, object]) -> list[str]:
    """Return human-readable labels for missing authentication fields."""
    return [AUTH_FIELD_LABELS[f] for f in get_missing_auth_fields(entities)]


def verify_auth(entities: dict[str, object], repo: MockCustomerRepository) -> bool:
    return repo.verify_customer(
        contract_number=str(entities["contract_number"]),
        full_name=str(entities["full_name"]),
        postal_code=str(entities["postal_code"]),
    )

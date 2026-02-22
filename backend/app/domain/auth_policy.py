from __future__ import annotations

from app.models.schemas import AUTH_REQUIRED_INTENTS, Intent
from app.services.mock_repos import MockCustomerRepository


REQUIRED_AUTH_FIELDS = ("contract_number", "full_name", "postal_code")


def needs_auth(intents: list[Intent]) -> bool:
    return any(intent in AUTH_REQUIRED_INTENTS for intent in intents)


def get_missing_auth_fields(entities: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_AUTH_FIELDS:
        value = entities.get(field)
        if not value:
            missing.append(field)
    return missing


def verify_auth(entities: dict[str, object], repo: MockCustomerRepository) -> bool:
    return repo.verify_customer(
        contract_number=str(entities["contract_number"]),
        full_name=str(entities["full_name"]),
        postal_code=str(entities["postal_code"]),
    )

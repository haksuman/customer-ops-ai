from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load(filename: str) -> list[dict]:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


class MockCustomerRepository:
    """
    Loads customer records from data/customers.json.
    Each document uses '_id' as the contract number key,
    mirroring MongoDB document structure for a future migration.
    """

    def __init__(self) -> None:
        records = _load("customers.json")
        self._customers: dict[str, dict] = {r["_id"]: r for r in records}

    def verify_customer(self, contract_number: str, full_name: str, postal_code: str) -> bool:
        customer = self._customers.get(contract_number)
        if not customer:
            return False
        return (
            customer["full_name"].lower() == full_name.lower()
            and customer["postal_code"] == postal_code
        )

    def previous_meter_reading(self, contract_number: str) -> int | None:
        customer = self._customers.get(contract_number)
        if not customer:
            return None
        return int(customer["last_meter_reading_kwh"])


class MockProductRepository:
    """
    Loads product/tariff records from data/products.json.
    Each document uses '_id' as the product slug key,
    mirroring MongoDB document structure for a future migration.
    """

    def __init__(self) -> None:
        records = _load("products.json")
        self._products: dict[str, dict] = {r["_id"]: r for r in records}

    def get_tariff_info(self, product_id: str = "dynamic-tariff") -> str:
        product = self._products.get(product_id)
        if not product:
            return "Product information is currently unavailable."
        return product["description"]

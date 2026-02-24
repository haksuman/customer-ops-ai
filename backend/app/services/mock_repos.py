from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load(filename: str) -> list[dict]:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _save(filename: str, data: list[dict]) -> None:
    with open(_DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class MockCustomerRepository:
    """
    Loads customer records from data/customers.json.
    Each document uses 'contract_number' as the primary key for lookups,
    while '_id' contains a GUID identifier.
    """

    def __init__(self) -> None:
        self._filename = "customers.json"
        records = _load(self._filename)
        self._customers: dict[str, dict] = {r["contract_number"]: r for r in records}
        self._by_id: dict[str, dict] = {r["_id"]: r for r in records}

    def verify_customer(self, contract_number: str, full_name: str, postal_code: str) -> bool:
        from app.services.extractor import normalize_contract_number, normalize_postal_code
        
        c_norm = normalize_contract_number(contract_number)
        if not c_norm:
            return False
            
        customer = self._customers.get(c_norm)
        if not customer:
            return False
            
        p_norm = normalize_postal_code(postal_code)
        if not p_norm or customer["postal_code"] != p_norm:
            return False
            
        # Tolerant name matching: simple check for inclusion
        # (Julia Meyer matches Julia Meyer, Julia M., etc.)
        expected_name = customer["full_name"].lower()
        provided_name = full_name.lower()
        
        # If the provided name is a subset or matches exactly after space normalization
        expected_parts = set(expected_name.split())
        provided_parts = set(provided_name.split())
        
        return len(provided_parts & expected_parts) >= 2 or provided_name in expected_name or expected_name in provided_name

    def previous_meter_reading(self, contract_number: str) -> int | None:
        from app.services.extractor import normalize_contract_number
        c_norm = normalize_contract_number(contract_number)
        if not c_norm:
            return None
        customer = self._customers.get(c_norm)
        if not customer:
            return None
        return int(customer["last_meter_reading_kwh"])

    def get_meter_number(self, contract_number: str) -> str | None:
        """
        In the current schema, the identification number (LB-xxxxxx) 
        is treated as the contract number.
        """
        from app.services.extractor import normalize_contract_number
        c_norm = normalize_contract_number(contract_number)
        if not c_norm:
            return None
        customer = self._customers.get(c_norm)
        if not customer:
            return None
        return customer.get("contract_number")

    def get_contract_by_id(self, guid: str) -> str | None:
        """Return the contract number for a given GUID, or None."""
        customer = self._by_id.get(guid)
        if not customer:
            return None
        return customer["contract_number"]

    def get_customer_by_contract(self, contract_number: str) -> dict | None:
        """Return full customer record by contract number."""
        from app.services.extractor import normalize_contract_number
        c_norm = normalize_contract_number(contract_number)
        return self._customers.get(c_norm)

    def update_customer_name(self, contract_number: str, new_name: str) -> bool:
        customer = self._customers.get(contract_number)
        if not customer:
            return False
        customer["full_name"] = new_name
        _save(self._filename, list(self._customers.values()))
        return True


class MockApprovalRepository:
    """
    Loads pending approvals from data/pending_approvals.json.
    """

    def __init__(self) -> None:
        self._filename = "pending_approvals.json"
        self._records = _load(self._filename)

    def list_pending(self) -> list[dict]:
        return self._records

    def add_pending(self, approval: dict) -> None:
        self._records.append(approval)
        _save(self._filename, self._records)

    def remove_pending(self, approval_id: str) -> bool:
        initial_len = len(self._records)
        self._records = [r for r in self._records if r["id"] != approval_id]
        if len(self._records) < initial_len:
            _save(self._filename, self._records)
            return True
        return False

    def get_by_id(self, approval_id: str) -> dict | None:
        for r in self._records:
            if r["id"] == approval_id:
                return r
        return None


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

    def list_tariffs(self) -> list[dict]:
        return list(self._products.values())

from __future__ import annotations


class MockCustomerRepository:
    def __init__(self) -> None:
        self._customers = {
            "LB-123456": {
                "full_name": "Julia Meyer",
                "postal_code": "20097",
                "last_meter_reading_kwh": 1200,
            }
        }

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
    def get_dynamic_tariff_info(self) -> str:
        return (
            "Our dynamic tariff reflects wholesale market prices, which can vary hourly. "
            "It benefits customers who can shift usage to lower-price periods and generally "
            "requires a compatible smart meter."
        )

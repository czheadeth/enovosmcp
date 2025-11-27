"""
Mock data for Enovos MCP Service
"""

MOCK_CUSTOMERS = {
    "C001": {
        "customer_id": "C001",
        "name": "Jean Dupont",
        "address": "12 Rue de la Gare, Luxembourg",
        "email": "jean.dupont@email.lu"
    },
    "C002": {
        "customer_id": "C002",
        "name": "Marie Schmidt",
        "address": "45 Avenue de la Liberté, Esch-sur-Alzette",
        "email": "marie.schmidt@email.lu"
    },
    "C003": {
        "customer_id": "C003",
        "name": "Pierre Martin",
        "address": "8 Boulevard Royal, Luxembourg",
        "email": "pierre.martin@email.lu"
    }
}

MOCK_CONSUMPTIONS = {
    "C001": {
        "customer_id": "C001",
        "electricity_kwh": 1500,
        "gas_kwh": 850,
        "period": "2024-11",
        "electricity_cost_eur": 285.50,
        "gas_cost_eur": 127.50,
        "total_cost_eur": 413.00
    },
    "C002": {
        "customer_id": "C002",
        "electricity_kwh": 2200,
        "gas_kwh": 1200,
        "period": "2024-11",
        "electricity_cost_eur": 418.00,
        "gas_cost_eur": 180.00,
        "total_cost_eur": 598.00
    },
    "C003": {
        "customer_id": "C003",
        "electricity_kwh": 980,
        "gas_kwh": 0,
        "period": "2024-11",
        "electricity_cost_eur": 186.20,
        "gas_cost_eur": 0,
        "total_cost_eur": 186.20
    }
}

MOCK_CONTRACTS = {
    "C001": {
        "customer_id": "C001",
        "contract_id": "CTR-2023-001",
        "contract_type": "residential",
        "tariff": "naturstroum",
        "start_date": "2023-01-15",
        "end_date": "2025-01-14",
        "electricity_included": True,
        "gas_included": True,
        "monthly_fee_eur": 12.50
    },
    "C002": {
        "customer_id": "C002",
        "contract_id": "CTR-2022-045",
        "contract_type": "residential",
        "tariff": "nova_naturstroum",
        "start_date": "2022-06-01",
        "end_date": "2024-05-31",
        "electricity_included": True,
        "gas_included": True,
        "monthly_fee_eur": 15.00
    },
    "C003": {
        "customer_id": "C003",
        "contract_id": "CTR-2024-012",
        "contract_type": "apartment",
        "tariff": "fix_1_year",
        "start_date": "2024-03-01",
        "end_date": "2025-02-28",
        "electricity_included": True,
        "gas_included": False,
        "monthly_fee_eur": 8.00
    }
}


def get_consumption_by_customer_id(customer_id: str) -> dict | None:
    """Get consumption data for a customer"""
    return MOCK_CONSUMPTIONS.get(customer_id)


def get_contract_by_customer_id(customer_id: str) -> dict | None:
    """Get contract data for a customer"""
    return MOCK_CONTRACTS.get(customer_id)


def get_customer_by_id(customer_id: str) -> dict | None:
    """Get customer info by ID"""
    return MOCK_CUSTOMERS.get(customer_id)


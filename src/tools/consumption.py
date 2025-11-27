"""
Tool for retrieving customer consumption data
"""
from src.data.mock_data import get_consumption_by_customer_id


def get_customer_consumption(customer_id: str) -> dict:
    """
    Récupère la consommation énergétique d'un client Enovos.
    
    Args:
        customer_id: L'identifiant unique du client (ex: C001, C002, C003)
    
    Returns:
        Les données de consommation incluant électricité, gaz et coûts
    """
    consumption = get_consumption_by_customer_id(customer_id)
    
    if consumption is None:
        return {
            "error": f"Client {customer_id} non trouvé",
            "customer_id": customer_id,
            "available_customers": ["C001", "C002", "C003"]
        }
    
    return consumption


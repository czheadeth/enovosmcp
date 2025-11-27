"""
Tool for retrieving customer contract data
"""
from src.data.mock_data import get_contract_by_customer_id


def get_customer_contract(customer_id: str) -> dict:
    """
    Récupère les détails du contrat d'un client Enovos.
    
    Args:
        customer_id: L'identifiant unique du client (ex: C001, C002, C003)
    
    Returns:
        Les détails du contrat incluant type, tarif, dates et services inclus
    """
    contract = get_contract_by_customer_id(customer_id)
    
    if contract is None:
        return {
            "error": f"Contrat pour le client {customer_id} non trouvé",
            "customer_id": customer_id,
            "available_customers": ["C001", "C002", "C003"]
        }
    
    return contract


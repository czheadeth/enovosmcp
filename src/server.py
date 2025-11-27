"""
Enovos MCP Server - Provides tools for customer consumption and contract data
"""
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from src.data.mock_data import (
    get_consumption_by_customer_id,
    get_contract_by_customer_id,
    get_customer_by_id,
    MOCK_CUSTOMERS
)

# Create the MCP server
mcp = FastMCP("enovos")


# Health check endpoint
async def health(request):
    return JSONResponse(
        {"status": "ok", "server": "enovos-mcp"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_consumption(customer_id: str = "C001") -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - sa consommation d'énergie, d'électricité ou de gaz
    - combien il a consommé
    - sa facture énergétique
    - ses kWh
    - le coût de son énergie
    
    Retourne la consommation électricité/gaz en kWh et les coûts en EUR.
    Par défaut utilise le client C001.
    
    Args:
        customer_id: Identifiant client (défaut: C001)
    """
    consumption = get_consumption_by_customer_id(customer_id)
    
    if consumption is None:
        return {
            "error": f"Client {customer_id} non trouvé",
            "customer_id": customer_id,
            "available_customers": list(MOCK_CUSTOMERS.keys())
        }
    
    return consumption


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_contract(customer_id: str = "C001") -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - son contrat d'énergie
    - son abonnement Enovos
    - son tarif électricité/gaz
    - les détails de son offre
    - la date de fin de contrat
    
    Retourne le type de contrat, tarif, dates et services inclus.
    Par défaut utilise le client C001.
    
    Args:
        customer_id: Identifiant client (défaut: C001)
    """
    contract = get_contract_by_customer_id(customer_id)
    
    if contract is None:
        return {
            "error": f"Contrat pour le client {customer_id} non trouvé",
            "customer_id": customer_id,
            "available_customers": list(MOCK_CUSTOMERS.keys())
        }
    
    return contract


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_info(customer_id: str = "C001") -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - ses informations personnelles
    - son profil client
    - son adresse
    - ses coordonnées
    
    Retourne nom, adresse et email du client.
    Par défaut utilise le client C001.
    
    Args:
        customer_id: Identifiant client (défaut: C001)
    """
    customer = get_customer_by_id(customer_id)
    
    if customer is None:
        return {
            "error": f"Client {customer_id} non trouvé",
            "customer_id": customer_id,
            "available_customers": list(MOCK_CUSTOMERS.keys())
        }
    
    return customer


if __name__ == "__main__":
    # Crée l'app Starlette avec le SSE MCP et un health check
    sse_app = mcp.sse_app()
    
    # Middleware CORS
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
    ]
    
    app = Starlette(
        routes=[
            Route("/", health),
            Route("/health", health),
            Mount("/mcp", app=sse_app),
        ],
        middleware=middleware,
    )
    
    print("Starting Enovos MCP Server on http://0.0.0.0:8000")
    print("Endpoints: / (health), /mcp/sse (MCP SSE)")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", proxy_headers=True, forwarded_allow_ips="*")


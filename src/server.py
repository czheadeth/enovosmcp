"""
Enovos MCP Server - Load Curve Consumption Data
Provides tools to query customer energy consumption from CSV files.
"""
import os
import csv
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Create the MCP server
mcp = FastMCP("enovos")

# Path to data files
DATA_DIR = Path(__file__).parent / "data"


def get_csv_path(customer_id: str) -> Path:
    """Get the CSV file path for a customer ID."""
    # Pad customer_id to 5 digits
    padded_id = customer_id.zfill(5)
    filename = f"LU_ENO_DELPHI_LU_virtual_ind_{padded_id}.csv"
    return DATA_DIR / filename


def load_csv_data(customer_id: str, date_from: str, date_to: str) -> list:
    """Load CSV data for a customer within a date range."""
    csv_path = get_csv_path(customer_id)
    
    if not csv_path.exists():
        return None
    
    # Parse dates
    try:
        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)  # Include end date
    except ValueError:
        return "invalid_date_format"
    
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            if start_date <= ts < end_date:
                data.append({
                    "timestamp": row['timestamp'],
                    "value_kwh": float(row['value'])
                })
    
    return data


# Health check endpoint
async def health(request):
    return JSONResponse(
        {"status": "ok", "server": "enovos-mcp", "version": "2.0"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_hourly(customer_id: str, date_from: str, date_to: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - consommation détaillée heure par heure
    - analyse d'une journée spécifique
    - pic de consommation
    - consommation pendant certaines heures
    - données fines sur une courte période
    
    Retourne la consommation moyenne par heure en kWh.
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Date de début au format YYYY-MM-DD (ex: "2023-01-15")
        date_to: Date de fin au format YYYY-MM-DD (ex: "2023-01-17")
    
    Returns:
        Liste de la consommation horaire en kWh.
        ATTENTION: Maximum 7 jours pour éviter trop de données.
    """
    # Validate date range (max 7 days)
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        if (end - start).days > 7:
            return {
                "error": "Plage de dates trop grande. Maximum 7 jours pour les données horaires.",
                "suggestion": "Utilisez get_consumption_daily pour des périodes plus longues."
            }
    except ValueError:
        return {"error": "Format de date invalide. Utilisez YYYY-MM-DD (ex: 2023-01-15)"}
    
    data = load_csv_data(customer_id, date_from, date_to)
    
    if data is None:
        return {
            "error": f"Client {customer_id} non trouvé.",
            "hint": "L'identifiant client doit être un nombre entre 00001 et 00088"
        }
    
    if data == "invalid_date_format":
        return {"error": "Format de date invalide. Utilisez YYYY-MM-DD (ex: 2023-01-15)"}
    
    if not data:
        return {
            "error": "Aucune donnée pour cette période.",
            "hint": "Les données disponibles vont de 2022-01-01 à 2023-12-31"
        }
    
    # Aggregate by hour (average of 4 x 15min values)
    hourly = defaultdict(list)
    for d in data:
        hour = d['timestamp'][:13] + ":00:00"  # YYYY-MM-DD HH:00:00
        hourly[hour].append(d['value_kwh'])
    
    hourly_data = [{"hour": k, "kwh": round(sum(v) / len(v), 3)} for k, v in sorted(hourly.items())]
    total_kwh = sum(d['kwh'] for d in hourly_data)
    
    return {
        "customer_id": customer_id,
        "period": {"from": date_from, "to": date_to},
        "granularity": "hourly",
        "total_kwh": round(total_kwh, 2),
        "hours_count": len(hourly_data),
        "consumption": hourly_data
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_daily(customer_id: str, date_from: str, date_to: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - consommation par jour
    - consommation d'une semaine
    - consommation d'un mois spécifique
    - comparaison entre jours
    - évolution quotidienne
    
    Retourne la consommation totale par jour en kWh.
    Calcul: moyenne horaire (4 x 15min) puis somme des 24 heures.
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Date de début au format YYYY-MM-DD (ex: "2023-01-01")
        date_to: Date de fin au format YYYY-MM-DD (ex: "2023-01-31")
    
    Returns:
        Liste de la consommation quotidienne en kWh.
        ATTENTION: Maximum 90 jours par requête.
    """
    # Validate date range (max 90 days)
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        if (end - start).days > 90:
            return {
                "error": "Plage de dates trop grande. Maximum 90 jours pour les données journalières.",
                "suggestion": "Utilisez get_consumption_monthly pour des périodes plus longues."
            }
    except ValueError:
        return {"error": "Format de date invalide. Utilisez YYYY-MM-DD (ex: 2023-01-15)"}
    
    data = load_csv_data(customer_id, date_from, date_to)
    
    if data is None:
        return {
            "error": f"Client {customer_id} non trouvé.",
            "hint": "L'identifiant client doit être un nombre entre 00001 et 00088"
        }
    
    if data == "invalid_date_format":
        return {"error": "Format de date invalide. Utilisez YYYY-MM-DD (ex: 2023-01-15)"}
    
    if not data:
        return {
            "error": "Aucune donnée pour cette période.",
            "hint": "Les données disponibles vont de 2022-01-01 à 2023-12-31"
        }
    
    # Step 1: Aggregate by hour (average of 4 x 15min values)
    hourly = defaultdict(list)
    for d in data:
        hour = d['timestamp'][:13]  # YYYY-MM-DD HH
        hourly[hour].append(d['value_kwh'])
    
    hourly_avg = {k: sum(v) / len(v) for k, v in hourly.items()}
    
    # Step 2: Sum hourly averages by day
    daily = defaultdict(float)
    for hour, avg_kwh in hourly_avg.items():
        date = hour[:10]  # YYYY-MM-DD
        daily[date] += avg_kwh
    
    daily_data = [{"date": k, "kwh": round(v, 2)} for k, v in sorted(daily.items())]
    total_kwh = sum(d['kwh'] for d in daily_data)
    avg_daily = total_kwh / len(daily_data) if daily_data else 0
    
    return {
        "customer_id": customer_id,
        "period": {"from": date_from, "to": date_to},
        "granularity": "daily",
        "total_kwh": round(total_kwh, 2),
        "average_daily_kwh": round(avg_daily, 2),
        "days_count": len(daily_data),
        "consumption": daily_data
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_monthly(customer_id: str, date_from: str, date_to: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - consommation mensuelle
    - consommation sur une année
    - tendance sur plusieurs mois
    - comparaison entre mois
    - évolution annuelle
    
    Retourne la consommation totale par mois en kWh.
    Calcul: moyenne horaire → somme journalière → somme mensuelle.
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Mois de début au format YYYY-MM (ex: "2023-01")
        date_to: Mois de fin au format YYYY-MM (ex: "2023-12")
    
    Returns:
        Liste de la consommation mensuelle en kWh.
    """
    # Parse monthly dates
    try:
        start = datetime.strptime(date_from + "-01", "%Y-%m-%d")
        end_month = datetime.strptime(date_to + "-01", "%Y-%m-%d")
        # Get last day of end month
        if end_month.month == 12:
            end = datetime(end_month.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(end_month.year, end_month.month + 1, 1) - timedelta(days=1)
    except ValueError:
        return {"error": "Format de date invalide. Utilisez YYYY-MM (ex: 2023-01)"}
    
    # Load data for the full period
    data = load_csv_data(customer_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    
    if data is None:
        return {
            "error": f"Client {customer_id} non trouvé.",
            "hint": "L'identifiant client doit être un nombre entre 00001 et 00088"
        }
    
    if data == "invalid_date_format":
        return {"error": "Format de date invalide. Utilisez YYYY-MM (ex: 2023-01)"}
    
    if not data:
        return {
            "error": "Aucune donnée pour cette période.",
            "hint": "Les données disponibles vont de 2022-01 à 2023-12"
        }
    
    # Step 1: Aggregate by hour (average of 4 x 15min values)
    hourly = defaultdict(list)
    for d in data:
        hour = d['timestamp'][:13]  # YYYY-MM-DD HH
        hourly[hour].append(d['value_kwh'])
    
    hourly_avg = {k: sum(v) / len(v) for k, v in hourly.items()}
    
    # Step 2: Sum hourly averages by day
    daily = defaultdict(float)
    for hour, avg_kwh in hourly_avg.items():
        date = hour[:10]  # YYYY-MM-DD
        daily[date] += avg_kwh
    
    # Step 3: Sum daily totals by month
    monthly = defaultdict(float)
    for date, daily_kwh in daily.items():
        month = date[:7]  # YYYY-MM
        monthly[month] += daily_kwh
    
    monthly_data = [{"month": k, "kwh": round(v, 2)} for k, v in sorted(monthly.items())]
    total_kwh = sum(d['kwh'] for d in monthly_data)
    avg_monthly = total_kwh / len(monthly_data) if monthly_data else 0
    
    return {
        "customer_id": customer_id,
        "period": {"from": date_from, "to": date_to},
        "granularity": "monthly",
        "total_kwh": round(total_kwh, 2),
        "average_monthly_kwh": round(avg_monthly, 2),
        "months_count": len(monthly_data),
        "consumption": monthly_data
    }


if __name__ == "__main__":
    # Create the Starlette app with SSE MCP and health check
    sse_app = mcp.sse_app()
    
    # CORS Middleware
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
    
    print("=" * 60)
    print("Enovos MCP Server v2.0 - Load Curve Data")
    print("=" * 60)
    print("Endpoints:")
    print("  - Health: http://0.0.0.0:8000/")
    print("  - MCP SSE: http://0.0.0.0:8000/mcp/sse")
    print("")
    print("Tools disponibles:")
    print("  - get_consumption_hourly(customer_id, date_from, date_to)")
    print("  - get_consumption_daily(customer_id, date_from, date_to)")
    print("  - get_consumption_monthly(customer_id, date_from, date_to)")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", proxy_headers=True, forwarded_allow_ips="*")

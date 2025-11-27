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
    
    Retourne la consommation moyenne par heure en kWh (24 valeurs par jour).
    
    IMPORTANT: Pour UNE SEULE journée, utilise la MEME date pour date_from et date_to.
    Exemple: journée du 15 mars → date_from="2023-03-15", date_to="2023-03-15"
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Date de début YYYY-MM-DD (incluse)
        date_to: Date de fin YYYY-MM-DD (incluse) - MEME date que date_from pour 1 jour
    
    Returns:
        Format compact: granularity, start, end, unit, total, values[]
        Maximum 7 jours.
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
        hour = d['timestamp'][:13]  # YYYY-MM-DD HH
        hourly[hour].append(d['value_kwh'])
    
    sorted_hours = sorted(hourly.keys())
    values = [round(sum(hourly[h]) / len(hourly[h]), 2) for h in sorted_hours]
    total_kwh = sum(values)
    
    return {
        "customer_id": customer_id,
        "granularity": "hourly",
        "start": sorted_hours[0] + ":00",
        "end": sorted_hours[-1] + ":00",
        "unit": "kwh",
        "total": round(total_kwh, 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_daily(customer_id: str, date_from: str, date_to: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - consommation par jour
    - consommation d'une semaine
    - consommation d'un mois spécifique
    - comparaison entre jours
    
    Retourne la consommation totale par jour en kWh.
    
    IMPORTANT: Les deux dates sont INCLUSIVES.
    Exemple semaine: date_from="2023-03-01", date_to="2023-03-07" → 7 jours
    Exemple mois: date_from="2023-03-01", date_to="2023-03-31" → 31 jours
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Date de début YYYY-MM-DD (incluse)
        date_to: Date de fin YYYY-MM-DD (incluse)
    
    Returns:
        Format compact: granularity, start, end, unit, total, values[]
        Maximum 90 jours.
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
    
    sorted_days = sorted(daily.keys())
    values = [round(daily[d], 2) for d in sorted_days]
    total_kwh = sum(values)
    
    return {
        "customer_id": customer_id,
        "granularity": "daily",
        "start": sorted_days[0],
        "end": sorted_days[-1],
        "unit": "kwh",
        "total": round(total_kwh, 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_monthly(customer_id: str, date_from: str, date_to: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - consommation mensuelle
    - consommation sur une année
    - tendance sur plusieurs mois
    - comparaison entre mois
    
    Retourne la consommation totale par mois en kWh.
    
    IMPORTANT: Les deux mois sont INCLUSIFS.
    Exemple année: date_from="2023-01", date_to="2023-12" → 12 mois
    Exemple trimestre: date_from="2023-01", date_to="2023-03" → 3 mois
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042", "00088")
        date_from: Mois de début YYYY-MM (inclus)
        date_to: Mois de fin YYYY-MM (inclus)
    
    Returns:
        Format compact: granularity, start, end, unit, total, values[]
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
    
    sorted_months = sorted(monthly.keys())
    values = [round(monthly[m], 2) for m in sorted_months]
    total_kwh = sum(values)
    
    return {
        "customer_id": customer_id,
        "granularity": "monthly",
        "start": sorted_months[0],
        "end": sorted_months[-1],
        "unit": "kwh",
        "total": round(total_kwh, 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_profile(customer_id: str) -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - son profil de consommation
    - son type de consommateur
    - analyse de son comportement énergétique
    - sa saisonnalité (hiver vs été)
    
    Retourne le profil horaire moyen (24h) et le ratio saisonnalité hiver/été.
    
    Interprétation du ratio_winter_summer:
    - > 2.0 = chauffage électrique probable (PAC)
    - < 0.7 = climatisation probable
    - ~1.0 = consommation stable toute l'année
    
    Args:
        customer_id: Identifiant client (ex: "00001", "00042")
    
    Returns:
        Format compact: customer_id, hourly_profile (24 valeurs), ratio_winter_summer
    """
    csv_path = get_csv_path(customer_id)
    
    if not csv_path.exists():
        return {
            "error": f"Client {customer_id} non trouvé.",
            "hint": "L'identifiant client doit être un nombre entre 00001 et 09831"
        }
    
    # Read CSV and compute profile
    hourly_values = defaultdict(list)  # {0: [...], 1: [...], ..., 23: [...]}
    monthly_values = defaultdict(list)  # {1: [...], ..., 12: [...]}
    total_kwh = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Use string slicing (fast) instead of datetime parsing
            hour = int(row['timestamp'][11:13])  # "2023-01-15 14:30:00" → 14
            month = int(row['timestamp'][5:7])   # "2023-01-15 14:30:00" → 1
            value = float(row['value'])
            
            hourly_values[hour].append(value)
            monthly_values[month].append(value)
            total_kwh += value
    
    # Compute hourly profile (24 values)
    hourly_profile = [
        round(sum(hourly_values[h]) / len(hourly_values[h]), 2) if hourly_values[h] else 0
        for h in range(24)
    ]
    
    # Compute seasonality ratio
    winter_months = [11, 12, 1, 2]
    summer_months = [6, 7, 8]
    
    winter_vals = [v for m in winter_months for v in monthly_values.get(m, [])]
    summer_vals = [v for m in summer_months for v in monthly_values.get(m, [])]
    
    winter_avg = sum(winter_vals) / len(winter_vals) if winter_vals else 1
    summer_avg = sum(summer_vals) / len(summer_vals) if summer_vals else 1
    ratio = round(winter_avg / summer_avg, 2) if summer_avg > 0 else 1.0
    
    return {
        "customer_id": customer_id.zfill(5),
        "hourly_profile": hourly_profile,
        "ratio_winter_summer": ratio,
        "total_kwh": round(total_kwh, 0)
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
    print("Enovos MCP Server v3.0 - Load Curve Data + Profiles")
    print("=" * 60)
    print("Endpoints:")
    print("  - Health: http://0.0.0.0:8000/")
    print("  - MCP SSE: http://0.0.0.0:8000/mcp/sse")
    print("")
    print("Tools consommation:")
    print("  - get_consumption_hourly(customer_id, date_from, date_to)")
    print("  - get_consumption_daily(customer_id, date_from, date_to)")
    print("  - get_consumption_monthly(customer_id, date_from, date_to)")
    print("")
    print("Tools profils:")
    print("  - get_customer_profile(customer_id) → profil 24h + saisonnalité")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", proxy_headers=True, forwarded_allow_ips="*")

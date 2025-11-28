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
    USE THIS TOOL when user asks for:
    - Hourly consumption details
    - Specific day analysis
    - Peak consumption times
    - Consumption during specific hours
    
    Returns average consumption per hour in kWh (24 values per day).
    
    IMPORTANT: For a SINGLE day, use the SAME date for date_from and date_to.
    Example: March 15th → date_from="2023-03-15", date_to="2023-03-15"
    
    Args:
        customer_id: Customer ID (e.g., "00001", "00042", "00088")
        date_from: Start date YYYY-MM-DD (inclusive)
        date_to: End date YYYY-MM-DD (inclusive) - SAME as date_from for 1 day
    
    Returns:
        Compact format: granularity, start, end, unit, total, values[]
        Maximum 7 days.
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
    USE THIS TOOL when user asks for:
    - Daily consumption
    - Weekly consumption
    - Monthly consumption for a specific month
    - Day-to-day comparison
    
    Returns total consumption per day in kWh.
    
    IMPORTANT: Both dates are INCLUSIVE.
    Example week: date_from="2023-03-01", date_to="2023-03-07" → 7 days
    Example month: date_from="2023-03-01", date_to="2023-03-31" → 31 days
    
    Args:
        customer_id: Customer ID (e.g., "00001", "00042", "00088")
        date_from: Start date YYYY-MM-DD (inclusive)
        date_to: End date YYYY-MM-DD (inclusive)
    
    Returns:
        Compact format: granularity, start, end, unit, total, values[]
        Maximum 90 days.
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
    USE THIS TOOL when user asks for:
    - Monthly consumption
    - Yearly consumption
    - Multi-month trends
    - Month-to-month comparison
    
    Returns total consumption per month in kWh.
    
    IMPORTANT: Both months are INCLUSIVE.
    Example year: date_from="2023-01", date_to="2023-12" → 12 months
    Example quarter: date_from="2023-01", date_to="2023-03" → 3 months
    
    Args:
        customer_id: Customer ID (e.g., "00001", "00042", "00088")
        date_from: Start month YYYY-MM (inclusive)
        date_to: End month YYYY-MM (inclusive)
    
    Returns:
        Compact format: granularity, start, end, unit, total, values[]
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
    USE THIS TOOL when user asks for:
    - Their consumption profile
    - Their consumer type
    - Energy behavior analysis
    - Seasonality (winter vs summer)
    
    ⚠️ ALSO USE THIS as FIRST STEP when user asks about:
    - Saving money / économiser
    - Reducing their bill / réduire la facture
    - Best offer for them / meilleure offre
    - Contract optimization
    - Whether their contract is suitable
    
    → After getting profile, you MUST also call:
      get_customer_contract() then get_enovos_offers() to give a complete answer!
    
    HOW TO INTERPRET the results:
    - hourly_profile: 24 values (index 0 = midnight, index 23 = 11pm)
      - High values at night (19-5h) = likely EV charging → Naturstrom Drive
      - High values during day (9-17h) = likely office → Energy Sharing
      - Peaks at 7-9h and 18-21h = typical residential → PV + Electris
    
    - ratio_winter_summer:
      - > 2.0 = electric heating (heat pump) → Naturstrom Fix
      - < 0.7 = air conditioning
      - ~1.0-1.3 = stable consumption (EV, standard residential)
    
    Args:
        customer_id: Customer ID (e.g., "00001", "00042")
    
    Returns:
        customer_id, hourly_profile (24 values), ratio_winter_summer, total_kwh
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


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_contract(customer_id: str) -> dict:
    """
    USE THIS TOOL to get the customer's CURRENT contract.
    
    ⚠️ IMPORTANT WORKFLOW - When user asks about contract suitability:
    
    You MUST follow these steps in order:
    
    STEP 1: Call get_customer_profile(customer_id) FIRST
            → Look at hourly_profile: which hours have highest values?
            → Look at ratio_winter_summer: above 2.0? below 0.7? around 1.0?
    
    STEP 2: Call get_customer_contract(customer_id)
            → Get their current contract name
    
    STEP 3: Call get_enovos_offers()
            → Get all available offers with "ideal_for" field
    
    STEP 4: MATCH profile to best offer:
            - If hourly_profile peaks at night (hours 19-5 are highest) AND ratio ~1.0-1.3
              → Best offer: "Naturstrom Drive" (EV owner)
            - If hourly_profile peaks during day (hours 9-17 are highest)
              → Best offer: "Energy Sharing" (office/business)
            - If ratio_winter_summer > 2.0
              → Best offer: "Naturstrom Fix" (heat pump)
            - Otherwise (standard residential)
              → Best offer: "PV + Electris"
    
    STEP 5: COMPARE current contract vs best offer
            → If different: recommend switching with estimated savings
            → If same: confirm they have the right contract
    
    Args:
        customer_id: Customer ID (e.g., "00001", "00042")
    
    Returns:
        Current contract details: name, price, start_date
    """
    # Check if customer exists
    csv_path = get_csv_path(customer_id)
    if not csv_path.exists():
        return {
            "error": f"Customer {customer_id} not found.",
            "hint": "Customer ID should be a number between 00001 and 09831"
        }
    
    # Default contract for all customers (demo)
    return {
        "customer_id": customer_id.zfill(5),
        "current_contract": "Naturstrom Fix",
        "price_kwh_eur": 0.25,
        "contract_start": "2022-01-01",
        "description": "Fixed price green energy contract"
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_enovos_offers() -> dict:
    """
    USE THIS TOOL to get ALL available Enovos energy offers.
    
    ⚠️ ALWAYS call get_customer_profile() BEFORE this tool to know the customer's pattern.
    
    HOW TO MATCH offers to customer profile:
    
    Look at the customer's hourly_profile (24 values, index 0=midnight, 23=11pm):
    
    1. NIGHT PEAK (values at hours 19,20,21,22,23,0,1,2,3,4,5 are HIGH):
       → Recommend: "Naturstrom Drive" - saves 40% on night consumption
       → Typical for: EV owners who charge at night
    
    2. DAY PEAK (values at hours 9,10,11,12,13,14,15,16,17 are HIGH):
       → Recommend: "Energy Sharing" - optimized for business hours
       → Typical for: Offices, shops, remote workers
    
    3. HIGH SEASONALITY (ratio_winter_summer > 2.0):
       → Recommend: "Naturstrom Fix" - stable price for high winter usage
       → Typical for: Heat pumps, electric heating
    
    4. STANDARD PATTERN (morning + evening peaks, ratio ~1.3):
       → Recommend: "PV + Electris" - solar self-consumption
       → Typical for: Families, standard residential
    
    Returns:
        List of all Enovos offers with prices, ideal_for field, and benefits
    """
    return {
        "offers": [
            {
                "name": "Naturstrom Fix",
                "description": "Fixed price, 100% green energy from renewable sources",
                "price_kwh_eur": 0.25,
                "price_type": "fixed",
                "ideal_for": "Stable consumption, heat pumps (high winter usage), customers wanting price security",
                "benefits": ["Price stability", "100% renewable", "No surprises"]
            },
            {
                "name": "Naturstrom Drive",
                "description": "Optimized for electric vehicle owners with advantageous night rates",
                "price_kwh_night_eur": 0.15,
                "price_kwh_day_eur": 0.28,
                "night_hours": "22:00-06:00",
                "price_type": "dual_tariff",
                "ideal_for": "EV owners charging at night, high night consumption (22h-6h peak)",
                "benefits": ["40% cheaper at night", "Perfect for EV charging", "100% renewable"]
            },
            {
                "name": "Energy Sharing",
                "description": "Share energy within your community or building",
                "price_kwh_eur": 0.22,
                "price_type": "community",
                "ideal_for": "Offices, businesses, buildings with daytime consumption (9h-17h peak)",
                "benefits": ["Lower rates", "Community benefits", "Daytime optimization"]
            },
            {
                "name": "PV + Electris",
                "description": "Solar self-consumption with grid backup, sell surplus",
                "price_kwh_eur": 0.20,
                "price_type": "prosumer",
                "ideal_for": "Residential homes with roof potential, standard consumption pattern",
                "benefits": ["Produce your own energy", "Sell surplus", "Reduce bills up to 70%"]
            }
        ]
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
    print("Enovos MCP Server v4.0 - Full Customer Intelligence")
    print("=" * 60)
    print("Endpoints:")
    print("  - Health: http://0.0.0.0:8000/")
    print("  - MCP SSE: http://0.0.0.0:8000/mcp/sse")
    print("")
    print("Consumption tools:")
    print("  - get_consumption_hourly(customer_id, date_from, date_to)")
    print("  - get_consumption_daily(customer_id, date_from, date_to)")
    print("  - get_consumption_monthly(customer_id, date_from, date_to)")
    print("")
    print("Profile tools:")
    print("  - get_customer_profile(customer_id)")
    print("")
    print("Contract tools:")
    print("  - get_customer_contract(customer_id)")
    print("  - get_enovos_offers()")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", proxy_headers=True, forwarded_allow_ips="*")

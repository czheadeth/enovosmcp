"""
Enovos MCP Server - Customer Energy Data
"""
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

mcp = FastMCP("enovos")
DATA_DIR = Path(__file__).parent / "data"


def get_csv_path(customer_id: str) -> Path:
    padded_id = customer_id.zfill(5)
    return DATA_DIR / f"LU_ENO_DELPHI_LU_virtual_ind_{padded_id}.csv"


def load_csv_data(customer_id: str, date_from: str, date_to: str) -> list:
    csv_path = get_csv_path(customer_id)
    if not csv_path.exists():
        return None
    
    try:
        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        return "invalid_date"
    
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            if start_date <= ts < end_date:
                data.append({"timestamp": row['timestamp'], "value_kwh": float(row['value'])})
    return data


async def health(request):
    return JSONResponse({"status": "ok", "server": "enovos-mcp"})


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_hourly(customer_id: str, date_from: str, date_to: str) -> dict:
    """Get hourly consumption for a customer. Max 7 days.
    
    Args:
        customer_id: Required. The customer's unique identifier
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD (same as date_from for 1 day)
    """
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        if (end - start).days > 7:
            return {"error": "Max 7 days"}
    except ValueError:
        return {"error": "Invalid date format"}
    
    data = load_csv_data(customer_id, date_from, date_to)
    if data is None:
        return {"error": f"Customer {customer_id} not found"}
    if data == "invalid_date":
        return {"error": "Invalid date format"}
    if not data:
        return {"error": "No data for this period"}
    
    hourly = defaultdict(list)
    for d in data:
        hour = d['timestamp'][:13]
        hourly[hour].append(d['value_kwh'])
    
    sorted_hours = sorted(hourly.keys())
    values = [round(sum(hourly[h]) / len(hourly[h]), 2) for h in sorted_hours]
    
    return {
        "customer_id": customer_id,
        "granularity": "hourly",
        "start": sorted_hours[0],
        "end": sorted_hours[-1],
        "unit": "kwh",
        "total": round(sum(values), 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_daily(customer_id: str, date_from: str, date_to: str) -> dict:
    """Get daily consumption for a customer. Max 90 days.
    
    Args:
        customer_id: Required. The customer's unique identifier
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD
    """
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        if (end - start).days > 90:
            return {"error": "Max 90 days"}
    except ValueError:
        return {"error": "Invalid date format"}
    
    data = load_csv_data(customer_id, date_from, date_to)
    if data is None:
        return {"error": f"Customer {customer_id} not found"}
    if data == "invalid_date":
        return {"error": "Invalid date format"}
    if not data:
        return {"error": "No data for this period"}
    
    hourly = defaultdict(list)
    for d in data:
        hourly[d['timestamp'][:13]].append(d['value_kwh'])
    
    daily = defaultdict(float)
    for hour, vals in hourly.items():
        daily[hour[:10]] += sum(vals) / len(vals)
    
    sorted_days = sorted(daily.keys())
    values = [round(daily[d], 2) for d in sorted_days]
    
    return {
        "customer_id": customer_id,
        "granularity": "daily",
        "start": sorted_days[0],
        "end": sorted_days[-1],
        "unit": "kwh",
        "total": round(sum(values), 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_consumption_monthly(customer_id: str, date_from: str, date_to: str) -> dict:
    """Get monthly consumption for a customer.
    
    Args:
        customer_id: Required. The customer's unique identifier
        date_from: Start month YYYY-MM
        date_to: End month YYYY-MM
    """
    try:
        start = datetime.strptime(date_from + "-01", "%Y-%m-%d")
        end_month = datetime.strptime(date_to + "-01", "%Y-%m-%d")
        if end_month.month == 12:
            end = datetime(end_month.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(end_month.year, end_month.month + 1, 1) - timedelta(days=1)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM"}
    
    data = load_csv_data(customer_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if data is None:
        return {"error": f"Customer {customer_id} not found"}
    if data == "invalid_date":
        return {"error": "Invalid date format"}
    if not data:
        return {"error": "No data for this period"}
    
    hourly = defaultdict(list)
    for d in data:
        hourly[d['timestamp'][:13]].append(d['value_kwh'])
    
    daily = defaultdict(float)
    for hour, vals in hourly.items():
        daily[hour[:10]] += sum(vals) / len(vals)
    
    monthly = defaultdict(float)
    for date, kwh in daily.items():
        monthly[date[:7]] += kwh
    
    sorted_months = sorted(monthly.keys())
    values = [round(monthly[m], 2) for m in sorted_months]
    
    return {
        "customer_id": customer_id,
        "granularity": "monthly",
        "start": sorted_months[0],
        "end": sorted_months[-1],
        "unit": "kwh",
        "total": round(sum(values), 2),
        "values": values
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_profile(customer_id: str) -> dict:
    """Get customer consumption profile with automatic classification.
    
    Args:
        customer_id: Required. The customer's unique identifier
    """
    csv_path = get_csv_path(customer_id)
    if not csv_path.exists():
        return {"error": f"Customer {customer_id} not found"}
    
    hourly_values = defaultdict(list)
    monthly_values = defaultdict(list)
    total_kwh = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hour = int(row['timestamp'][11:13])
            month = int(row['timestamp'][5:7])
            value = float(row['value'])
            hourly_values[hour].append(value)
            monthly_values[month].append(value)
            total_kwh += value
    
    hourly_profile = [
        round(sum(hourly_values[h]) / len(hourly_values[h]), 2) if hourly_values[h] else 0
        for h in range(24)
    ]
    
    winter_vals = [v for m in [11, 12, 1, 2] for v in monthly_values.get(m, [])]
    summer_vals = [v for m in [6, 7, 8] for v in monthly_values.get(m, [])]
    
    winter_avg = sum(winter_vals) / len(winter_vals) if winter_vals else 1
    summer_avg = sum(summer_vals) / len(summer_vals) if summer_vals else 1
    ratio = round(winter_avg / summer_avg, 2) if summer_avg > 0 else 1.0
    
    # Classify profile
    night_hours = [19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5]
    day_hours = [9, 10, 11, 12, 13, 14, 15, 16, 17]
    
    night_avg = sum(hourly_profile[h] for h in night_hours) / len(night_hours)
    day_avg = sum(hourly_profile[h] for h in day_hours) / len(day_hours)
    
    if ratio > 2.0:
        profile_type = "heat_pump"
    elif night_avg > day_avg * 1.5:
        profile_type = "ev"
    elif day_avg > night_avg * 1.5:
        profile_type = "office"
    else:
        profile_type = "residential"
    
    return {
        "customer_id": customer_id.zfill(5),
        "profile_type": profile_type,
        "hourly_profile": hourly_profile,
        "ratio_winter_summer": ratio,
        "total_kwh": round(total_kwh, 0)
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_contract(customer_id: str) -> dict:
    """Get customer's current energy contract.
    
    Args:
        customer_id: Required. The customer's unique identifier
    """
    csv_path = get_csv_path(customer_id)
    if not csv_path.exists():
        return {"error": f"Customer {customer_id} not found"}
    
    return {
        "customer_id": customer_id.zfill(5),
        "contract": "Naturstrom Fix",
        "price_kwh": 0.25,
        "start_date": "2022-01-01"
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_enovos_offers() -> dict:
    """Get all available Enovos energy offers.
    
    Use this to see all offers and compare with customer's current contract.
    Each offer has an 'ideal_for' field matching profile types from get_customer_profile.
    """
    return {
        "offers": [
            {
                "name": "Naturstrom Fix",
                "price_eur_kwh": 0.25,
                "type": "fixed",
                "ideal_for": "heat_pump",
                "description": "Fixed price, 100% renewable, price security"
            },
            {
                "name": "Naturstrom Drive",
                "price_night_eur_kwh": 0.15,
                "price_day_eur_kwh": 0.28,
                "night_hours": "22:00-06:00",
                "type": "dual",
                "ideal_for": "ev",
                "description": "Optimized for EV charging, -40% at night"
            },
            {
                "name": "Energy Sharing",
                "base_price_eur_kwh": 0.25,
                "network_fee_savings": "up to 10%",
                "type": "p2p",
                "ideal_for": "office",
                "description": "Share with a local partner, save up to 10% on network fees",
                "how_it_works": "Find partner nearby → share production → both reduce grid fees"
            },
            {
                "name": "Nova Naturstroum",
                "price_eur_kwh": 0.23,
                "type": "green",
                "ideal_for": "residential",
                "description": "100% local renewable energy"
            }
        ]
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_advice(customer_id: str) -> dict:
    """Get advice workflow for a customer asking how to save money.
    
    CALL THIS FIRST when customer asks: how to save, reduce bill, optimize, best offer, etc.
    
    Args:
        customer_id: Required. The customer's unique identifier
    """
    return {
        "workflow": [
            "1. Call get_customer_profile(customer_id) to get profile_type",
            "2. Call get_customer_contract(customer_id) to get current contract",
            "3. Call get_enovos_offers() to see all offers with ideal_for field",
            "4. Compare: find offer where ideal_for == profile_type",
            "5. If current contract != recommended offer → suggest switching",
            "6. If current contract == recommended offer → give generic tips"
        ],
        "generic_tips": [
            "Shift consumption to off-peak hours",
            "Install smart thermostat",
            "Check for energy-efficient appliances",
            "Consider solar panels"
        ],
        "customer_id": customer_id
    }


@mcp.tool(annotations={"readOnlyHint": True})
def find_sharing_partners(customer_id: str) -> dict:
    """Find residential solar producers available for Energy Sharing.
    
    For office/business customers who consume during daytime:
    Residential customers with solar panels produce during the day.
    These producers have agreed to join the Energy Sharing program.
    
    Both parties save up to 10% on network fees!
    
    Args:
        customer_id: Required. The customer's unique identifier
    """
    return {
        "customer_id": customer_id,
        "your_profile": "High daytime consumption (office)",
        "matching_producers": [
            {
                "id": "PROD-2847",
                "type": "Residential with solar (6 kWp)",
                "district": "Kirchberg",
                "available_kwh_month": 450,
                "potential_savings_percent": 9,
                "status": "Available"
            },
            {
                "id": "PROD-1923",
                "type": "Residential with solar (4 kWp)",
                "district": "Limpertsberg",
                "available_kwh_month": 320,
                "potential_savings_percent": 7,
                "status": "Available"
            },
            {
                "id": "PROD-5561",
                "type": "Residential with solar (8 kWp)",
                "district": "Gasperich",
                "available_kwh_month": 600,
                "potential_savings_percent": 10,
                "status": "Available"
            }
        ],
        "how_it_works": "These residents produce solar energy during the day when you consume. Perfect match!",
        "next_step": "Use signal_interest to notify Enovos"
    }


@mcp.tool(annotations={"readOnlyHint": True})
def signal_interest(customer_id: str, producer_id: str) -> dict:
    """Signal interest in Energy Sharing partnership to Enovos.
    
    After finding a matching producer with find_sharing_partners,
    the customer can signal their interest. Enovos will then contact
    both parties to set up the partnership.
    
    Args:
        customer_id: Required. The customer's unique identifier
        producer_id: Required. The producer ID from find_sharing_partners (e.g. "PROD-2847")
    """
    return {
        "status": "success",
        "message": "Your interest has been registered!",
        "customer_id": customer_id,
        "producer_id": producer_id,
        "next_steps": [
            "Enovos will verify eligibility",
            "Both parties will be contacted within 48h",
            "Contract adjustment and partnership activation"
        ],
        "estimated_savings": "Up to 10% on network fees",
        "reference": f"ES-{customer_id}-{producer_id}"
    }


if __name__ == "__main__":
    sse_app = mcp.sse_app()
    
    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], 
                   allow_headers=["*"], allow_credentials=True)
    ]
    
    app = Starlette(
        routes=[
            Route("/", health),
            Route("/health", health),
            Mount("/mcp", app=sse_app),
        ],
        middleware=middleware,
    )
    
    print("=" * 50)
    print("Enovos MCP Server")
    print("=" * 50)
    print("Tools:")
    print("  - get_consumption_hourly")
    print("  - get_consumption_daily")
    print("  - get_consumption_monthly")
    print("  - get_customer_profile")
    print("  - get_customer_contract")
    print("  - get_enovos_offers")
    print("  - get_advice")
    print("  - find_sharing_partners")
    print("  - signal_interest")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

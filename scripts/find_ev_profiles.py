"""
Script pour trouver des profils EV (pic nocturne)
Usage: python scripts/find_ev_profiles.py
"""
import csv
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "src" / "data"


def analyze_customer(csv_path):
    """Analyse un client et retourne son profil."""
    hourly_values = defaultdict(list)
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hour = int(row['timestamp'][11:13])
            value = float(row['value'])
            hourly_values[hour].append(value)
    
    # Profil 24h
    profile = [sum(hourly_values[h]) / len(hourly_values[h]) if hourly_values[h] else 0 for h in range(24)]
    
    # Calcul ratio nuit/jour
    night_hours = [22, 23, 0, 1, 2, 3, 4, 5]  # 22h-6h
    day_hours = [10, 11, 12, 13, 14, 15, 16, 17]  # 10h-18h
    
    night_avg = sum(profile[h] for h in night_hours) / len(night_hours)
    day_avg = sum(profile[h] for h in day_hours) / len(day_hours)
    
    night_ratio = night_avg / day_avg if day_avg > 0 else 1
    
    # Heure du pic
    peak_hour = profile.index(max(profile))
    
    return {
        'profile': profile,
        'night_ratio': night_ratio,
        'peak_hour': peak_hour,
        'night_avg': night_avg,
        'day_avg': day_avg
    }


def main():
    print("🔍 Recherche de profils EV (pic nocturne)...\n")
    
    # Scanner les 100 premiers clients
    csv_files = sorted(DATA_DIR.glob("*.csv"))[:100]
    
    results = []
    
    for i, csv_file in enumerate(csv_files):
        customer_id = csv_file.stem.split("_")[-1]
        
        if (i + 1) % 20 == 0:
            print(f"   Analysé {i + 1}/{len(csv_files)} clients...")
        
        try:
            analysis = analyze_customer(csv_file)
            results.append({
                'customer_id': customer_id,
                **analysis
            })
        except Exception as e:
            print(f"   ⚠️ Erreur sur {customer_id}: {e}")
    
    # Trier par ratio nocturne (plus haut = plus EV)
    results.sort(key=lambda x: x['night_ratio'], reverse=True)
    
    print("\n" + "=" * 60)
    print("🔌 TOP 10 PROFILS EV (pic nocturne)")
    print("=" * 60)
    print(f"{'Client':<10} {'Ratio Nuit/Jour':<15} {'Pic à':<8} {'Nuit avg':<10} {'Jour avg':<10}")
    print("-" * 60)
    
    for r in results[:10]:
        print(f"{r['customer_id']:<10} {r['night_ratio']:<15.2f} {r['peak_hour']:02d}h      {r['night_avg']:<10.1f} {r['day_avg']:<10.1f}")
    
    print("\n" + "=" * 60)
    print("🏠 TOP 5 PROFILS RÉSIDENTIELS CLASSIQUES (pic journée)")
    print("=" * 60)
    
    for r in results[-5:]:
        print(f"{r['customer_id']:<10} {r['night_ratio']:<15.2f} {r['peak_hour']:02d}h      {r['night_avg']:<10.1f} {r['day_avg']:<10.1f}")
    
    # Afficher le profil du meilleur candidat EV
    best_ev = results[0]
    print("\n" + "=" * 60)
    print(f"📊 PROFIL DÉTAILLÉ DU MEILLEUR CANDIDAT EV: {best_ev['customer_id']}")
    print("=" * 60)
    print("Heure │ Consommation")
    print("──────┼─────────────")
    for h, val in enumerate(best_ev['profile']):
        bar = "█" * int(val / max(best_ev['profile']) * 30)
        marker = " ← PIC" if h == best_ev['peak_hour'] else ""
        night = " (nuit)" if h in [22, 23, 0, 1, 2, 3, 4, 5] else ""
        print(f"  {h:02d}h │ {val:6.1f} {bar}{marker}{night}")


if __name__ == "__main__":
    main()


"""
Génère un profil EV synthétique pour le client 00000
"""
import csv
import random
from datetime import datetime, timedelta

OUTPUT_FILE = "src/data/LU_ENO_DELPHI_LU_virtual_ind_00000.csv"

# Profil horaire EV MARQUÉ
# Rentre du boulot 18h-19h, branche la voiture, charge jusqu'à ~3h
HOURLY_PROFILE = {
    0: 9.0,   # Charge en cours
    1: 9.0,   # Charge en cours
    2: 8.5,   # Charge en cours
    3: 4.0,   # Fin de charge
    4: 1.2,   # Base
    5: 1.2,   # Base
    6: 1.5,   # Réveil
    7: 2.0,   # Petit-déj, prépa
    8: 1.0,   # Parti au travail
    9: 0.8,   # Personne - base
    10: 0.8,
    11: 0.8,
    12: 0.8,
    13: 0.8,
    14: 0.8,
    15: 0.8,
    16: 0.8,
    17: 1.0,  # Base
    18: 2.5,  # Retour maison
    19: 9.5,  # BRANCHE LA VOITURE - début charge
    20: 10.0, # Charge pleine puissance
    21: 10.0, # Charge pleine puissance
    22: 9.5,  # Charge
    23: 9.0,  # Charge
}

# Facteur saisonnier (1.0 = été, légèrement plus en hiver)
def get_seasonal_factor(month):
    """Retourne le facteur saisonnier. EV = stable, légère hausse hiver."""
    seasonal = {
        1: 1.15,   # Janvier - hiver
        2: 1.12,
        3: 1.05,
        4: 1.0,
        5: 0.98,
        6: 0.95,   # Juin - été
        7: 0.93,
        8: 0.95,
        9: 1.0,
        10: 1.05,
        11: 1.10,
        12: 1.15,  # Décembre - hiver
    }
    return seasonal.get(month, 1.0)


def generate_ev_data():
    """Génère 2 ans de données EV."""
    
    start_date = datetime(2022, 1, 1, 0, 0, 0)
    end_date = datetime(2024, 1, 1, 0, 0, 0)
    
    data = []
    current = start_date
    
    while current < end_date:
        hour = current.hour
        month = current.month
        
        # Base value from hourly profile
        base = HOURLY_PROFILE[hour]
        
        # Apply seasonal factor
        seasonal = get_seasonal_factor(month)
        
        # Add some randomness (±15%)
        noise = random.uniform(0.85, 1.15)
        
        # Weekend slightly different (more home time)
        if current.weekday() >= 5:  # Samedi/Dimanche
            if 10 <= hour <= 16:
                noise *= 1.3  # Plus de conso le WE en journée
        
        value = base * seasonal * noise
        
        data.append({
            'timestamp': current.strftime("%Y-%m-%d %H:%M:%S"),
            'value': round(value, 2)
        })
        
        current += timedelta(minutes=15)
    
    return data


def main():
    print("🔌 Génération du profil EV pour client 00000...")
    
    data = generate_ev_data()
    
    print(f"   {len(data)} points générés (2 ans, 15 min)")
    
    # Écrire le CSV
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'value'])
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Fichier créé: {OUTPUT_FILE}")
    
    # Afficher quelques stats
    night_vals = [d['value'] for d in data if int(d['timestamp'][11:13]) in [22,23,0,1,2,3,4,5]]
    day_vals = [d['value'] for d in data if int(d['timestamp'][11:13]) in [10,11,12,13,14,15,16,17]]
    
    winter_vals = [d['value'] for d in data if int(d['timestamp'][5:7]) in [1,2,11,12]]
    summer_vals = [d['value'] for d in data if int(d['timestamp'][5:7]) in [6,7,8]]
    
    print(f"\n📊 Stats du profil:")
    print(f"   Moyenne nuit (22h-6h):  {sum(night_vals)/len(night_vals):.2f} kWh")
    print(f"   Moyenne jour (10h-18h): {sum(day_vals)/len(day_vals):.2f} kWh")
    print(f"   Ratio nuit/jour: {(sum(night_vals)/len(night_vals)) / (sum(day_vals)/len(day_vals)):.2f}")
    print(f"\n   Moyenne hiver: {sum(winter_vals)/len(winter_vals):.2f} kWh")
    print(f"   Moyenne été:   {sum(summer_vals)/len(summer_vals):.2f} kWh")
    print(f"   Ratio hiver/été: {(sum(winter_vals)/len(winter_vals)) / (sum(summer_vals)/len(summer_vals)):.2f}")


if __name__ == "__main__":
    main()


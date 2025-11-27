"""
Clustering des load curves pour identifier les profils types.
Usage:
    python -m src.clustering --sample 500 --clusters 6
    python -m src.clustering --find-optimal --sample 300
"""
import os
import csv
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

# Essayer d'importer sklearn, sinon donner des instructions
try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
except ImportError:
    print("❌ sklearn non installé. Exécute: pip install scikit-learn")
    exit(1)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = Path(__file__).parent / "clusters.json"


def extract_customer_id(filepath: Path) -> str:
    """Extrait l'ID client du nom de fichier."""
    # LU_ENO_DELPHI_LU_virtual_ind_00001.csv → 00001
    name = filepath.stem
    return name.split("_")[-1]


def extract_features(csv_path: Path) -> dict:
    """Extrait les features d'un fichier CSV loadcurve."""
    
    hourly_values = defaultdict(list)  # {0: [...], 1: [...], ..., 23: [...]}
    monthly_values = defaultdict(list)  # {1: [...], 2: [...], ..., 12: [...]}
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            value = float(row['value'])
            
            hourly_values[ts.hour].append(value)
            monthly_values[ts.month].append(value)
    
    # 1. Profil journalier moyen (24 valeurs)
    hourly_profile = np.array([
        np.mean(hourly_values[h]) if hourly_values[h] else 0 
        for h in range(24)
    ])
    
    # 2. Saisonnalité
    winter_months = [11, 12, 1, 2]
    summer_months = [6, 7, 8]
    
    winter_values = [v for m in winter_months for v in monthly_values.get(m, [])]
    summer_values = [v for m in summer_months for v in monthly_values.get(m, [])]
    
    winter_avg = np.mean(winter_values) if winter_values else 1
    summer_avg = np.mean(summer_values) if summer_values else 1
    ratio_winter_summer = winter_avg / summer_avg if summer_avg > 0 else 1.0
    
    # 3. Variabilité (coefficient de variation)
    all_values = [v for hour_vals in hourly_values.values() for v in hour_vals]
    mean_val = np.mean(all_values) if all_values else 1
    std_val = np.std(all_values) if all_values else 0
    variability = std_val / mean_val if mean_val > 0 else 0
    
    # 4. Total kWh
    total_kwh = sum(all_values)
    
    return {
        'hourly_profile': hourly_profile,
        'ratio_winter_summer': ratio_winter_summer,
        'variability': variability,
        'total_kwh': total_kwh
    }


def prepare_feature_matrix(customers_data: dict) -> np.ndarray:
    """Prépare la matrice de features normalisée et pondérée."""
    
    features = []
    customer_ids = []
    
    for customer_id, data in customers_data.items():
        # Normaliser le profil horaire (forme 0-1)
        profile = data['hourly_profile']
        profile_max = profile.max() if profile.max() > 0 else 1
        profile_norm = profile / profile_max
        
        # Features saisonnières normalisées
        ratio = min(data['ratio_winter_summer'] / 4.0, 1.5)  # Cap à 1.5
        variability = min(data['variability'] / 2.0, 1.5)    # Cap à 1.5
        
        # Vecteur complet
        vector = np.concatenate([
            profile_norm,    # 24 valeurs
            [ratio],         # 1 valeur
            [variability]    # 1 valeur
        ])
        
        features.append(vector)
        customer_ids.append(customer_id)
    
    X = np.array(features)
    
    # Pondérer les features saisonnières (plus d'importance)
    X[:, 24] *= 3.0  # ratio_winter_summer ×3
    X[:, 25] *= 2.0  # variability ×2
    
    return X, customer_ids


def find_optimal_clusters(X: np.ndarray, k_range=range(3, 12)) -> int:
    """Trouve le nombre optimal de clusters."""
    
    print("\n🔍 Recherche du nombre optimal de clusters...")
    print("-" * 50)
    
    results = []
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        inertia = kmeans.inertia_
        silhouette = silhouette_score(X, labels)
        
        results.append({
            'k': k,
            'inertia': inertia,
            'silhouette': silhouette
        })
        
        bar = "█" * int(silhouette * 40)
        print(f"  k={k:2d} │ silhouette={silhouette:.3f} │ {bar}")
    
    # Meilleur k = silhouette max
    best = max(results, key=lambda x: x['silhouette'])
    print("-" * 50)
    print(f"✅ Optimal: k={best['k']} (silhouette={best['silhouette']:.3f})")
    
    return best['k']


def assign_cluster_names(kmeans, X, customer_ids, customers_data) -> dict:
    """Assigne des noms aux clusters basés sur leurs caractéristiques."""
    
    cluster_stats = defaultdict(lambda: {
        'count': 0,
        'ratios': [],
        'peak_hours': [],
        'profiles': []
    })
    
    labels = kmeans.predict(X)
    
    for i, (customer_id, label) in enumerate(zip(customer_ids, labels)):
        data = customers_data[customer_id]
        cluster_stats[label]['count'] += 1
        cluster_stats[label]['ratios'].append(data['ratio_winter_summer'])
        cluster_stats[label]['profiles'].append(data['hourly_profile'])
        
        # Trouver les heures de pic
        profile = data['hourly_profile']
        peak_hour = np.argmax(profile)
        cluster_stats[label]['peak_hours'].append(peak_hour)
    
    cluster_definitions = {}
    
    for cluster_id, stats in cluster_stats.items():
        avg_ratio = np.mean(stats['ratios'])
        avg_profile = np.mean(stats['profiles'], axis=0)
        peak_hours = stats['peak_hours']
        
        # Déterminer le nom basé sur les caractéristiques
        avg_peak = np.mean(peak_hours)
        night_peaks = sum(1 for h in peak_hours if h >= 22 or h <= 5)
        night_ratio = night_peaks / len(peak_hours) if peak_hours else 0
        
        # Logique de nommage
        if avg_ratio > 2.5:
            name = "🌡️ Pompe à chaleur"
            description = f"Forte saisonnalité (ratio hiver/été: {avg_ratio:.1f})"
        elif avg_ratio < 0.7:
            name = "❄️ Climatisation"
            description = f"Consommation été > hiver (ratio: {avg_ratio:.1f})"
        elif night_ratio > 0.5:
            name = "🔌 EV Owner"
            description = "Pic de consommation nocturne (22h-6h)"
        elif 6 <= avg_peak <= 9 or 17 <= avg_peak <= 21:
            name = "🏠 Résidentiel classique"
            description = "Pics matin et soir typiques"
        elif 9 <= avg_peak <= 17:
            name = "💼 Télétravail/Bureau"
            description = "Consommation élevée en journée"
        else:
            name = "📊 Profil mixte"
            description = "Pas de pattern dominant"
        
        cluster_definitions[str(cluster_id)] = {
            'name': name,
            'description': description,
            'count': stats['count'],
            'avg_ratio_winter_summer': round(avg_ratio, 2),
            'centroid': [round(x, 3) for x in avg_profile.tolist()]
        }
    
    return cluster_definitions


def main():
    parser = argparse.ArgumentParser(description='Clustering des load curves')
    parser.add_argument('--sample', type=int, default=0, 
                        help='Nombre de fichiers à échantillonner (0 = tous)')
    parser.add_argument('--clusters', type=int, default=0,
                        help='Nombre de clusters (0 = auto-détection)')
    parser.add_argument('--find-optimal', action='store_true',
                        help='Affiche le graphique pour trouver k optimal')
    args = parser.parse_args()
    
    # 1. Lister les fichiers CSV
    csv_files = list(DATA_DIR.glob("*.csv"))
    print(f"\n📁 Trouvé {len(csv_files)} fichiers CSV dans {DATA_DIR}")
    
    if len(csv_files) == 0:
        print("❌ Aucun fichier CSV trouvé!")
        return
    
    # 2. Échantillonner si demandé
    if args.sample > 0 and args.sample < len(csv_files):
        csv_files = random.sample(csv_files, args.sample)
        print(f"📊 Échantillon de {len(csv_files)} fichiers")
    
    # 3. Extraire les features
    print(f"\n⏳ Extraction des features...")
    customers_data = {}
    
    for i, csv_file in enumerate(csv_files):
        if (i + 1) % 50 == 0 or i == len(csv_files) - 1:
            print(f"   {i + 1}/{len(csv_files)} fichiers traités", end='\r')
        
        customer_id = extract_customer_id(csv_file)
        try:
            features = extract_features(csv_file)
            customers_data[customer_id] = features
        except Exception as e:
            print(f"\n⚠️ Erreur sur {csv_file}: {e}")
    
    print(f"\n✅ {len(customers_data)} clients traités")
    
    # 4. Préparer la matrice
    X, customer_ids = prepare_feature_matrix(customers_data)
    print(f"📐 Matrice: {X.shape[0]} clients × {X.shape[1]} features")
    
    # 5. Trouver k optimal ou utiliser la valeur donnée
    if args.clusters > 0:
        n_clusters = args.clusters
        print(f"\n🎯 Utilisation de {n_clusters} clusters (paramètre)")
    else:
        n_clusters = find_optimal_clusters(X)
    
    if args.find_optimal:
        print("\n💡 Relance avec --clusters N pour utiliser N clusters")
        return
    
    # 6. Clustering final
    print(f"\n🔄 Clustering avec k={n_clusters}...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    # 7. Assigner les noms aux clusters
    cluster_definitions = assign_cluster_names(kmeans, X, customer_ids, customers_data)
    
    # 8. Créer le mapping customer → cluster
    customer_clusters = {
        customer_id: int(label)
        for customer_id, label in zip(customer_ids, labels)
    }
    
    # 9. Afficher le résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES CLUSTERS")
    print("=" * 60)
    
    for cluster_id, info in sorted(cluster_definitions.items()):
        print(f"\nCluster {cluster_id}: {info['name']}")
        print(f"  └─ {info['count']} clients ({info['count']/len(customer_ids)*100:.1f}%)")
        print(f"  └─ {info['description']}")
        print(f"  └─ Ratio hiver/été: {info['avg_ratio_winter_summer']}")
    
    # 10. Sauvegarder
    output = {
        'metadata': {
            'created': datetime.now().isoformat(),
            'n_clusters': n_clusters,
            'n_customers': len(customer_ids),
            'silhouette_score': round(silhouette_score(X, labels), 3)
        },
        'cluster_definitions': cluster_definitions,
        'customer_clusters': customer_clusters
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Résultats sauvegardés dans {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()


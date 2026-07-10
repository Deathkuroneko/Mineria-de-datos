import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
import scipy.cluster.hierarchy as sch
import os

print("📊 Cargando datos optimizados para el Dendrograma...")
df = pd.read_parquet("opensky_datos_optimizados.parquet")

X = df[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

os.makedirs("Visualizacion", exist_ok=True)

print("📐 Generando Dendrograma Jerárquico (Criterio de Ward)...")
# Muestra controlada para evitar desbordar la memoria y mantener el gráfico legible
muestra_tamano = min(1500, len(X_scaled))
indices_muestra = np.random.choice(X_scaled.shape[0], muestra_tamano, replace=False)
X_sample = X_scaled[indices_muestra]

plt.figure(figsize=(10, 5))
sch.dendrogram(
    sch.linkage(X_sample, method='ward'),
    no_labels=True,
    color_threshold=None
)
plt.title('Dendrograma Jerárquico Aglomerativo (Muestra de Validación UCE)')
plt.xlabel('Aeronaves Observadas (Muestra Aleatoria)')
plt.ylabel('Distancia Euclídea de Fusión')
plt.tight_layout()

# Guardar directamente en la carpeta de Visualización
plt.savefig("Visualizacion/dendrograma_jerarquico.png", dpi=300)
plt.close()
print("✔️ ¡Imagen del Dendrograma guardada con éxito!")
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Datos de ejemplo: [Tamaño paquete KB, puerto sospechoso 1/0, es_sospechoso 1/0]
X_train = [
    [50, 1, 1],   # tráfico sospechoso
    [5, 0, 0],    # tráfico normal
    [120, 1, 1],  # sospechoso
    [10, 0, 0]    # normal
]

y_train = [1, 0, 1, 0]

# Entrenar modelo
model = RandomForestClassifier()
model.fit([x[:2] for x in X_train], y_train)

# Guardar modelo
os.makedirs("data", exist_ok=True)
joblib.dump(model, "data/abeja3_model.pkl")
print("[IA] Modelo de red entrenado y guardado en data/abeja_red_model.pkl")

from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Datos de ejemplo: [CPU %, Memoria MB, es_sospechoso 1/0]
X_train = [
    [50, 100, 1],   # proceso sospechoso
    [5, 50, 0],     # proceso normal
    [70, 200, 1],   # sospechoso
    [10, 60, 0]     # normal
]

y_train = [1, 0, 1, 0]

# Entrenar modelo
model = RandomForestClassifier()
model.fit([x[:2] for x in X_train], y_train)  # usar solo CPU y Memoria como features

# Guardar modelo
os.makedirs("data", exist_ok=True)
joblib.dump(model, "data/abeja2_model.pkl")
print("[IA] Modelo de procesos entrenado y guardado en data/abeja_procesos_model.pkl")

from sklearn.ensemble import RandomForestClassifier
import numpy as np
import joblib
import os

# Datos de entrenamiento simulados
# X = [tamaño en KB, entropía, es .exe (1/0)]
X_train = [
    [50, 4.5, 1],   # archivo sospechoso
    [2, 3.2, 0],    # archivo normal
    [120, 5.0, 1],  # otro sospechoso
    [1, 2.8, 0]     # normal
]

y_train = [1, 0, 1, 0]  # 1=sospechoso, 0=no sospechoso

# Entrenar modelo
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Guardar modelo
os.makedirs("data", exist_ok=True)
joblib.dump(model, "data/abeja1_model.pkl")
print("[IA] Modelo entrenado y guardado en data/abeja1_model.pkl")

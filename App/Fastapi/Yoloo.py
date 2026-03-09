import sqlite3
import os
import cv2
import pytesseract
from ultralytics import YOLO

# --- CONFIGURACIÓN ESTRATÉGICA DE RUTAS ---
# 1. Ubicación de este script (Gaming/App/Fastapi/Yoloo.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Apuntamos a la carpeta Db que está en el mismo nivel
DB_FOLDER = os.path.join(BASE_DIR, "Db")

# 3. Aseguramos que la carpeta Db exista (por si el gitignore la borró)
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# 4. Ruta final del archivo .db
PATH_SQLITE = os.path.join(DB_FOLDER, "progreso_jugador.db")

# Cargamos el modelo (está en la misma carpeta Fastapi según tu imagen)
model = YOLO('yolov8n.pt') 

def analizar_gameplay_aaa(frame, nombre_archivo):
    """
    Versión Triple A: Evalúa múltiples métricas y guarda en la carpeta Db.
    """
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    # Creamos la tabla robusta si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_aaa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            enemigos INTEGER,
            municion TEXT,
            estado_accion TEXT,
            archivo_origen TEXT
        )
    ''')

    results = model(frame, verbose=False)
    
    # Métricas iniciales
    conteo_enemigos = 0
    municion_valor = "N/A"
    estado = "Exploración"

    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            
            if label == 'person':
                conteo_enemigos += 1
            
            # Watch Dogs HUD: Buscamos el celular/reloj para Tesseract
            if label in ['cell phone', 'clock']:
                coords = box.xyxy[0].tolist()
                roi = frame[int(coords[1]):int(coords[3]), int(coords[0]):int(coords[2])]
                # Tesseract entra en acción con el recorte de YOLO
                municion_valor = pytesseract.image_to_string(roi, config='--psm 7 digits').strip()

    # Lógica de estado dinámico
    if conteo_enemigos > 0:
        estado = "Combate"
    if "fire" in [model.names[int(b.cls[0])] for r in results for b in r.boxes]:
        estado = "Caos Total"

    # Guardado en la DB (Ubicada en /Db/)
    cursor.execute('''
        INSERT INTO telemetria_aaa (enemigos, municion, estado_accion, archivo_origen)
        VALUES (?, ?, ?, ?)
    ''', (conteo_enemigos, municion_valor, estado, nombre_archivo))
    
    conn.commit()
    conn.close()
    
    return {"enemigos": conteo_enemigos, "status": estado}
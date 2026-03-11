import sqlite3
import os
import cv2
from ultralytics import YOLO

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_SQLITE = os.path.join(BASE_DIR, "Db", "progreso_jugador.db")

# Aseguramos que la carpeta Db exista
if not os.path.exists(os.path.join(BASE_DIR, "Db")):
    os.makedirs(os.path.join(BASE_DIR, "Db"))

# Cargamos el modelo
model = YOLO(os.path.join(BASE_DIR, 'yolov8n.pt'))

def inicializar_db():
    """Crea las tablas necesarias desde cero."""
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    # Tabla 1: Telemetría General
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_general (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo_origen TEXT,
            enemigos_conteo INTEGER,
            estado_accion TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla 2: Coordenadas para Tesseract (Lo que verificaste antes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coordenadas_ocr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_frame TEXT,
            tipo_indicador TEXT,
            x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
            texto_extraido TEXT DEFAULT 'PENDIENTE',
            procesado INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Inicializamos la base de datos al importar el script
inicializar_db()

def analizar_gameplay_aaa(frame, nombre_archivo):
    """
    Función principal llamada por loading.py.
    Registra datos en las dos tablas y devuelve un resumen.
    """
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    results = model(frame, verbose=False)
    conteo_enemigos = 0
    detecciones_ocr = []

    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            coords = box.xyxy[0].tolist()
            conf = float(box.conf[0])

            if label == 'person':
                conteo_enemigos += 1
            
            # Captura de indicadores para Tesseract (Celular/HUD)
            if label in ['cell phone', 'clock'] and conf > 0.3:
                detecciones_ocr.append((
                    nombre_archivo, label, 
                    int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                ))

    # Guardar en Tabla 1
    cursor.execute('''
        INSERT INTO telemetria_general (archivo_origen, enemigos_conteo, estado_accion)
        VALUES (?, ?, ?)
    ''', (nombre_archivo, conteo_enemigos, "Combate" if conteo_enemigos > 0 else "Exploración"))

    # Guardar en Tabla 2 (Mapa de coordenadas)
    if detecciones_ocr:
        cursor.executemany('''
            INSERT INTO coordenadas_ocr (id_frame, tipo_indicador, x1, y1, x2, y2)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', detecciones_ocr)

    conn.commit()
    conn.close()
    
    return {"enemigos": conteo_enemigos, "ocr_detectados": len(detecciones_ocr)}
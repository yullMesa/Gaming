import sqlite3
import pytesseract
import cv2
import os
from ultralytics import YOLO
import pytesseract

# Detectamos la ruta de la carpeta 'Db' donde está este archivo
# Según tu imagen, Yoloo.py está dentro de Gaming/App/Fastapi/Db/
PATH_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(PATH_ACTUAL, "progreso_jugador.db")

# Cargamos el modelo una sola vez
model = YOLO('yolov8n.pt') 

def inicializar_db():
    # Conectamos directamente al archivo en la carpeta actual
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            enemigos_total INTEGER,
            datos_ocr TEXT,
            archivo_origen TEXT
        )
    ''')
    conn.commit()
    return conn

def analizar_gameplay(frame, nombre_archivo):
    conn = inicializar_db()
    cursor = conn.cursor()
    
    results = model(frame, verbose=False)
    conteo_enemigos = 0
    ocr_data = "N/A"

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            
            # En Watch Dogs, 'person' suelen ser los enemigos/NPCs
            if label == 'person':
                conteo_enemigos += 1
            
            # Si YOLO llegara a detectar un área de interés (ej: munición)
            # aquí podrías activar Tesseract dinámicamente
            if label == 'cell phone' or label == 'clock': # Elementos del HUD
                coords = box.xyxy[0].tolist()
                roi = frame[int(coords[1]):int(coords[3]), int(coords[0]):int(coords[2])]
                ocr_data = pytesseract.image_to_string(roi, config='--psm 7').strip()

    # Guardamos el registro en la DB
    cursor.execute('''
        INSERT INTO sesiones (enemigos_total, datos_ocr, archivo_origen) 
        VALUES (?, ?, ?)
    ''', (conteo_enemigos, ocr_data, nombre_archivo))
    
    conn.commit()
    conn.close()
    
    return {"enemigos": conteo_enemigos, "ocr": ocr_data}
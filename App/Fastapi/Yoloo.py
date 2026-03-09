import sqlite3
import os
import cv2
import pytesseract
from ultralytics import YOLO

# --- CONFIGURACIÓN DE RUTAS ---
# Detecta la carpeta donde está este script (Gaming/App/Fastapi)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define la ruta a la carpeta Db y al archivo .db
DB_FOLDER = os.path.join(BASE_DIR, "Db")
PATH_SQLITE = os.path.join(DB_FOLDER, "progreso_jugador.db")

# Crea la carpeta Db si no existe
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# Cargamos el modelo YOLOv8 (Asegúrate de que el .pt esté en Fastapi)
model = YOLO(os.path.join(BASE_DIR, 'yolov8n.pt'))

def inicializar_db():
    """Crea la tabla con la estructura completa para juegos AAA."""
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_aaa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            enemigos INTEGER,
            bateria_status TEXT,
            vida_indicador TEXT,
            estado_accion TEXT,
            archivo_origen TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Inicializamos la DB apenas se carga el módulo
inicializar_db()

def analizar_gameplay_aaa(frame, nombre_archivo):
    """
    Analiza el frame buscando enemigos e indicadores de interfaz (HUD).
    """
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    results = model(frame, verbose=False)
    
    # Valores iniciales
    conteo_enemigos = 0
    bateria = "N/A"
    vida = "Estable"
    estado = "Exploración"

    # 1. Procesar detecciones de YOLO
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])

            # Detectar enemigos/NPCs
            if label == 'person':
                conteo_enemigos += 1
            
            # Detectar el HUD (Celular/Reloj en Watch Dogs) para Tesseract
            if label in ['cell phone', 'clock'] and conf > 0.4:
                coords = box.xyxy[0].tolist()
                # Recorte del área de interés (ROI)
                x1, y1, x2, y2 = map(int, coords)
                roi = frame[y1:y2, x1:x2]
                
                if roi.size > 0:
                    # Pre-procesamiento para mejorar el OCR
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    # Usamos PSM 7 (trata la imagen como una sola línea de texto)
                    texto_detectado = pytesseract.image_to_string(gray, config='--psm 7').strip()
                    if texto_detectado:
                        bateria = texto_detectado

    # 2. Lógica de estado dinámico
    if conteo_enemigos > 0:
        estado = "Combate"
    
    # 3. Guardar en la Base de Datos
    cursor.execute('''
        INSERT INTO telemetria_aaa 
        (enemigos, bateria_status, vida_indicador, estado_accion, archivo_origen) 
        VALUES (?, ?, ?, ?, ?)
    ''', (conteo_enemigos, bateria, vida, estado, nombre_archivo))
    
    conn.commit()
    conn.close()
    
    return {"enemigos": conteo_enemigos, "bateria": bateria, "estado": estado}
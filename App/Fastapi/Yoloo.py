import sqlite3
import os
import cv2
import pytesseract
from ultralytics import YOLO

# Rutas inteligentes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Db", "progreso_jugador.db")

model = YOLO('yolov8n.pt')

def analizar_gameplay_aaa(frame, nombre_archivo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla expandida para métricas estáticas
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

    results = model(frame, verbose=False)
    
    # Valores por defecto
    conteo_enemigos = 0
    bateria = "N/A"
    vida = "Estable" # En Watch Dogs la vida es visual/sangre
    estado = "Exploración"

    # 1. Analizamos entidades móviles
    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            if label == 'person':
                conteo_enemigos += 1

    # 2. Análisis de Indicadores Estáticos (HUD)
    # Definimos coordenadas de ROI basadas en Watch Dogs (esquina inferior derecha para el cel)
    # Si quieres que sea automático, YOLO debe detectar la clase 'cell phone' primero
    h, w, _ = frame.shape
    
    # Ejemplo de ROI para el área de batería/celular (Ajustar según tu resolución)
    # Tomamos el 20% inferior derecho de la pantalla
    roi_hud = frame[int(h*0.7):int(h*0.95), int(w*0.75):int(w*0.95)]
    
    # Pre-procesamiento para Tesseract (Crucial para juegos AAA con fondos complejos)
    gray_hud = cv2.cvtColor(roi_hud, cv2.COLOR_BGR2GRAY)
    _, thresh_hud = cv2.threshold(gray_hud, 150, 255, cv2.THRESH_BINARY_INV)

    # Tesseract intenta leer el nivel de batería o habilidades
    texto_hud = pytesseract.image_to_string(thresh_hud, config='--psm 6').strip()
    if any(char.isdigit() for char in texto_hud):
        bateria = texto_hud

    # 3. Lógica de Estado
    if conteo_enemigos > 0:
        estado = "Combate"
    
    # Detección de daño (Si el frame tiene mucho rojo en los bordes)
    # Calculamos el promedio del canal Rojo en los bordes
    b_mean, g_mean, r_mean = cv2.mean(frame[:50, :50])[:3]
    if r_mean > 150: # Umbral de alerta roja
        vida = "Baja / Daño"
        estado = "Peligro"

    # Guardado en DB
    cursor.execute('''
        INSERT INTO telemetria_aaa (enemigos, bateria_status, vida_indicador, estado_accion, archivo_origen)
        VALUES (?, ?, ?, ?, ?)
    ''', (conteo_enemigos, bateria, vida, estado, nombre_archivo))
    
    conn.commit()
    conn.close()
    
    return {"enemigos": conteo_enemigos, "bateria": bateria, "estado": estado}
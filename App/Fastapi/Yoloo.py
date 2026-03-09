import sqlite3
import cv2
import os
import pytesseract
import time
from ultralytics import YOLO

# Rutas limpias (Sin carpetas extra)
FOLDER_DB = os.path.dirname(os.path.abspath(__file__))
PATH_SQLITE = os.path.join(FOLDER_DB, "progreso_jugador.db")

# Modelo YOLOv8
model = YOLO('yolov8n.pt')

def inicializar_db_aaa():
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    # 1. Tabla de Sesiones (Información general)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sesiones (
            id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            juego_detectado TEXT,
            duracion_total REAL
        )
    ''')

    # 2. Tabla de Telemetría (Lo que pasa frame a frame)
    # Aquí es donde YOLO y Tesseract meten la data pesada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
            id_sesion INTEGER,
            timestamp_video REAL,
            enemigos_conteo INTEGER,
            aliados_conteo INTEGER,
            municion_texto TEXT,
            vida_porcentaje REAL,
            estado_accion TEXT, -- 'Sigilo', 'Combate', 'Muerto', 'Menu'
            posicion_x REAL, -- Si YOLO detecta el minimapa
            posicion_y REAL,
            FOREIGN KEY(id_sesion) REFERENCES sesiones(id_sesion)
        )
    ''')
    
    conn.commit()
    return conn

def analizar_gameplay_robusto(frame, nombre_archivo):
    conn = inicializar_db_aaa()
    cursor = conn.cursor()
    
    results = model(frame, verbose=False)
    
    # --- MÉTRICAS ---
    conteo_enemigos = 0
    municion = "N/A"
    agresividad = 0.0
    evento = "Exploración"

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])
            
            # 1. Detección de Acción (Enemigos/NPCs)
            if label == 'person':
                conteo_enemigos += 1
            
            # 2. Ayuda a Tesseract: Buscar el HUD (Celular/Reloj en Watch Dogs)
            if label in ['cell phone', 'clock'] and conf > 0.5:
                coords = box.xyxy[0].tolist()
                # Recorte de precisión para Tesseract
                roi = frame[int(coords[1]):int(coords[3]), int(coords[0]):int(coords[2])]
                # Limpiamos imagen para mejor lectura
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                municion = pytesseract.image_to_string(gray, config='--psm 7 digits').strip()
                evento = "Combate Activo"

    # 3. Cálculo de Agresividad (Ejemplo: Densidad de enemigos por frame)
    if conteo_enemigos > 3:
        agresividad = 0.8  # Alta tensión
        evento = "Enfrentamiento Pesado"
    elif conteo_enemigos > 0:
        agresividad = 0.3

    # Guardado en la DB robusta
    cursor.execute('''
        INSERT INTO sesiones_pro 
        (enemigos_en_pantalla, municion_detectada, nivel_agresividad, evento_especial, archivo_origen) 
        VALUES (?, ?, ?, ?, ?)
    ''', (conteo_enemigos, municion, agresividad, evento, nombre_archivo))
    
    conn.commit()
    conn.close()
    
    return {
        "enemigos": conteo_enemigos, 
        "municion": municion, 
        "agresividad": agresividad,
        "evento": evento
    }

def analizar_gameplay_aaa(frame, id_sesion, tiempo_seg, nombre_img):
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    results = model(frame, verbose=False)
    
    # Inicializamos variables de estado
    data = {
        "enemigos": 0, "aliados": 0, "municion": "0", 
        "vida": 100.0, "estado": "Explorando"
    }

    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            coords = box.xyxy[0].tolist()

            # --- DETECCIÓN DE ENTIDADES ---
            if label == 'person':
                # Podrías diferenciar por color si son enemigos o aliados
                data["enemigos"] += 1
            
            # --- DETECCIÓN DE INTERFAZ (HUD) ---
            # Si YOLO detecta elementos que suelen tener números
            if label in ['cell phone', 'clock', 'tv', 'laptop']:
                roi = frame[int(coords[1]):int(coords[3]), int(coords[0]):int(coords[2])]
                texto = pytesseract.image_to_string(roi, config='--psm 7').strip()
                if texto.isdigit():
                    data["municion"] = texto
            
            # --- LÓGICA DE ESTADO AAA ---
            if data["enemigos"] > 0:
                data["estado"] = "Combate"
            if label == 'fire' or label == 'explosion': # Elementos de caos
                data["estado"] = "Acción Intensa"

    # Insertar en la tabla de telemetría
    cursor.execute('''
        INSERT INTO telemetria 
        (id_sesion, timestamp_video, enemigos_conteo, aliados_conteo, municion_texto, vida_porcentaje, estado_accion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (id_sesion, tiempo_seg, data["enemigos"], data["aliados"], data["municion"], data["vida"], data["estado"]))
    
    conn.commit()
    conn.close()
    return data
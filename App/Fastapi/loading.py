import os
import sys
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
import cv2
import json
from ultralytics import YOLO
import pytesseract
import time
import shutil
from Yoloo import analizar_gameplay_aaa 

app = FastAPI()

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# 2. Definimos la ruta de Assets que está al mismo nivel que loading.py
# Según tu imagen: Gaming/App/Fastapi/Assets
PATH_ASSETS = os.path.join(DIRECTORIO_ACTUAL, "Assets")

# 3. Definimos la carpeta final para los frames
OUTPUT_DIR = os.path.join(PATH_ASSETS, "frames_extraidos")

# Aseguramos que la carpeta exista para evitar errores de cv2.imwrite
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"✅ Carpeta creada: {OUTPUT_DIR}")

# --- CARGA DE MODELOS ---
model = YOLO('yolov8n.pt')

ruta_actual = os.path.dirname(os.path.abspath(__file__)) # Esto es 'Fastapi'
ruta_raiz = os.path.dirname(ruta_actual) # Esto sube un nivel a 'datascience'

# 2. Agregamos la raíz al sistema para que vea la carpeta 'ML'
if ruta_raiz not in sys.path:
    sys.path.append(ruta_raiz)

# NUEVA: Ruta absoluta a la carpeta de Base de Datos (Db)
PATH_DB = os.path.join(DIRECTORIO_ACTUAL, "Db")
# Aseguramos que ambas carpetas existan
for folder in [OUTPUT_DIR, PATH_DB]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Carpeta garantizada: {folder}")

# Buscamos la carpeta 'teser' subiendo niveles desde este archivo
# 1. Ubicación de este archivo (Gaming/App/Fastapi/loading.py)
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# 2. Subimos a 'App' -> Subimos a 'Gaming' (La raíz)
RAIZ_GAMING = os.path.dirname(os.path.dirname(DIRECTORIO_ACTUAL))

# 3. Bajamos a Framework/teser/tesseract.exe
ruta_tesseract_exe = os.path.join(RAIZ_GAMING, "Framework", "teser", "tesseract.exe")

# Asignación y verificación
if os.path.exists(ruta_tesseract_exe):
    pytesseract.pytesseract.tesseract_cmd = ruta_tesseract_exe
else:
    print(f"❌ ERROR: Tesseract no está en {ruta_tesseract_exe}")


def proceso_maestro_ysm(video_path, rangos):
    start_time = time.time() # Timer global
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: No se pudo abrir el video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames_procesados = []
    metadata_final = []

    # --- FASE 1: EXTRACCIÓN (Bloqueante hasta terminar) ---
    print(f"🚀 Iniciando extracción de frames para: {video_path}")
    
    for r in rangos:
        inicio, fin = map(int, r.split('-'))
        frame_actual = int(inicio * fps)
        frame_limite = int(fin * fps)
        salto = int(fps * 7) # Ajusta esto según qué tan denso quieres el análisis

        while frame_actual <= frame_limite:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_actual)
            ret, frame = cap.read()
            if not ret: break

            nombre_archivo = f"moment_{frame_actual}.jpg"
            ruta_frame = os.path.join(OUTPUT_DIR, nombre_archivo)
            
            # Guardamos físicamente
            cv2.imwrite(ruta_frame, frame)
            frames_procesados.append((ruta_frame, frame_actual))
            
            frame_actual += salto
    
    cap.release()
    print(f"✅ Fase 1 completada: {len(frames_procesados)} imágenes guardadas.")

    # --- FASE 2: ANÁLISIS ML (Solo inicia cuando los archivos existen) ---
    print("🧠 Iniciando análisis YOLO...")
    
    for ruta_img, f_id in frames_procesados:
        if os.path.exists(ruta_img):
            frame = cv2.imread(ruta_img)
            # Ejecutas la lógica robusta
            res = analizar_gameplay_aaa(frame, os.path.basename(ruta_img))
            
            metadata_final.append({
                "seg": round(f_id / fps, 2),
                "data": res
            })

    # Al terminar, ejecutamos la limpieza que querías
    shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🧹 Fase 2 completada y carpeta de frames limpia.")
    # --- FASE 3: CIERRE Y REPORTE ---
    with open(os.path.join(PATH_DB, "gameplay_data.json"), "w") as f:
        json.dump(metadata_final, f, indent=4)

    end_time = time.time()
    duracion = round(end_time - start_time, 7)
    print(f"🏆 Proceso total finalizado en {duracion} segundos.")


    try:
        # Borramos todo el contenido de la carpeta de frames
        shutil.rmtree(OUTPUT_DIR)
        # La recreamos vacía para el siguiente proceso
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"🧹 Carpeta de frames limpia para el próximo análisis.")
    except Exception as e:
        print(f"⚠️ No se pudo limpiar la carpeta: {e}")

@app.post("/procesar-todo/")
async def endpoint_maestro(background_tasks: BackgroundTasks, ruta: str, tiempos: str):
    if not os.path.exists(ruta):
        return {"error": "Video no encontrado"}
    
    lista_rangos = tiempos.split(",") if tiempos else []
    
    # Usamos BackgroundTasks para que el usuario reciba el "ok" 
    # mientras el servidor trabaja de fondo
    background_tasks.add_task(proceso_maestro_ysm, ruta, lista_rangos)
    
    return {
        "status": "procesando",
        "mensaje": "El backend está extrayendo y analizando. Revisa el JSON en unos momentos."
    }

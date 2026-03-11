import sqlite3
import cv2
import pytesseract
import os
from App.Fastapi.Yoloo import PATH_SQLITE # Usamos la ruta que ya definimos

def procesar_pendientes_ocr():
    conn = sqlite3.connect(PATH_SQLITE)
    cursor = conn.cursor()
    
    # Buscamos solo lo que YOLO marcó pero Tesseract no ha leído
    cursor.execute('SELECT id, id_frame, x1, y1, x2, y2 FROM coordenadas_ocr WHERE procesado = 0')
    pendientes = cursor.fetchall()
    
    for p in pendientes:
        id_reg, frame_name, x1, y1, x2, y2 = p
        ruta_img = os.path.join("Assets", "frames_extraidos", frame_name)
        
        if os.path.exists(ruta_img):
            img = cv2.imread(ruta_img)
            # Recorte quirúrgico basado en las coordenadas de YOLO
            roi = img[y1:y2, x1:x2]
            
            # Tesseract lee el recorte
            texto = pytesseract.image_to_string(roi, config='--psm 7').strip()
            
            # Actualizamos la tabla: ponemos el texto y marcamos como PROCESADO (1)
            cursor.execute('''
                UPDATE coordenadas_ocr 
                SET texto_extraido = ?, procesado = 1 
                WHERE id = ?
            ''', (texto, id_reg))
            print(f"✅ Leído en {frame_name}: {texto}")
            
    conn.commit()
    conn.close()
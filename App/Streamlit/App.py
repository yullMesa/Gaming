import requests
import streamlit as st
import tkinter as tk
from tkinter import filedialog

def seleccionar_archivo_local():
    root = tk.Tk()
    root.withdraw()
    # Forzar que la ventana salga al frente
    root.attributes('-topmost', True)
    ruta = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
    root.destroy()
    return ruta

st.set_page_config(layout="wide", page_title="Gamer Diagnostic Tool")
st.title("Gamer Diagnostic Tool 🎮")

# --- SECCIÓN DE ENTRADA ---
with st.expander("📤 Sube tus datos de partida"):
    st.write("Aquí puedes subir los archivos generados por nuestro motor de análisis.")
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        yt_link = st.text_input("Link de YouTube de tu Gameplay", "https://youtu.be/9qUf8iQfjvQ")
    
    with col_input2:
        uploaded_file = st.file_uploader("Sube tu archivo .CSV o .JSON extraído", type=['csv', 'json'])

st.divider()
# --- DISEÑO DE PANTALLA ---
col_video, col_stats = st.columns([0.7, 0.3])

with col_video:
    st.subheader("📺 Visualización de tu gameplay")
    # Restauramos el link de YouTube para no consumir RAM local
    # yt_link viene del st.text_input de la sección de entrada
    st.video(yt_link) 
    
st.divider()

with col_stats:
    st.subheader("🕵️ Diagnóstico YSM")

    #subir el video en formato mp4 para ser analizado
    with st.expander("📂 Selección de Gameplay Local"):
        st.write("Selecciona tu archivo y define los 7 momentos.")
        
        # Botón para abrir el explorador de Windows
        if st.button("📁 Abrir Explorador de Archivos"):
            ruta = seleccionar_archivo_local()
            if ruta:
                st.session_state.ruta_seleccionada = ruta
        
        # Mostrar la ruta seleccionada (solo lectura para que no la editen mal)
        ruta_final = st.session_state.get('ruta_seleccionada', "")
        st.text_input("Ruta cargada:", value=ruta_final, disabled=True)

        # Slots de tiempo (tus 7 momentos)
        rangos_seleccionados = []
        for i in range(1, 8):
            col_ini, col_fin = st.columns(2)
            with col_ini:
                ini = st.number_input(f"M{i} Inicio", min_value=0, key=f"ini_{i}")
            with col_fin:
                fin = st.number_input(f"M{i} Fin", min_value=0, key=f"fin_{i}")
            if fin > ini:
                rangos_seleccionados.append(f"{ini}-{fin}")

        # 1. El botón que "dispara" la acción
        if st.button("Enviar", use_container_width=True):
            
            if ruta_final and rangos_seleccionados:
                tiempos_string = ",".join(rangos_seleccionados)
                
                # Enviamos solo la ruta y los tiempos al backend
                params = {"ruta": ruta_final, "tiempos": tiempos_string}
                response = requests.post("http://localhost:8000/procesar-todo/", params=params)
                
                if response.status_code == 200:
                    st.success("✅ Backend trabajando. YOLO está analizando los frames.")
                else:
                    st.error("❌ Error al contactar el backend. Asegúrate de que esté corriendo.")
                    
    with st.expander("📈Gráficos de Rendimiento (Visual Metrics)"):
        st.write("Aquí se mostrarán los gráficos de rendimiento basados en los datos analizados.")
        # Aquí irían tus gráficos, por ahora solo un placeholder
        st.line_chart([1, 2, 3, 4, 5])

    with st.expander("📝Feedback Narrativo (Natural Language Generation)"):
        st.write("Aquí se generará un feedback narrativo basado en el análisis de tu gameplay.")
        # Placeholder para el feedback narrativo
        st.markdown("""
        **Feedback Ejemplo:**
        - En el minuto 2:30, tu tiempo de reacción fue excelente.
        - En el minuto 5:00, notamos una caída en tu precisión.
        - Recomendación: Practica más en situaciones de alta presión para mejorar tu rendimiento general.
        """)
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(spreadsheet=url, worksheet="Hoja 1")
except:
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- FUNCIÓN NOTIFICACIÓN PUSH ---
def enviar_push(mensaje):
    js = f"<script>if(window.Notification && Notification.permission==='granted'){{new Notification('{mensaje}');}}</script>"
    components.html(js, height=0)

# --- BARRA LATERAL (CONFIGURACIÓN Y REGISTRO) ---
st.sidebar.header("⚙️ Ajustes")
dias_alerta = st.sidebar.slider("Días de anticipación:", 1, 15, 2, key="slider_alerta")

st.sidebar.divider()
st.sidebar.header("📥 Registrar")

# --- SECCIÓN DE LA CÁMARA ---
# 1. Agregamos el interruptor
activar_camara = st.sidebar.checkbox("📷 Activar Cámara", key="toggle_camara")

if activar_camara:
    # 2. Si está activo, mostramos la cámara que ya tenías
    # Usamos el código de tu imagen image_b9f444.png
    foto = st.sidebar.camera_input("Escanear producto", key="camara_unica")
else:
    # 3. Si está desactivado, foto queda vacío
    foto = None
    st.sidebar.info("Cámara apagada.")

# --- EL RESTO DE TU FORMULARIO (Sigue igual que en image_b9f444.png) ---
nombre_prod = st.sidebar.text_input("Nombre del Producto", key="input_nombre")
fecha_p = st.sidebar.date_input("Fecha Producción", key="date_prod")
fecha_v = st.sidebar.date_input("Fecha Vencimiento", key="date_venc")

# --- LECTURA DE DATOS ---
try:
    # Forzamos la lectura de "Hoja 1" y eliminamos el caché para ver siempre lo nuevo
    df = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0) 
except Exception as e:
    st.error(f"Error al leer: {e}")
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- LÓGICA DE GUARDADO ---
if st.sidebar.button("💾 Guardar Producto", key="btn_guardar"):
    if nombre_prod:
        # 1. Crear la nueva fila
        nueva_fila = pd.DataFrame([[nombre_prod, str(fecha_p), str(fecha_v)]], 
                                 columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
        
        # 2. Unir con los datos que acabamos de leer
        df_act = pd.concat([df, nueva_fila], ignore_index=True)
        
        # 3. Actualizar la hoja específica "Hoja 1"
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_act)
        
        st.sidebar.success("¡Guardado correctamente!")
        st.rerun() # Refresca la app para mostrar la lista actualizada

# --- TABLA Y ALERTAS ---
st.title("🍎 Control de Inventario")

if not df.empty:
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'])
    hoy = pd.to_datetime(datetime.now().date())
    limite = hoy + timedelta(days=dias_alerta)
    
    def color_filas(row):
        if row['Vencimiento'] <= hoy: return ['background-color: #ff4b4b'] * len(row)
        if row['Vencimiento'] <= limite: return ['background-color: #ffa500'] * len(row)
        return [''] * len(row)

    st.dataframe(df.style.apply(color_filas, axis=1), use_container_width=True)
    
    criticos = df[df['Vencimiento'] <= limite]
    if not criticos.empty:
        enviar_push(f"Aviso: {len(criticos)} productos cerca de vencer")
else:
    st.info("Inventario vacío.")




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
    df = conn.read(spreadsheet=url)
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

# Aquí corregimos los IDs para que no haya duplicados
foto = st.sidebar.camera_input("Escanear producto", key="camara_unica")
nombre_prod = st.sidebar.text_input("Nombre del Producto", key="input_nombre")
fecha_p = st.sidebar.date_input("Fecha Producción", datetime.now(), key="date_prod")
fecha_v = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), key="date_venc")

if st.sidebar.button("💾 Guardar Producto", key="btn_guardar"):
    if nombre_prod:
        nueva_fila = pd.DataFrame([[nombre_prod, str(fecha_p), str(fecha_v)]], 
                                 columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
        df_act = pd.concat([df, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, data=df_act)
        st.sidebar.success("¡Guardado!")
        st.rerun()

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

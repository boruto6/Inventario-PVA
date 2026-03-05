import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        if "Aviso_Dias" not in df_raw.columns:
            df_raw["Aviso_Dias"] = 7
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN REFORZADA CON SONIDO ---
def enviar_notificacion_externa(mensaje, canal):
    try:
        # Enviamos con prioridad 5 (Máxima) y etiquetas de alerta para forzar sonido
        requests.post(f"https://ntfy.sh/{canal}", 
                      data=mensaje.encode('utf-8'),
                      headers={
                          "Title": "🚨 ALERTA URGENTE: RETIRAR PRODUCTO",
                          "Priority": "5",
                          "Tags": "warning,loud_sound,rotating_light",
                          "Click": url
                      })
    except:
        pass

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Registro")
canal_notif = st.sidebar.text_input("Canal (Celular):", "mi_inventario_privado_123")

nombre_n = st.sidebar.text_input("Nombre del Producto")
f_venc_n = st.sidebar.date_input("Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")
dias_propio = st.sidebar.slider("Aviso (Días):", 1, 30, 7)

if st.sidebar.button("💾 Guardar"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{"Nombre/Codigo": nombre_n, "Vencimiento": f_venc_n.strftime('%d/%m/%Y'), "Aviso_Dias": dias_propio}])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success("Guardado!")
        st.rerun()

# --- CUERPO PRINCIPAL (ALERTAS Y SONIDO) ---
st.title("🍎 Control de Inventario")

hoy = datetime.now().date()
criticos = []

if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            limite = row['Aviso_Dias']
            
            if 0 <= restan <= limite:
                st.warning(f"⚠️ RETIRAR: {row['Nombre/Codigo']} (Faltan {restan} días)")
                criticos.append(row['Nombre/Codigo'])

    # Si hay productos críticos y no hemos notificado en esta sesión, enviamos el sonido
    if criticos and "alerta_enviada" not in st.session_state:
        enviar_notificacion_externa(f"¡Atención! Tienes {len(criticos)} productos por vencer: {', '.join(criticos)}", canal_notif)
        st.session_state.alerta_enviada = True

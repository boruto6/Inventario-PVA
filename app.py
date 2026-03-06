import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN BÁSICA
st.set_page_config(page_title="Inventario Pro", page_icon="🍎")

# --- CONEXIÓN DIRECTA ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # SOLUCIÓN DECIMALES: Forzamos números enteros
        if "Aviso_Dias" in df_raw.columns:
            df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN FORZADA (V5) ---
def enviar_alerta_push(mensaje, canal):
    try:
        # Enviamos con prioridad máxima y sonido fuerte
        res = requests.post(
            f"https://ntfy.sh/{canal}", 
            data=mensaje.encode('utf-8'),
            headers={
                "Title": "🚨 ALERTA DE INVENTARIO",
                "Priority": "5",
                "Tags": "warning,loud_sound"
            },
            timeout=10
        )
        if res.status_code == 200:
            st.success(f"✅ ¡Enviado a ntfy! Revisa tu celular.")
        else:
            st.error(f"❌ Error de servidor: {res.status_code}")
    except Exception as e:
        st.error(f"❌ No se pudo conectar con ntfy: {e}")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración")
canal_notif = st.sidebar.text_input("Canal ntfy:", "mi_inventario_privado_123")

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

if not df.empty:
    hoy = datetime.now().date()
    criticos = []

    # REVISIÓN DE PRODUCTOS (RECUADROS AMARILLOS)
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            limite = row.get('Aviso_Dias', 7)
            
            if 0 <= restan <= limite:
                st.warning(f"⚠️ RETIRAR: {row['Nombre/Codigo']} (Faltan {restan} días)")
                criticos.append(row['Nombre/Codigo'])

    # BOTÓN DE PRUEBA MANUAL
    st.divider()
    if st.button("🔔 PROBAR SONIDO EN CELULAR AHORA"):
        enviar_alerta_push("Prueba de conexión: Si lees esto, el sistema funciona.", canal_notif)

    # ENVÍO AUTOMÁTICO
    if criticos and "notificado_hoy" not in st.session_state:
        enviar_alerta_push(f"Atención: Tienes {len(criticos)} productos por vencer.", canal_notif)
        st.session_state.notificado_hoy = True

    # TABLA LIMPIA
    st.subheader("Lista de Productos")
    df_ver = df.copy()
    df_ver['Vencimiento'] = df_ver['Vencimiento'].dt.strftime('%d/%m/%Y')
    st.write(df_ver[["Nombre/Codigo", "Vencimiento", "Aviso_Dias"]])

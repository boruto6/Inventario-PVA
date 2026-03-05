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

# --- FUNCIÓN DE NOTIFICACIÓN (MÁXIMA PRIORIDAD) ---
def enviar_alerta(mensaje, canal):
    try:
        requests.post(f"https://ntfy.sh/{canal}", 
                      data=mensaje.encode('utf-8'),
                      headers={
                          "Title": "🚨 ALERTA DE VENCIMIENTO",
                          "Priority": "5",
                          "Tags": "warning,loud_sound"
                      })
    except:
        pass

# --- BARRA LATERAL ---
st.sidebar.header("📥 Registro de Producto")
canal_notif = st.sidebar.text_input("Canal ntfy:", "mi_inventario_privado_123")

nombre_n = st.sidebar.text_input("Nombre:")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")
dias_propio = st.sidebar.slider("Días de aviso previo:", 1, 30, 7)

if st.sidebar.button("💾 Guardar Producto"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y'),
            "Aviso_Dias": dias_propio
        }])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        # Formatear fechas como texto antes de subir
        df_save['Produccion'] = pd.to_datetime(df_save['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
        df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success("¡Guardado!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

hoy = datetime.now().date()
criticos = []

if not df.empty:
    # 1. Mostrar Alertas Visuales
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            limite = row['Aviso_Dias']
            
            if 0 <= restan <= limite:
                st.warning(f"⚠️ RETIRAR: {row['Nombre/Codigo']} (Vence en {restan} días)")
                criticos.append(row['Nombre/Codigo'])
            elif restan < 0:
                st.error(f"🚫 CADUCADO: {row['Nombre/Codigo']}")

    # 2. Enviar Notificación de Sonido (solo una vez por apertura)
    if criticos and "notificado_hoy" not in st.session_state:
        enviar_alerta(f"Tienes {len(criticos)} productos próximos a vencer. Revisa la lista.", canal_notif)
        st.session_state.notificado_hoy = True

    # 3. Tablas de Vista
    st.subheader("⏳ Próximos a Vencer")
    df_ver = df.sort_values(by="Vencimiento").head(10).copy()
    df_ver['Vencimiento'] = df_ver['Vencimiento'].dt.strftime('%d/%m/%Y')
    st.table(df_ver[["Nombre/Codigo", "Vencimiento", "Aviso_Dias"]])

# --- SECCIÓN DE BORRADO ---
st.divider()
if not df.empty:
    st.subheader("🗑️ Eliminar Producto")
    prod_borrar = st.selectbox("Selecciona producto:", df['Nombre/Codigo'].tolist())
    if st.button("Eliminar"):
        df_final = df[df['Nombre/Codigo'] != prod_borrar].copy()
        # Formatear antes de subir
        df_final['Produccion'] = pd.to_datetime(df_final['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
        df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.rerun()

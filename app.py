import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Personalizado", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # Asegurar que existan las columnas necesarias
        if "Aviso_Dias" not in df_raw.columns:
            df_raw["Aviso_Dias"] = 7
        
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN ---
def enviar_notificacion(mensaje, canal):
    try:
        requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'))
    except: pass

# --- BARRA LATERAL: REGISTRO CON SLIDER INDEPENDIENTE ---
st.sidebar.header("📥 Registrar Nuevo")

if "camara_on" not in st.session_state:
    st.session_state.camara_on = False

if st.sidebar.button("📷 Alternar Cámara"):
    st.session_state.camara_on = not st.session_state.camara_on
    st.rerun()

if st.session_state.camara_on:
    st.sidebar.camera_input("Capturar", key="cam")

nombre_n = st.sidebar.text_input("Nombre del Producto")
f_prod_n = st.sidebar.date_input("Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")

# AQUÍ DEFINES EL AVISO PARA ESTE PRODUCTO ESPECÍFICO
dias_propio = st.sidebar.slider("Días de aviso para este producto:", 1, 30, 7)

if st.sidebar.button("💾 Guardar"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y'),
            "Aviso_Dias": dias_propio
        }])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        # Convertir a texto para la nube
        df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
        df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success(f"¡{nombre_n} guardado con aviso de {dias_propio} días!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS BASADAS EN EL AVISO INDEPENDIENTE DE CADA FILA
hoy = datetime.now().date()
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            # Usamos el valor guardado en la columna 'Aviso_Dias' para este producto
            limite_aviso = row['Aviso_Dias']
            
            if restan < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {f_venc.strftime('%d/%m/%Y')})")
            elif 0 <= restan <= limite_aviso:
                st.warning(f"⚠️ **RETIRAR PRONTO**: {row['Nombre/Codigo']} (Faltan {restan} días. Configurado para avisar {limite_aviso} días antes)")

# 2. TABLA DE STOCK ACTUAL
st.subheader("📦 Stock Actual")
if not df.empty:
    # Formatear para visualización limpia
    df_ver = df.copy()
    df_ver['Produccion'] = df_ver['Produccion'].dt.strftime('%d/%m/%Y')
    df_ver['Vencimiento'] = df_ver['Vencimiento'].dt.strftime('%d/%m/%Y')
    
    # Mostrar tabla con la columna Aviso_Dias que ahora es distinta para cada uno
    st.table(df_ver[["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"]])

# 3. GESTIÓN (PARA CORREGIR LOS DÍAS DE AVISO SI HAY ERRORES)
st.divider()
st.subheader("🛠️ Corregir Aviso o Datos")
if not df.empty:
    prod_edit = st.selectbox("Seleccionar producto:", df['Nombre/Codigo'].tolist())
    idx = df[df['Nombre/Codigo'] == prod_edit].index[0]
    
    with st.expander("Modificar configuración"):
        nuevo_aviso = st.slider("Cambiar días de aviso:", 1, 30, int(df.at[idx, 'Aviso_Dias']))
        if st.button("Actualizar Configuración"):
            df.at[idx, 'Aviso_Dias'] = nuevo_aviso
            df_save = df.copy()
            df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
            df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
            st.success("¡Configuración actualizada!")
            st.rerun()

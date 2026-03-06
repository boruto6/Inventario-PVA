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
        # CORRECCIÓN 1: Forzar números enteros para evitar el .0000
        if "Aviso_Dias" in df_raw.columns:
            df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df = cargar_datos()

# --- CORRECCIÓN 2: FUNCIÓN DE ENVÍO SIN EMOJIS INTERNOS (Evita el error 'latin-1') ---
def enviar_notificacion_externa(mensaje, canal):
    try:
        # Quitamos emojis del 'data' y 'Title' para que el servidor no lo bloquee
        res = requests.post(
            f"https://ntfy.sh/{canal}", 
            data=mensaje.encode('utf-8'),
            headers={
                "Title": "Alerta de Inventario", 
                "Priority": "5",
                "Tags": "warning,loud_sound"
            },
            timeout=10
        )
        return res.status_code == 200
    except:
        return False

# --- BARRA LATERAL: RECUPERANDO TODAS LAS FUNCIONES ---
st.sidebar.header("⚙️ Configuración y Registro")
canal_notif = st.sidebar.text_input("Canal ntfy:", "mi_inventario_privado_123")

st.sidebar.divider()

# Control de Cámara
if "camara_on" not in st.session_state:
    st.session_state.camara_on = False

if st.sidebar.button("📷 Alternar Cámara"):
    st.session_state.camara_on = not st.session_state.camara_on
    st.rerun()

if st.session_state.camara_on:
    st.sidebar.camera_input("Capturar", key="cam")

# Formulario de Registro
nombre_n = st.sidebar.text_input("Nombre del Producto")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")
dias_propio = st.sidebar.slider("Días de aviso previo:", 1, 30, 7)

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y'),
            "Aviso_Dias": int(dias_propio)
        }])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        # Formatear fechas como texto antes de subir a Sheets
        df_save['Produccion'] = pd.to_datetime(df_save['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
        df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success("¡Registrado con éxito!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS VISUALES (Recuadros Amarillos)
hoy = datetime.now().date()
criticos = []
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            limite = int(row['Aviso_Dias'])
            
            if restan < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} ({f_venc.strftime('%d/%m/%Y')})")
                criticos.append(row['Nombre/Codigo'])
            elif 0 <= restan <= limite:
                st.warning(f"⚠️ **RETIRAR**: {row['Nombre/Codigo']} (Faltan {restan} días)")
                criticos.append(row['Nombre/Codigo'])

    # Botón de Prueba Manual
    st.divider()
    if st.button("🔔 PROBAR SONIDO EN CELULAR"):
        if enviar_notificacion_externa("Prueba de sonido: El sistema esta conectado correctamente", canal_notif):
            st.success("✅ ¡Enviado! Revisa tu celular.")
        else:
            st.error("❌ Error de conexión con ntfy.")

    # Envío automático (Solo una vez por sesión)
    if criticos and "notificado_hoy" not in st.session_state:
        mensaje_push = f"Atencion: Tienes {len(criticos)} productos criticos en el inventario."
        enviar_notificacion_externa(mensaje_push, canal_notif)
        st.session_state.notificado_hoy = True

# 2. BUSCADOR
st.subheader("🔍 Buscador")
busqueda = st.text_input("Filtrar productos por nombre...", "").lower()

# 3. TABLA DE DATOS
if not df.empty:
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()
    st.divider()
    st.subheader("⏳ Lista de Productos")
    df_ver = df_filtrado.copy()
    df_ver['Vencimiento'] = df_ver['Vencimiento'].dt.strftime('%d/%m/%Y')
    # Mostramos la tabla (Aviso_Dias ya es entero por la corrección en la carga)
    st.table(df_ver[["Nombre/Codigo", "Vencimiento", "Aviso_Dias"]])

# 4. GESTIÓN DE BORRADO
st.divider()
if not df.empty:
    st.subheader("🗑️ Eliminar Producto")
    prod_borrar = st.selectbox("Selecciona un producto para eliminar:", df['Nombre/Codigo'].tolist())
    if st.button("Eliminar"):
        df_final = df[df['Nombre/Codigo'] != prod_borrar].copy()
        # Formatear antes de subir
        df_final['Produccion'] = pd.to_datetime(df_final['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
        df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.success(f"Producto {prod_borrar} eliminado.")
        st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN EXTERNA ---
def enviar_notificacion_externa(mensaje, canal):
    try:
        requests.post(f"https://ntfy.sh/{canal}", 
                      data=mensaje.encode('utf-8'),
                      headers={"Title": "Alerta de Inventario 🍎", "Priority": "high"})
    except:
        pass

# --- BARRA LATERAL: CONFIGURACIÓN Y REGISTRO ---
st.sidebar.header("⚙️ Configuración de Alertas")

# Configuración de días de aviso (Editable por el usuario)
dias_aviso = st.sidebar.slider("¿Cuántos días antes avisar?", 1, 90, 7)
canal_notif = st.sidebar.text_input("Canal para notificaciones (Celular):", "mi_inventario_privado_123")

st.sidebar.divider()
st.sidebar.header("📥 Registrar Nuevo")

if "camara_on" not in st.session_state:
    st.session_state.camara_on = False

btn_cam = "🔴 Apagar Cámara" if st.session_state.camara_on else "📷 Activar Cámara"
if st.sidebar.button(btn_cam):
    st.session_state.camara_on = not st.session_state.camara_on
    st.rerun()

if st.session_state.camara_on:
    st.sidebar.camera_input("Capturar Producto", key="cam")

nombre_n = st.sidebar.text_input("Nombre del Producto")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y')
        }])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
        df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success("¡Registrado!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. LÓGICA DE ALERTAS
hoy = datetime.now().date()
criticos = []

if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            if restan < 0 or (0 <= restan <= dias_aviso):
                criticos.append(row['Nombre/Codigo'])
            
            if restan < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} ({f_venc.strftime('%d/%m/%Y')})")
            elif 0 <= restan <= dias_aviso:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Faltan {restan} días)")

    if criticos and "notificado" not in st.session_state:
        msg = f"Atención: Tienes {len(criticos)} productos próximos a vencer (Configuración: {dias_aviso} días)."
        enviar_notificacion_externa(msg, canal_notif)
        st.session_state.notificado = True

# 2. BUSCADOR
st.subheader("🔍 Buscador")
busqueda = st.text_input("Filtrar productos...", "").lower()

# 3. VISTA DE TABLAS
if not df.empty:
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()
    
    st.divider()
    st.subheader(f"⏳ Top 10 Próximos Vencimientos")
    
    # --- PROCESAR TABLA CON COLUMNA DE AVISO ---
    df_venc = df_filtrado.sort_values(by="Vencimiento").head(10).copy()
    
    # Agregamos la columna que pediste (Configuración de aviso)
    df_venc['Aviso (Días)'] = dias_aviso
    
    # Formatear fechas para vista
    df_venc['Produccion'] = df_venc['Produccion'].dt.strftime('%d/%m/%Y')
    df_venc['Vencimiento'] = df_venc['Vencimiento'].dt.strftime('%d/%m/%Y')
    
    # Reordenar columnas para que "Aviso (Días)" sea visible al final
    st.table(df_venc[["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso (Días)"]])

    st.divider()
    st.subheader("🆕 Últimos 2 Agregados")
    df_recientes = df_filtrado.tail(2).copy()
    df_recientes['Aviso (Días)'] = dias_aviso
    df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y')
    df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_recientes, use_container_width=True)

# 4. GESTIÓN DE ERRORES (EDITAR/MODIFICAR)
st.divider()
st.subheader("🛠️ Corregir Errores de Registro")

if not df.empty:
    prod_sel = st.selectbox("Producto con error:", df['Nombre/Codigo'].tolist())
    idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📝 Editar Datos"):
            n_nom = st.text_input("Corregir Nombre", value=df.at[idx, 'Nombre/Codigo'])
            val_venc = df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now()
            n_venc = st.date_input("Corregir Vencimiento", value=val_venc, format="DD/MM/YYYY")
            
            if st.button("Aplicar Corrección"):
                df.at[idx, 'Nombre/Codigo'] = n_nom
                df.at[idx, 'Vencimiento'] = n_venc
                df_save = df.copy()
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡

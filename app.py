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
            # Forzamos formato día-mes-año para evitar los "None" de tu imagen
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN EXTERNA ---
def enviar_notificacion_externa(mensaje, canal):
    try:
        # Servicio gratuito ntfy.sh para notificaciones tipo celular
        requests.post(f"https://ntfy.sh/{canal}", 
                      data=mensaje.encode('utf-8'),
                      headers={"Title": "Alerta de Inventario 🍎", "Priority": "high"})
    except:
        pass

# --- BARRA LATERAL: CONFIGURACIÓN Y REGISTRO ---
st.sidebar.header("⚙️ Configuración")

# Slider para días de aviso (Esto controla la columna que pediste)
dias_aviso = st.sidebar.slider("¿Cuántos días antes avisar?", 1, 90, 7)
canal_notif = st.sidebar.text_input("Canal Notificaciones (Celular):", "mi_inventario_privado_123")

st.sidebar.divider()
st.sidebar.header("📥 Registrar Nuevo")

# Interruptor de Cámara
if "camara_on" not in st.session_state:
    st.session_state.camara_on = False

btn_texto = "🔴 Apagar Cámara" if st.session_state.camara_on else "📷 Activar Cámara"
if st.sidebar.button(btn_texto):
    st.session_state.camara_on = not st.session_state.camara_on
    st.rerun()

if st.session_state.camara_on:
    st.sidebar.camera_input("Capturar", key="cam")

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
        df_final = pd.concat([df, nueva_fila], ignore_index=True)
        # Formatear todo a texto para Google Sheets
        df_final['Produccion'] = pd.to_datetime(df_final['Produccion']).dt.strftime('%d/%m/%Y')
        df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento']).dt.strftime('%d/%m/%Y')
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS VISUALES
hoy = datetime.now().date()
criticos = []

if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            if restan < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} ({f_venc.strftime('%d/%m/%Y')})")
                criticos.append(row['Nombre/Codigo'])
            elif 0 <= restan <= dias_aviso:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Faltan {restan} días)")
                criticos.append(row['Nombre/Codigo'])

    # Enviar notificación push al celular una vez por sesión
    if criticos and "notificado" not in st.session_state:
        enviar_notificacion_externa(f"Revisión necesaria: {len(criticos)} productos próximos a vencer.", canal_notif)
        st.session_state.notificado = True

# 2. BUSCADOR
st.subheader("🔍 Buscador")
busqueda = st.text_input("Escribe el nombre del producto...", "").lower()

# 3. TABLAS DE STOCK (LIMITADAS)
if not df.empty:
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()
    
    st.divider()
    st.subheader(f"⏳ Top 10 Próximos a Vencer")
    
    # Preparar tabla con la columna de Aviso que pediste
    df_venc = df_filtrado.sort_values(by="Vencimiento").head(10).copy()
    df_venc['Aviso (Días)'] = dias_aviso # Nueva columna
    
    # Formatear fechas para que no salga "None"
    df_venc['Produccion'] = df_venc['Produccion'].dt.strftime('%d/%m/%Y').fillna("---")
    df_venc['Vencimiento'] = df_venc['Vencimiento'].dt.strftime('%d/%m/%Y').fillna("---")
    
    # Mostrar tabla principal
    st.table(df_venc[["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso (Días)"]])

    st.divider()
    st.subheader("🆕 Últimos 2 Agregados")
    df_recientes = df_filtrado.tail(2).copy()
    df_recientes['Aviso (Días)'] = dias_aviso
    df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y').fillna("---")
    df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y').fillna("---")
    st.dataframe(df_recientes, use_container_width=True)

# 4. GESTIÓN (CORREGIR ERRORES O ELIMINAR)
st.divider()
st.subheader("🛠️ Gestión de Productos")
if not df.empty:
    prod_sel = st.selectbox("Selecciona un producto para editar o borrar:", df['Nombre/Codigo'].tolist())
    idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
    
    col_ed, col_bo = st.columns(2)
    with col_ed:
        with st.expander("📝 Editar Datos"):
            n_nom = st.text_input("Nuevo Nombre", value=df.at[idx, 'Nombre/Codigo'])
            # Aseguramos que la fecha sea válida para el input
            f_v_val = df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now()
            n_venc = st.date_input("Nuevo Vencimiento", value=f_v_val, format="DD/MM/YYYY")
            
            if st.button("Actualizar Producto"):
                df.at[idx, 'Nombre/Codigo'] = n_nom
                df.at[idx, 'Vencimiento'] = n_venc
                df_save = df.copy()
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Corregido!")
                st.rerun()
                
    with col_bo:
        if st.button("🗑️ Eliminar Producto", type="primary"):
            df_final = df[df['Nombre/Codigo'] != prod_sel].copy()
            df_final['Produccion'] = df_final['Produccion'].dt.strftime('%d/%m/%Y')
            df_final['Vencimiento'] = df_final['Vencimiento'].dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
            st.rerun()

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
        
        # CORRECCIÓN DE LECTURA: Aseguramos que interprete el día primero (DD/MM/YYYY)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df = cargar_datos()

# --- FUNCIÓN DE NOTIFICACIÓN (MEJORADA PARA QUE SUENE) ---
def enviar_notificacion_externa(mensaje, canal):
    try:
        requests.post(f"https://ntfy.sh/{canal}", 
                      data=mensaje.encode('utf-8'),
                      headers={
                          "Title": "🚨 ALERTA DE INVENTARIO",
                          "Priority": "5",
                          "Tags": "warning,loud_sound"
                      })
    except:
        pass

# --- BARRA LATERAL: REGISTRO ---
st.sidebar.header("⚙️ Configuración y Registro")
canal_notif = st.sidebar.text_input("Canal Notificaciones (Celular):", "mi_inventario_privado_123")

st.sidebar.divider()

if "camara_on" not in st.session_state:
    st.session_state.camara_on = False

if st.sidebar.button("📷 Alternar Cámara"):
    st.session_state.camara_on = not st.session_state.camara_on
    st.rerun()

if st.session_state.camara_on:
    st.sidebar.camera_input("Capturar", key="cam")

nombre_n = st.sidebar.text_input("Nombre del Producto")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")
dias_propio = st.sidebar.slider("Días de aviso para este producto:", 1, 30, 7)

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y'),
            "Aviso_Dias": dias_propio
        }])
        df_save = pd.concat([df, nueva_fila], ignore_index=True)
        
        # CORRECCIÓN AL GUARDAR: Forzamos el formato texto DD/MM/YYYY
        df_save['Produccion'] = pd.to_datetime(df_save['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
        df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
        
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
        st.sidebar.success("¡Registrado correctamente!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS
hoy = datetime.now().date()
criticos = []
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            restan = (f_venc - hoy).days
            limite = row['Aviso_Dias']
            if restan < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} ({f_venc.strftime('%d/%m/%Y')})")
                criticos.append(row['Nombre/Codigo'])
            elif 0 <= restan <= limite:
                st.warning(f"⚠️ **RETIRAR**: {row['Nombre/Codigo']} (Faltan {restan} días / Aviso: {limite})")
                criticos.append(row['Nombre/Codigo'])

    if criticos and "notificado" not in st.session_state:
        enviar_notificacion_externa(f"Atención: {len(criticos)} productos requieren revisión inmediata.", canal_notif)
        st.session_state.notificado = True

# 2. BUSCADOR
st.subheader("🔍 Buscador")
busqueda = st.text_input("Filtrar productos...", "").lower()

# 3. TABLAS (TOP 10 Y ÚLTIMOS 2)
if not df.empty:
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()
    st.divider()
    st.subheader("⏳ Top 10 Próximos Vencimientos")
    
    # CORRECCIÓN EN TABLA: Ordenar y luego formatear para evitar errores de visualización
    df_venc = df_filtrado.sort_values(by="Vencimiento").head(10).copy()
    df_venc['Produccion'] = df_venc['Produccion'].dt.strftime('%d/%m/%Y')
    df_venc['Vencimiento'] = df_venc['Vencimiento'].dt.strftime('%d/%m/%Y')
    st.table(df_venc[["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"]])

    st.divider()
    st.subheader("🆕 Últimos 2 Agregados")
    df_recientes = df_filtrado.tail(2).copy()
    df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y')
    df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_recientes[["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"]], use_container_width=True)

# 4. GESTIÓN (EDITAR Y BORRAR)
st.divider()
st.subheader("🛠️ Gestión de Productos")
if not df.empty:
    lista_p = df['Nombre/Codigo'].tolist()
    prod_sel = st.selectbox("Producto para modificar o eliminar:", lista_p)
    idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("📝 Editar"):
            n_n = st.text_input("Nombre", value=df.at[idx, 'Nombre/Codigo'])
            f_v_a = df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now()
            n_v = st.date_input("Vencimiento", value=f_v_a, format="DD/MM/YYYY")
            n_a = st.slider("Días Aviso", 1, 30, int(df.at[idx, 'Aviso_Dias']))
            if st.button("Actualizar"):
                df.at[idx, 'Nombre/Codigo'] = n_n
                df.at[idx, 'Vencimiento'] = n_v
                df.at[idx, 'Aviso_Dias'] = n_a
                df_u = df.copy()
                # CORRECCIÓN AL ACTUALIZAR: Asegurar formato DD/MM/YYYY
                df_u['Produccion'] = pd.to_datetime(df_u['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_u['Vencimiento'] = pd.to_datetime(df_u['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_u)
                st.rerun()
    with c2:
        if st.button(f"Borrar {prod_sel}", type="primary"):
            df_f = df[df['Nombre/Codigo'] != prod_sel].copy()
            # CORRECCIÓN AL BORRAR: Mantener integridad de formato
            df_f['Produccion'] = pd.to_datetime(df_f['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
            df_f['Vencimiento'] = pd.to_datetime(df_f['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_f)
            st.rerun()

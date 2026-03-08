import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS MANTENIDO ---
st.markdown("""
    <style>
    .card-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 8px;
        border: 1px solid #555;
    }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; margin: 0; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    
    .stButton > button {
        background-color: rgba(255,255,255,0.2) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        border-radius: 5px !important;
        padding: 2px 8px !important;
        height: 35px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A DATOS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df = cargar_datos()

def enviar_notificacion_externa(mensaje, canal):
    if not canal: return False
    try:
        headers = {"Title": "Alerta de Inventario", "Priority": "high", "Tags": "warning"}
        response = requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except: return False

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Registro")
    canal_notif = st.text_input("Canal ntfy:", "mi_inventario_privado_123")
    
    if "camara_on" not in st.session_state: st.session_state.camara_on = False
    if st.button("📷 Cámara ON/OFF"):
        st.session_state.camara_on = not st.session_state.camara_on
        st.rerun()
    if st.session_state.camara_on:
        st.camera_input("Captura", key="cam")

    st.divider()
    with st.expander("➕ AÑADIR NUEVO", expanded=True):
        n_nombre = st.text_input("Nombre")
        n_venc = st.date_input("Vencimiento", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Días aviso", 1, 30, 7)
        if st.button("💾 Guardar"):
            if n_nombre:
                nueva_fila = pd.DataFrame([{"Nombre/Codigo": n_nombre, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": n_venc.strftime('%d/%m/%Y'), "Aviso_Dias": n_aviso}])
                df_save = pd.concat([df, nueva_fila], ignore_index=True)
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.rerun()

# --- PANEL PRINCIPAL ---
st.title("🍎 Control de Inventario")

if not df.empty:
    # Cálculos base
    hoy = datetime.now().date()
    df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
    df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(df))
    c2.metric("Vencidos", len(df[df['Dias_Restantes'] < 0]))
    c3.metric("Urgentes", len(df[df['Indice_Urgencia'] <= 0]))

    st.divider()

    # ESTA ES LA LÍNEA QUE FALTABA O ESTABA MAL UBICADA
    tab_p, tab_b, tab_g = st.tabs(["🚀 Prioridad", "🔍 Buscador", "🛠️ Gestión"])

    with tab_p:
        df_p = df.sort_values("Indice_Urgencia")
        for idx, r in df_p.iterrows():
            color = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
            st.markdown(f'<div class="card-container {color}"><p class="t-blanco">{r["Nombre/Codigo"]} (Vence: {r["Vencimiento"].strftime("%d/%m/%Y")})</p></div>', unsafe_allow_html=True)
            col1, col2 = st.columns([4, 1])
            if col2.button("🗑️", key=f"del_{idx}"):
                df_res = df.drop(idx)
                df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                st.rerun()

    with tab_b:
        busq = st.text_input("Buscar...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())].copy()
        if not df_f.empty:
            df_f['Vencimiento'] = df_f['Vencimiento'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_f[["Nombre/Codigo", "Vencimiento", "Aviso_Dias"]], use_container_width=True)

    with tab_g:
        st.subheader("🛠️ Editar Producto")
        p_sel = st.selectbox("Seleccione:", df['Nombre/Codigo'].tolist())
        if p_sel:
            p_idx = df[df['Nombre/Codigo'] == p_sel].index[0]
            with st.form("form_edit"):
                f_nom = st.text_input("Nombre", value=df.at[p_idx, 'Nombre/Codigo'])
                f_ven = st.date_input("Vencimiento", value=df.at[p_idx, 'Vencimiento'])
                f_avi = st.slider("Aviso", 1, 30, int(df.at[p_idx, 'Aviso_Dias']))
                if st.form_submit_button("Actualizar"):
                    df.at[p_idx, 'Nombre/Codigo'] = f_nom
                    df.at[p_idx, 'Vencimiento'] = pd.to_datetime(f_ven)
                    df.at[p_idx, 'Aviso_Dias'] = f_avi
                    df_up = df.copy()
                    df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                    df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_up)
                    st.rerun()

    # Notificaciones al final
    if "ultima_notif" not in st.session_state: st.session_state.ultima_notif = None
    urgentes = df[df['Indice_Urgencia'] <= 0]
    if len(urgentes) > 0 and st.session_state.ultima_notif != datetime.now().date():
        if enviar_notificacion_externa(f"Tienes {len(urgentes)} urgentes", canal_notif):
            st.session_state.ultima_notif = datetime.now().date()
else:
    st.info("Agrega productos para comenzar.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS AJUSTADO (Iconos y Tarjetas) ---
st.markdown("""
    <style>
    .card { 
        padding: 12px; 
        border-radius: 10px; 
        margin-bottom: 5px; 
        border: 1px solid #555;
    }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    
    /* Estilo para botones pequeños y pegados */
    .stButton > button {
        width: 45px !important;
        height: 35px !important;
        padding: 0px !important;
        font-size: 18px !important;
        background-color: rgba(255,255,255,0.2) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        margin-top: 5px;
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

# --- FUNCIÓN DE NOTIFICACIÓN ---
def enviar_notificacion_externa(mensaje, canal):
    if not canal: return False
    try:
        headers = {"Title": "Alerta de Inventario", "Priority": "high", "Tags": "warning"}
        response = requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except: return False

# --- BARRA LATERAL (Añadir productos y Cámara) ---
with st.sidebar:
    st.header("⚙️ Registro y Cámara")
    canal_notif = st.text_input("Canal ntfy:", "mi_inventario_privado_123")
    
    if "camara_on" not in st.session_state: st.session_state.camara_on = False
    if st.button("📷 Cámara ON/OFF", key="btn_cam"):
        st.session_state.camara_on = not st.session_state.camara_on
        st.rerun()
    if st.session_state.camara_on:
        st.camera_input("Captura", key="cam")

    st.divider()
    # ESTA ES LA SECCIÓN QUE HABÍA DESAPARECIDO
    with st.expander("➕ AÑADIR NUEVO PRODUCTO", expanded=True):
        n_nombre = st.text_input("Nombre del producto")
        n_venc = st.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Días de aviso previo", 1, 30, 7)
        if st.button("💾 Guardar en Inventario"):
            if n_nombre:
                nueva_fila = pd.DataFrame([{
                    "Nombre/Codigo": n_nombre, 
                    "Produccion": datetime.now().strftime('%d/%m/%Y'), 
                    "Vencimiento": n_venc.strftime('%d/%m/%Y'), 
                    "Aviso_Dias": n_aviso
                }])
                df_save = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Producto Guardado!")
                st.rerun()

# --- PANEL PRINCIPAL ---
st.title("🍎 Control de Inventario")

if not df.empty:
    hoy = datetime.now().date()
    df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
    df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(df))
    c2.metric("Vencidos", len(df[df['Dias_Restantes'] < 0]))
    c3.metric("Urgentes", len(df[df['Indice_Urgencia'] <= 0]))

    st.divider()

    tab_p, tab_b, tab_g = st.tabs(["🚀 Prioridad", "🔍 Buscador", "🛠️ Gestión"])

    with tab_p:
        df_p = df.sort_values("Indice_Urgencia")
        for idx, r in df_p.iterrows():
            bg = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
            
            # Tarjeta con botones horizontales ajustados
            col_info, col_v, col_t, col_e = st.columns([3, 0.4, 0.4, 0.4])
            
            with col_info:
                st.markdown(f"""
                    <div class="card {bg}">
                        <div class="t-blanco" style="font-size: 1rem;">{r['Nombre/Codigo']}</div>
                        <div class="t-blanco" style="font-size: 0.8rem; opacity: 0.9;">
                            Faltan: {r['Dias_Restantes']} días
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with col_v:
                if st.button("✅", key=f"v_{idx}"):
                    df_res = df.drop(idx)
                    df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                    df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                    st.rerun()
            with col_t:
                if st.button("🗑️", key=f"t_{idx}"):
                    df_res = df.drop(idx)
                    df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                    df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                    st.rerun()
            with col_e:
                edit_mode = st.button("✏️", key=f"e_{idx}")

            if edit_mode:
                with st.expander(f"✏️ Editando: {r['Nombre/Codigo']}", expanded=True):
                    en = st.text_input("Nuevo Nombre", value=r['Nombre/Codigo'], key=f"en_{idx}")
                    ev = st.date_input("Nuevo Vencimiento", value=r['Vencimiento'], key=f"ev_{idx}")
                    ea = st.slider("Nuevo Aviso", 1, 30, int(r['Aviso_Dias']), key=f"ea_{idx}")
                    if st.button("Guardar Cambios", key=f"s_{idx}"):
                        df.at[idx, 'Nombre/Codigo'] = en
                        df.at[idx, 'Vencimiento'] = pd.to_datetime(ev)
                        df.at[idx, 'Aviso_Dias'] = ea
                        df_s = df.copy()
                        df_s['Produccion'] = df_s['Produccion'].dt.strftime('%d/%m/%Y')
                        df_s['Vencimiento'] = df_s['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_s)
                        st.rerun()

    with tab_b:
        busq = st.text_input("Buscar producto...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())]
        st.dataframe(df_f, use_container_width=True)

    with tab_g:
        st.subheader("🛠️ Gestión y Notificaciones")
        p_sel = st.selectbox("Seleccione para modificar:", df['Nombre/Codigo'].tolist())
        if p_sel:
            idx_g = df[df['Nombre/Codigo'] == p_sel].index[0]
            with st.form("form_gestion"):
                st.text_input("Nombre", value=df.at[idx_g, 'Nombre/Codigo'], key="gn")
                st.date_input("Vencimiento", value=df.at[idx_g, 'Vencimiento'], key="gv")
                if st.form_submit_button("Actualizar"):
                    st.info("Utilice el lápiz ✏️ en la pestaña Prioridad para cambios rápidos.")
            
            if st.button("🗑️ Eliminar Definitivamente", type="primary"):
                df_d = df[df['Nombre/Codigo'] != p_sel]
                df_d['Produccion'] = df_d['Produccion'].dt.strftime('%d/%m/%Y')
                df_d['Vencimiento'] = df_d['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_d)
                st.rerun()

        st.divider()
        st.subheader("🔔 Prueba de Alertas")
        if st.button("📣 Enviar Notificación de Prueba"):
            enviar_notificacion_externa("Prueba de sonido activa", canal_notif)
            st.success("Enviado.")

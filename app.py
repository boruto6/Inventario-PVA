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
        min-width: 40px !important;
    }
    
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        height: auto !important;
        padding: 10px !important;
        white-space: normal !important;
        line-height: 1.2 !important;
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

# --- BARRA LATERAL ---
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
    with st.expander("➕ AÑADIR NUEVO PRODUCTO", expanded=True):
        n_nombre = st.text_input("Nombre del producto")
        n_venc = st.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")
        n_aviso = st.slider("Días de aviso previo", 1, 30, 7)
        if st.button("💾 Guardar en Inventario", key="save_sidebar"):
            if n_nombre:
                nueva_fila = pd.DataFrame([{
                    "Nombre/Codigo": n_nombre, 
                    "Produccion": datetime.now().strftime('%d/%m/%Y'), 
                    "Vencimiento": n_venc.strftime('%d/%m/%Y'), 
                    "Aviso_Dias": n_aviso
                }])
                df_save = pd.concat([df, nueva_fila], ignore_index=True)
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
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
            color_class = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
            fecha_venc_str = r['Vencimiento'].strftime('%d/%m/%Y') if pd.notnull(r['Vencimiento']) else "Sin fecha"
            
            st.markdown(f"""
                <div class="card-container {color_class}">
                    <div>
                        <p class="t-blanco" style="font-size: 1.1rem;">{r['Nombre/Codigo']}</p>
                        <p class="t-blanco" style="font-size: 0.85rem; opacity: 0.9;">Vence: {fecha_venc_str} | Faltan: {r['Dias_Restantes']} días</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_spacer, col_btns = st.columns([3, 1])
            with col_btns:
                c_v, c_t, c_e = st.columns(3)
                with c_v:
                    if st.button("✅", key=f"v_{idx}"):
                        df_res = df.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                        st.rerun()
                with c_t:
                    if st.button("🗑️", key=f"t_{idx}"):
                        df_res = df.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                        st.rerun()
                with c_e:
                    # Usamos session_state para controlar qué expander está abierto
                    edit_mode = st.button("✏️", key=f"e_{idx}")

            if edit_mode or st.session_state.get(f"open_{idx}", False):
                st.session_state[f"open_{idx}"] = True
                with st.expander(f"✏️ Editando: {r['Nombre/Codigo']}", expanded=True):
                    en_val = st.text_input("Nombre", value=r['Nombre/Codigo'], key=f"in_n_{idx}")
                    ev_val = st.date_input("Vencimiento", value=r['Vencimiento'], key=f"in_v_{idx}", format="DD/MM/YYYY")
                    ea_val = st.slider("Aviso", 1, 30, int(r['Aviso_Dias']), key=f"in_a_{idx}")
                    
                    col_save, col_cancel = st.columns(2)
                    if col_save.button("Guardar Cambios", key=f"bs_{idx}"):
                        df.at[idx, 'Nombre/Codigo'] = en_val
                        df.at[idx, 'Vencimiento'] = pd.to_datetime(ev_val)
                        df.at[idx, 'Aviso_Dias'] = ea_val
                        df_s = df.copy()
                        df_s['Produccion'] = df_s['Produccion'].dt.strftime('%d/%m/%Y')
                        df_s['Vencimiento'] = df_s['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_s)
                        st.session_state[f"open_{idx}"] = False
                        st.rerun()
                    if col_cancel.button("Cerrar", key=f"bc_{idx}"):
                        st.session_state[f"open_{idx}"] = False
                        st.rerun()

    with tab_b:
        busq = st.text_input("Buscar producto...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())].copy()
        if not df_f.empty:
            df_f['Produccion'] = df_f['Produccion'].dt.strftime('%d/%m/%Y')
            df_f['Vencimiento'] = df_f['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_f, use_container_width=True)

    with tab_g:
        st.subheader("🛠️ Gestión y Notificaciones")
        # CORRECCIÓN GESTIÓN: Aseguramos que el selectbox cargue los datos correctamente
        p_sel = st.selectbox("Seleccione para modificar:", df['Nombre/Codigo'].tolist(), key="sel_g_main")
        
        if p_sel:
            # Obtener datos frescos del producto seleccionado
            producto_data = df[df['Nombre/Codigo'] == p_sel].iloc[0]
            idx_g = producto_data.name
            
            with st.form("form_g_v2"):
                gn_g = st.text_input("Nombre", value=producto_data['Nombre/Codigo'])
                gv_g = st.date_input("Vencimiento", value=producto_data['Vencimiento'], format="DD/MM/YYYY")
                ga_g = st.slider("Días Aviso", 1, 30, int(producto_data['Aviso_Dias']))
                
                if st.form_submit_button("Actualizar Producto"):
                    df.at[idx_g, 'Nombre/Codigo'] = gn_g
                    df.at[idx_g, 'Vencimiento'] = pd.to_datetime(gv_g)
                    df.at[idx_g, 'Aviso_Dias'] = ga_g
                    df_up = df.copy()
                    df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                    df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_up)
                    st.success("¡Actualizado con éxito!")
                    st.rerun()
            
            if st.button("🗑️ Eliminar Definitivamente", type="primary", key="del_g_final"):
                df_d = df.drop(idx_g)
                df_d['Produccion'] = df_d['Produccion'].dt.strftime('%d/%m/%Y')
                df_d['Vencimiento'] = df_d['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_d)
                st.rerun()

        st.divider()
        st.subheader("🔔 Centro de Alertas")
        if st.button("🚀 Enviar Prueba al Celular", key="test_notif_g"):
            enviar_notificacion_externa("Prueba de sonido activa", canal_notif)
            st.success("Enviado.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS PARA VISIBILIDAD EN MODO OSCURO ---
st.markdown("""
    <style>
    .card { padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #555; }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    .seccion-alerta { 
        background-color: rgba(255, 255, 255, 0.05); 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px dashed #888;
        margin-top: 20px;
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
    st.header("⚙️ Configuración")
    canal_notif = st.text_input("Canal ntfy:", "mi_inventario_privado_123")
    
    if "camara_on" not in st.session_state: st.session_state.camara_on = False
    if st.button("📷 Cámara ON/OFF"):
        st.session_state.camara_on = not st.session_state.camara_on
        st.rerun()
    if st.session_state.camara_on:
        st.camera_input("Captura", key="cam")

    st.divider()
    with st.expander("➕ Nuevo Producto", expanded=False):
        n_nombre = st.text_input("Nombre:")
        n_venc = st.date_input("Vencimiento:", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Días de aviso:", 1, 30, 7)
        if st.button("💾 Guardar"):
            if n_nombre:
                nueva_fila = pd.DataFrame([{"Nombre/Codigo": n_nombre, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": n_venc.strftime('%d/%m/%Y'), "Aviso_Dias": n_aviso}])
                df_save = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Guardado!")
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

    # --- PESTAÑAS (Solo 3) ---
    tab_p, tab_b, tab_g = st.tabs(["Prioridad", "Buscador", "Gestión"])

    with tab_p:
        df_p = df.sort_values("Indice_Urgencia")
        for _, r in df_p.iterrows():
            bg = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
            st.markdown(f"""
                <div class="card {bg}">
                    <div class="t-blanco" style="font-size: 1.2rem;">{r['Nombre/Codigo']}</div>
                    <div class="t-blanco" style="font-size: 0.9rem; opacity: 0.9;">
                        Urgencia: {r['Indice_Urgencia']} | Faltan: {r['Dias_Restantes']} días
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with tab_b:
        b = st.text_input("Buscar producto...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(b.lower())]
        st.dataframe(df_f, use_container_width=True)

    with tab_g:
        st.subheader("🛠️ Editar o Eliminar")
        p_sel = st.selectbox("Seleccione producto:", df['Nombre/Codigo'].tolist())
        
        if p_sel:
            idx = df[df['Nombre/Codigo'] == p_sel].index[0]
            with st.form("f_edit_final"):
                en = st.text_input("Nombre", value=df.at[idx, 'Nombre/Codigo'])
                ev = st.date_input("Vencimiento", value=df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now())
                ea = st.slider("Aviso (días)", 1, 30, int(df.at[idx, 'Aviso_Dias']))
                if st.form_submit_button("✅ Actualizar"):
                    df.at[idx, 'Nombre/Codigo'], df.at[idx, 'Vencimiento'], df.at[idx, 'Aviso_Dias'] = en, pd.to_datetime(ev), ea
                    df_u = df.copy()
                    df_u['Produccion'] = df_u['Produccion'].dt.strftime('%d/%m/%Y')
                    df_u['Vencimiento'] = df_u['Vencimiento'].dt.strftime('%d/%m/%Y')
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_u)
                    st.rerun()
            
            if st.button("🗑️ Eliminar Producto", type="primary"):
                df_d = df[df['Nombre/Codigo'] != p_sel]
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_d)
                st.rerun()

        # --- SECCIÓN DE NOTIFICACIONES DENTRO DE GESTIÓN ---
        st.markdown('<div class="seccion-alerta">', unsafe_allow_html=True)
        st.subheader("🔔 Prueba de Alertas")
        st.write(f"Configurado para el canal: `{canal_notif}`")
        if st.button("🚀 Enviar Notificación de Prueba"):
            if enviar_notificacion_externa("Prueba: Sistema de inventario funcionando correctamente.", canal_notif):
                st.success("¡Notificación enviada! Revisa tu celular.")
            else:
                st.error("Error al enviar. Verifica el nombre del canal.")
        st.markdown('</div>', unsafe_allow_html=True)

# Alerta automática una vez por carga
if not df.empty and "avisado" not in st.session_state:
    if len(df[df['Indice_Urgencia'] <= 0]) > 0:
        enviar_notificacion_externa("Atención: Tienes productos urgentes por retirar.", canal_notif)
        st.session_state.avisado = True

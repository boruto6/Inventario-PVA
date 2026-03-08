import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS MEJORADO ---
st.markdown("""
    <style>
    .card { 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        border: 1px solid #555;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    
    /* Estilo para que los botones parezcan iconos limpios dentro de la tarjeta */
    .stButton > button {
        border-radius: 5px;
        padding: 2px 10px;
        background-color: rgba(255,255,255,0.2);
        color: white;
        border: 1px solid rgba(255,255,255,0.4);
    }
    .stButton > button:hover {
        background-color: rgba(255,255,255,0.4);
        border: 1px solid white;
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
            
            # Usamos columnas nativas de Streamlit pero dentro de un contenedor para simular la tarjeta
            with st.container():
                # Fila principal de la tarjeta
                col_txt, col_v, col_t, col_e = st.columns([3, 0.5, 0.5, 0.5])
                
                with col_txt:
                    st.markdown(f"""
                        <div class="card {bg}">
                            <div>
                                <div class="t-blanco" style="font-size: 1.1rem;">{r['Nombre/Codigo']}</div>
                                <div class="t-blanco" style="font-size: 0.85rem; opacity: 0.9;">
                                    Urgencia: {r['Indice_Urgencia']} | Faltan: {r['Dias_Restantes']} días
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                # Botones en horizontal dentro del espacio de la tarjeta
                with col_v:
                    if st.button("✅", key=f"v_{idx}"):
                        df = df.drop(idx)
                        df['Produccion'] = df['Produccion'].dt.strftime('%d/%m/%Y')
                        df['Vencimiento'] = df['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df)
                        st.rerun()
                with col_t:
                    if st.button("🗑️", key=f"t_{idx}"):
                        df = df.drop(idx)
                        df['Produccion'] = df['Produccion'].dt.strftime('%d/%m/%Y')
                        df['Vencimiento'] = df['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df)
                        st.rerun()
                with col_e:
                    edit_mode = st.button("✏️", key=f"e_{idx}")

                if edit_mode:
                    with st.expander(f"Editar: {r['Nombre/Codigo']}", expanded=True):
                        en = st.text_input("Nombre", value=r['Nombre/Codigo'], key=f"en_{idx}")
                        ev = st.date_input("Vencimiento", value=r['Vencimiento'], key=f"ev_{idx}")
                        ea = st.slider("Aviso", 1, 30, int(r['Aviso_Dias']), key=f"ea_{idx}")
                        if st.button("Guardar", key=f"s_{idx}"):
                            df.at[idx, 'Nombre/Codigo'] = en
                            df.at[idx, 'Vencimiento'] = pd.to_datetime(ev)
                            df.at[idx, 'Aviso_Dias'] = ea
                            df['Produccion'] = df['Produccion'].dt.strftime('%d/%m/%Y')
                            df['Vencimiento'] = df['Vencimiento'].dt.strftime('%d/%m/%Y')
                            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df)
                            st.rerun()

    with tab_b:
        busq = st.text_input("Buscar...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())]
        st.dataframe(df_f, use_container_width=True)

    with tab_g:
        st.subheader("🛠️ Gestión de Productos")
        # Selector de productos para edición/borrado tradicional
        p_list = df['Nombre/Codigo'].tolist()
        p_sel = st.selectbox("Seleccione para gestionar:", p_list)
        
        if p_sel:
            sel_idx = df[df['Nombre/Codigo'] == p_sel].index[0]
            with st.form("gestion_completa"):
                g_n = st.text_input("Nombre", value=df.at[sel_idx, 'Nombre/Codigo'])
                g_v = st.date_input("Vencimiento", value=df.at[sel_idx, 'Vencimiento'])
                g_a = st.slider("Días Aviso", 1, 30, int(df.at[sel_idx, 'Aviso_Dias']))
                
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    if st.form_submit_button("✅ Actualizar"):
                        df.at[sel_idx, 'Nombre/Codigo'] = g_n
                        df.at[sel_idx, 'Vencimiento'] = pd.to_datetime(g_v)
                        df.at[sel_idx, 'Aviso_Dias'] = g_a
                        df_up = df.copy()
                        df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                        df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_up)
                        st.rerun()
                with col_g2:
                    # El borrado lo dejamos fuera o como botón de acción del form
                    pass
            
            if st.button("🗑️ Eliminar Producto Seleccionado", type="primary"):
                df_del = df[df['Nombre/Codigo'] != p_sel]
                df_del['Produccion'] = df_del['Produccion'].dt.strftime('%d/%m/%Y')
                df_del['Vencimiento'] = df_del['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_del)
                st.rerun()

        st.divider()
        st.subheader("🔔 Centro de Alertas")
        canal_input = st.text_input("Canal ntfy:", value="mi_inventario_privado_123")
        if st.button("📣 Enviar Prueba"):
            if enviar_notificacion_externa("Prueba de sistema activa", canal_input):
                st.success("Notificación enviada.")
            else:
                st.error("Error de envío.")

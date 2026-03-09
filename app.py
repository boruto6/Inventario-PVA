import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .titulo-grande { font-size: 3rem !important; font-weight: bold; margin-bottom: 20px; }
    .stExpander p { font-size: 1.5rem !important; font-weight: bold !important; }
    .card-container {
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #555;
    }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; margin: 0; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    
    .stButton > button {
        background-color: rgba(128,128,128,0.2) !important;
        border-radius: 5px !important; padding: 2px 8px !important;
        height: 35px !important; min-width: 45px !important; width: 100% !important;
    }
    [data-testid="column"] { min-width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A DATOS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(nombre_hoja):
    try:
        df_raw = conn.read(spreadsheet=url, worksheet=nombre_hoja, ttl=0)
        if df_raw.empty: return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])
        df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df_carnes = cargar_datos("Hoja 1")
df_paste = cargar_datos("Pasteleria")

# --- FUNCIÓN DE NOTIFICACIÓN ---
def enviar_notificacion_externa(mensaje, canal):
    if not canal: return False
    try:
        headers = {"Title": "Alerta de Inventario", "Priority": "high", "Tags": "warning,apple"}
        response = requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except: return False

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Registro")
    canal_notif = st.text_input("Canal ntfy:", "mi_inventario_privado_123")
    cat_destino = st.selectbox("Destino del producto:", ["Carnes y Pescados", "Pastelería"])
    
    with st.expander("➕ NUEVO PRODUCTO", expanded=True):
        n_nombre = st.text_input("Nombre")
        n_venc = st.date_input("Vencimiento", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Aviso previo", 1, 30, 7)
        if st.button("💾 Guardar"):
            if n_nombre:
                hoja = "Hoja 1" if cat_destino == "Carnes y Pescados" else "Pasteleria"
                df_ref = df_carnes if cat_destino == "Carnes y Pescados" else df_paste
                nueva_fila = pd.DataFrame([{"Nombre/Codigo": n_nombre, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": n_venc.strftime('%d/%m/%Y'), "Aviso_Dias": n_aviso}])
                df_final = pd.concat([df_ref, nueva_fila], ignore_index=True)
                df_final['Produccion'] = pd.to_datetime(df_final['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet=hoja, data=df_final)
                st.success("¡Guardado!")
                st.rerun()

# --- PANEL PRINCIPAL ---
st.markdown('<p class="titulo-grande">🍎 Control de Inventario</p>', unsafe_allow_html=True)

def dibujar_seccion(titulo, df_local, nombre_hoja, key_p):
    with st.expander(titulo, expanded=False):
        if df_local.empty:
            st.info("No hay productos registrados.")
            return

        hoy = datetime.now().date()
        df_local['Dias_Restantes'] = df_local['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
        df_local['Indice_Urgencia'] = df_local['Dias_Restantes'] - df_local['Aviso_Dias']

        m1, m2, m3 = st.columns(3)
        m1.metric("Total", len(df_local))
        m2.metric("Vencidos", len(df_local[df_local['Dias_Restantes'] < 0]))
        m3.metric("Urgentes", len(df_local[df_local['Indice_Urgencia'] <= 0]))

        st.divider()
        
        t1, t2, t3 = st.tabs(["🚀 Prioridad", "🔍 Buscador", "🛠️ Gestión"])
        
        with t1:
            for idx, r in df_local.sort_values("Indice_Urgencia").iterrows():
                color = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
                fv = r['Vencimiento'].strftime('%d/%m/%Y') if pd.notnull(r['Vencimiento']) else "S/D"
                
                st.markdown(f'<div class="card-container {color}"><div class="t-blanco">{r["Nombre/Codigo"]}<br><small>Vence: {fv} | Faltan: {r["Dias_Restantes"]} días</small></div></div>', unsafe_allow_html=True)
                
                _, col_btns = st.columns([2, 1.5])
                with col_btns:
                    b1, b2, b3 = st.columns([1,1,1])
                    if b1.button("✅", key=f"ok_{key_p}_{idx}") or b2.button("🗑️", key=f"del_{key_p}_{idx}"):
                        df_res = df_local.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_res)
                        st.rerun()
                    
                    # El lápiz activa el modo edición para este producto específico
                    if b3.button("✏️", key=f"ed_{key_p}_{idx}"):
                        st.session_state[f"edit_mode_{key_p}_{idx}"] = True

                # FORMULARIO DE EDICIÓN "IN SITU" (Aparece justo debajo al tocar el lápiz)
                if st.session_state.get(f"edit_mode_{key_p}_{idx}", False):
                    with st.container():
                        st.markdown("---")
                        st.write(f"**Editando:** {r['Nombre/Codigo']}")
                        new_n = st.text_input("Nombre", value=r['Nombre/Codigo'], key=f"n_{key_p}_{idx}")
                        new_v = st.date_input("Vencimiento", value=r['Vencimiento'], key=f"v_{key_p}_{idx}")
                        new_a = st.slider("Días Aviso", 1, 30, int(r['Aviso_Dias']), key=f"a_{key_p}_{idx}")
                        
                        c_save, c_cancel = st.columns(2)
                        if c_save.button("Guardar Cambios", key=f"save_{key_p}_{idx}"):
                            df_local.at[idx, 'Nombre/Codigo'] = new_n
                            df_local.at[idx, 'Vencimiento'] = pd.to_datetime(new_v)
                            df_local.at[idx, 'Aviso_Dias'] = new_a
                            df_up = df_local.copy()
                            df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                            df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                            conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_up)
                            st.session_state[f"edit_mode_{key_p}_{idx}"] = False
                            st.rerun()
                        if c_cancel.button("Cancelar", key=f"can_{key_p}_{idx}"):
                            st.session_state[f"edit_mode_{key_p}_{idx}"] = False
                            st.rerun()
                        st.markdown("---")

        with t2:
            busq = st.text_input("Filtrar...", key=f"f_{key_p}")
            df_v = df_local[df_local['Nombre/Codigo'].str.lower().str.contains(busq.lower())].copy()
            if not df_v.empty:
                df_v['Vencimiento'] = df_v['Vencimiento'].dt.strftime('%d/%m/%Y')
                df_v['Produccion'] = df_v['Produccion'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_v, use_container_width=True)

        with t3:
            st.write("### 🛠️ Gestión y Notificaciones")
            p_sel = st.selectbox("Elegir producto:", df_local['Nombre/Codigo'].tolist(), key=f"sel_{key_p}")
            
            if p_sel:
                detalles = df_local[df_local['Nombre/Codigo'] == p_sel].iloc[0]
                with st.form(f"form_g_{key_p}"):
                    en = st.text_input("Nombre", value=detalles['Nombre/Codigo'])
                    ev = st.date_input("Vencimiento", value=detalles['Vencimiento'])
                    ea = st.slider("Días Aviso", 1, 30, int(detalles['Aviso_Dias']))
                    if st.form_submit_button("Actualizar Producto"):
                        df_local.at[detalles.name, 'Nombre/Codigo'] = en
                        df_local.at[detalles.name, 'Vencimiento'] = pd.to_datetime(ev)
                        df_local.at[detalles.name, 'Aviso_Dias'] = ea
                        df_up = df_local.copy()
                        df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                        df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_up)
                        st.rerun()

            st.divider()
            if st.button(f"🚀 Probar Notificación ({titulo})", key=f"test_{key_p}"):
                if enviar_notificacion_externa(f"Prueba exitosa en {titulo}", canal_notif):
                    st.success("¡Enviado!")
                else:
                    st.error("Error al enviar.")

# Dibujamos secciones
dibujar_seccion("🥩 Carnes y Pescados 🐟", df_carnes, "Hoja 1", "carnes")
st.write("")
dibujar_seccion("🍰 Pastelería 🥐", df_paste, "Pasteleria", "paste")

# Notificaciones automáticas
if "ultima_notif" not in st.session_state: st.session_state.ultima_notif = None
total_urg = len(df_carnes[df_carnes['Indice_Urgencia'] <= 0]) + len(df_paste[df_paste['Indice_Urgencia'] <= 0])
if total_urg > 0 and st.session_state.ultima_notif != datetime.now().date():
    if enviar_notificacion_externa(f"Alerta: Tienes {total_urg} productos urgentes.", canal_notif):
        st.session_state.ultima_notif = datetime.now().date()

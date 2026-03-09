import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
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
        background-color: rgba(255,255,255,0.2) !important;
        color: white !important; border: 1px solid rgba(255,255,255,0.4) !important;
        border-radius: 5px !important; padding: 2px 8px !important;
        height: 35px !important; min-width: 45px !important; width: 100% !important;
    }
    [data-testid="column"] { min-width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN Y CARGA ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(nombre_hoja):
    try:
        df_raw = conn.read(spreadsheet=url, worksheet=nombre_hoja, ttl=0)
        df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

df_carnes = cargar_datos("Hoja 1")
df_paste = cargar_datos("Pasteleria")

# --- NOTIFICACIONES ---
def enviar_notificacion_externa(mensaje, canal):
    if not canal: return False
    try:
        headers = {"Title": "Alerta Inventario", "Priority": "high", "Tags": "warning"}
        requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'), headers=headers, timeout=10)
        return True
    except: return False

# --- BARRA LATERAL (Registro Independiente) ---
with st.sidebar:
    st.header("⚙️ Registro")
    canal_notif = st.text_input("Canal ntfy:", "mi_inventario_privado_123")
    cat_destino = st.selectbox("Destino del producto:", ["Carnes y Pescados", "Pastelería"])
    
    with st.expander("➕ NUEVO PRODUCTo", expanded=True):
        n_nombre = st.text_input("Nombre")
        n_venc = st.date_input("Vencimiento", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Aviso previo", 1, 30, 7)
        
        if st.button("💾 Guardar"):
            hoja = "Hoja 1" if cat_destino == "Carnes y Pescados" else "Pasteleria"
            df_actual = df_carnes if cat_destino == "Carnes y Pescados" else df_paste
            nueva_fila = pd.DataFrame([{"Nombre/Codigo": n_nombre, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": n_venc.strftime('%d/%m/%Y'), "Aviso_Dias": n_aviso}])
            df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
            df_final['Produccion'] = pd.to_datetime(df_final['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
            df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet=hoja, data=df_final)
            st.success("Guardado!")
            st.rerun()

# --- LÓGICA DE RENDERIZADO ---
def dibujar_seccion(titulo, df_local, nombre_hoja, key_p):
    with st.expander(titulo, expanded=False):
        if df_local.empty:
            st.info("No hay productos en esta categoría.")
            return

        hoy = datetime.now().date()
        df_local['Dias_Restantes'] = df_local['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
        df_local['Indice_Urgencia'] = df_local['Dias_Restantes'] - df_local['Aviso_Dias']

        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(df_local))
        c2.metric("Vencidos", len(df_local[df_local['Dias_Restantes'] < 0]))
        c3.metric("Urgentes", len(df_local[df_local['Indice_Urgencia'] <= 0]))

        t1, t2, t3 = st.tabs(["🚀 Prioridad", "🔍 Buscador", "🛠️ Gestión"])
        
        with t1:
            for idx, r in df_local.sort_values("Indice_Urgencia").iterrows():
                color = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
                st.markdown(f'<div class="card-container {color}"><div class="t-blanco">{r["Nombre/Codigo"]}<br><small>Vence: {r["Vencimiento"].strftime("%d/%m/%Y")} | Faltan: {r["Dias_Restantes"]} días</small></div></div>', unsafe_allow_html=True)
                
                _, col_btns = st.columns([2, 1.5])
                with col_btns:
                    cv, ct, ce = st.columns([1,1,1])
                    if cv.button("✅", key=f"v_{key_p}_{idx}") or ct.button("🗑️", key=f"t_{key_p}_{idx}"):
                        df_res = df_local.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_res)
                        st.rerun()
                    if ce.button("✏️", key=f"e_{key_p}_{idx}"):
                        st.session_state[f"edit_{key_p}_{idx}"] = True

        with t2:
            busq = st.text_input("Buscar...", key=f"b_{key_p}")
            st.dataframe(df_local[df_local['Nombre/Codigo'].str.lower().str.contains(busq.lower())], use_container_width=True)

        with t3:
            p_sel = st.selectbox("Producto:", df_local['Nombre/Codigo'].tolist(), key=f"s_{key_p}")
            if st.button("Eliminar Seleccionado", key=f"del_{key_p}"):
                df_d = df_local[df_local['Nombre/Codigo'] != p_sel]
                df_d['Produccion'] = df_d['Produccion'].dt.strftime('%d/%m/%Y')
                df_d['Vencimiento'] = df_d['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_d)
                st.rerun()

# --- DASHBOARD ---
st.markdown('<p class="titulo-grande">🍎 Control de Inventario</p>', unsafe_allow_html=True)
dibujar_seccion("🥩 Carnes y Pescados 🐟", df_carnes, "Hoja 1", "carnes")
st.write("")
dibujar_seccion("🍰 Pastelería 🥐", df_paste, "Pasteleria", "paste")

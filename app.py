import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN GENERAL DE LA APP
st.set_page_config(page_title="Gestión de Inventario Pro", page_icon="📦", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .seccion-contenedor {
        padding: 20px;
        border-radius: 15px;
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 5px solid #d32f2f;
        margin-bottom: 25px;
    }
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

def enviar_notificacion(mensaje, canal):
    if not canal: return False
    try:
        headers = {"Title": "Aviso de Inventario", "Priority": "high"}
        requests.post(f"https://ntfy.sh/{canal}", data=mensaje.encode('utf-8'), headers=headers, timeout=10)
        return True
    except: return False

# --- TÍTULO PRINCIPAL DE LA APP ---
st.title("📦 Panel de Control de Inventarios")
st.write(f"Fecha actual: {datetime.now().strftime('%d/%m/%Y')}")

# =========================================================
# SECCIÓN 1: CARNES Y PESCADOS 🥩🐟
# =========================================================
with st.container():
    st.markdown('<div class="seccion-contenedor">', unsafe_allow_html=True)
    st.header("🥩 Carnes y Pescados 🐟")
    st.caption("Gestión específica de productos cárnicos y derivados del mar.")
    
    if not df.empty:
        hoy = datetime.now().date()
        df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
        df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
        
        # Métricas rápidas de la tabla
        m1, m2, m3 = st.columns(3)
        m1.metric("Ítems en Carnes", len(df))
        m2.metric("Críticos", len(df[df['Indice_Urgencia'] <= 0]))
        m3.metric("Vencidos", len(df[df['Dias_Restantes'] < 0]))

        # Pestañas internas de la tabla
        t1, t2, t3 = st.tabs(["📋 Lista de Prioridad", "🔍 Buscador", "➕ Añadir/Editar"])

        with t1:
            df_p = df.sort_values("Indice_Urgencia")
            for idx, r in df_p.iterrows():
                color = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
                st.markdown(f"""
                    <div class="card-container {color}">
                        <div>
                            <p class="t-blanco">{r['Nombre/Codigo']}</p>
                            <p class="t-blanco" style="font-size:0.8rem; opacity:0.8;">Vence: {r['Vencimiento'].strftime('%d/%m/%Y')} | Faltan: {r['Dias_Restantes']} días</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botones de acción rápida
                b1, b2, b3, _ = st.columns([0.5, 0.5, 0.5, 5])
                if b1.button("✅", key=f"ok_{idx}"):
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df.drop(idx))
                    st.rerun()
                if b2.button("🗑️", key=f"del_{idx}"):
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df.drop(idx))
                    st.rerun()

        with t2:
            busq = st.text_input("Filtrar Carnes...", key="search_carnes")
            st.dataframe(df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())], use_container_width=True)

        with t3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Nuevo Ingreso")
                new_n = st.text_input("Producto", key="new_n_c")
                new_v = st.date_input("Vencimiento", datetime.now() + timedelta(days=5), key="new_v_c")
                if st.button("Guardar en Carnes", key="btn_save_c"):
                    nueva_fila = pd.DataFrame([{"Nombre/Codigo": new_n, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": new_v.strftime('%d/%m/%Y'), "Aviso_Dias": 3}])
                    df_final = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
                    st.rerun()
            with col_b:
                st.subheader("Cámara")
                if st.checkbox("Activar Cámara para esta sección", key="cam_c"):
                    st.camera_input("Foto de etiqueta", key="camera_carnes")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# (ESPACIO PARA FUTURAS TABLAS)
# Aquí puedes copiar el bloque anterior para Lácteos, etc.
# =========================================================

# --- BARRA LATERAL CONFIG ---
with st.sidebar:
    st.header("⚙️ Configuración Global")
    canal = st.text_input("Canal ntfy:", "mi_almacen_general")
    st.divider()
    st.info("Este panel gestiona todas las secciones del inventario.")

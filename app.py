import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN INICIAL (Debe ser lo primero)
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS REPARADO ---
# Eliminamos la fuerza del fondo claro para dejar que Streamlit use su tema nativo y evitar el conflicto de "pantalla negra"
st.markdown("""
    <style>
    .titulo-grande { 
        font-size: 3rem !important; 
        font-weight: bold; 
        margin-bottom: 20px;
    }
    
    .stExpander p { 
        font-size: 1.5rem !important; 
        font-weight: bold !important; 
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
    
    /* Botones horizontales forzados para móvil y PC */
    .stButton > button {
        background-color: rgba(128,128,128,0.2) !important;
        border-radius: 5px !important; 
        padding: 2px 8px !important;
        height: 35px !important; 
        min-width: 45px !important; 
        width: 100% !important;
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
        # Limpieza básica de datos
        if df_raw.empty: return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])
        df_raw["Aviso_Dias"] = pd.to_numeric(df_raw["Aviso_Dias"], errors='coerce').fillna(7).astype(int)
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except Exception as e:
        st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento", "Aviso_Dias"])

# Cargamos las bases de datos
df_carnes = cargar_datos("Hoja 1")
df_paste = cargar_datos("Pasteleria")

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
                
                nueva_fila = pd.DataFrame([{
                    "Nombre/Codigo": n_nombre, 
                    "Produccion": datetime.now().strftime('%d/%m/%Y'), 
                    "Vencimiento": n_venc.strftime('%d/%m/%Y'), 
                    "Aviso_Dias": n_aviso
                }])
                
                df_final = pd.concat([df_ref, nueva_fila], ignore_index=True)
                # Formatear antes de subir
                df_final['Produccion'] = pd.to_datetime(df_final['Produccion'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_final['Vencimiento'] = pd.to_datetime(df_final['Vencimiento'], dayfirst=True).dt.strftime('%d/%m/%Y')
                
                conn.update(spreadsheet=url, worksheet=hoja, data=df_final)
                st.success("¡Guardado!")
                st.rerun()
            else:
                st.warning("Escribe un nombre")

# --- PANEL PRINCIPAL (Lo que estaba fallando) ---
st.markdown('<p class="titulo-grande">🍎 Control de Inventario</p>', unsafe_allow_html=True)

def dibujar_seccion(titulo, df_local, nombre_hoja, key_p):
    with st.expander(titulo, expanded=False):
        if df_local.empty:
            st.info("No hay productos registrados aquí.")
            return

        hoy = datetime.now().date()
        # Calculamos tiempos
        df_local['Dias_Restantes'] = df_local['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
        df_local['Indice_Urgencia'] = df_local['Dias_Restantes'] - df_local['Aviso_Dias']

        # Métricas
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
                
                st.markdown(f'''
                    <div class="card-container {color}">
                        <div class="t-blanco">
                            {r["Nombre/Codigo"]}<br>
                            <small>Vence: {fv} | Faltan: {r["Dias_Restantes"]} días</small>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Botones corregidos
                _, col_btns = st.columns([2, 1.5])
                with col_btns:
                    b1, b2, b3 = st.columns([1,1,1])
                    if b1.button("✅", key=f"ok_{key_p}_{idx}") or b2.button("🗑️", key=f"del_{key_p}_{idx}"):
                        df_res = df_local.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_res)
                        st.rerun()
                    if b3.button("✏️", key=f"ed_{key_p}_{idx}"):
                        st.info("Usa la pestaña 'Gestión' para editar este producto.")

        with t2:
            busq = st.text_input("Filtrar nombre...", key=f"f_{key_p}")
            df_v = df_local[df_local['Nombre/Codigo'].str.lower().str.contains(busq.lower())].copy()
            if not df_v.empty:
                df_v['Vencimiento'] = df_v['Vencimiento'].dt.strftime('%d/%m/%Y')
                df_v['Produccion'] = df_v['Produccion'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_v, use_container_width=True)

        with t3:
            st.write("### Modificar Producto")
            p_sel = st.selectbox("Elegir producto:", df_local['Nombre/Codigo'].tolist(), key=f"sel_{key_p}")
            if p_sel:
                detalles = df_local[df_local['Nombre/Codigo'] == p_sel].iloc[0]
                with st.form(f"form_{key_p}"):
                    en = st.text_input("Nuevo Nombre", value=detalles['Nombre/Codigo'])
                    ev = st.date_input("Nuevo Vencimiento", value=detalles['Vencimiento'])
                    ea = st.slider("Nuevo Aviso", 1, 30, int(detalles['Aviso_Dias']))
                    if st.form_submit_button("Guardar Cambios"):
                        df_local.at[detalles.name, 'Nombre/Codigo'] = en
                        df_local.at[detalles.name, 'Vencimiento'] = pd.to_datetime(ev)
                        df_local.at[detalles.name, 'Aviso_Dias'] = ea
                        df_up = df_local.copy()
                        df_up['Produccion'] = df_up['Produccion'].dt.strftime('%d/%m/%Y')
                        df_up['Vencimiento'] = df_up['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet=nombre_hoja, data=df_up)
                        st.rerun()

# Dibujamos las categorías
dibujar_seccion("🥩 Carnes y Pescados 🐟", df_carnes, "Hoja 1", "carnes")
st.write("")
dibujar_seccion("🍰 Pastelería 🥐", df_paste, "Pasteleria", "paste")

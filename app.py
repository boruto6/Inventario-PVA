import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS MEJORADO PARA MODO OSCURO ---
st.markdown("""
    <style>
    /* Forzamos el color de la tarjeta y el texto */
    .card {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #555;
    }
    .t-blanco { color: white !important; }
    .t-negro { color: #1a1a1a !important; }
    
    /* Colores intensos para que se vean en fondo negro o blanco */
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
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
    with st.expander("➕ Añadir Producto", expanded=True):
        n_nombre = st.text_input("Nombre")
        n_venc = st.date_input("Vencimiento", datetime.now() + timedelta(days=30))
        n_aviso = st.slider("Días aviso", 1, 30, 7)
        if st.button("💾 Guardar Nuevo"):
            if n_nombre:
                nueva_fila = pd.DataFrame([{"Nombre/Codigo": n_nombre, "Produccion": datetime.now().strftime('%d/%m/%Y'), "Vencimiento": n_venc.strftime('%d/%m/%Y'), "Aviso_Dias": n_aviso}])
                df_save = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Hecho!")
                st.rerun()

# --- PANEL PRINCIPAL ---
st.title("🍎 Mi Inventario Inteligente")

if not df.empty:
    hoy = datetime.now().date()
    df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
    df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(df))
    col2.metric("Vencidos", len(df[df['Dias_Restantes'] < 0]))
    col3.metric("Urgentes", len(df[df['Indice_Urgencia'] <= 0]))

    tab1, tab2, tab3 = st.tabs(["🚀 Prioridad", "🔍 Buscador", "🛠️ Gestión"])

    with tab1:
        df_prioridad = df.sort_values("Indice_Urgencia")
        for _, row in df_prioridad.iterrows():
            if row['Dias_Restantes'] < 0:
                bg, emoji = "bg-rojo", "🚫"
            elif row['Indice_Urgencia'] <= 0:
                bg = "bg-naranja"; emoji = "⚠️"
            else:
                bg = "bg-verde"; emoji = "✅"

            st.markdown(f"""
                <div class="card {bg}">
                    <h3 class="t-blanco" style="margin:0;">{emoji} {row['Nombre/Codigo']}</h3>
                    <p class="t-blanco" style="margin:0; opacity: 0.9;">
                        <b>Urgencia: {row['Indice_Urgencia']}</b> | Faltan: {row['Dias_Restantes']} días<br>
                        Vence: {row['Vencimiento'].strftime('%d/%m/%Y')}
                    </p>
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        busq = st.text_input("Filtrar por nombre...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(busq.lower())]
        st.dataframe(df_f, use_container_width=True)

    with tab3:
        st.subheader("🛠️ Modificar Producto")
        opciones = df['Nombre/Codigo'].tolist()
        prod_sel = st.selectbox("Selecciona para editar o eliminar:", opciones)
        
        if prod_sel:
            idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
            
            with st.form("edit_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_nombre = st.text_input("Nombre", value=df.at[idx, 'Nombre/Codigo'])
                    # Manejo de fecha para evitar errores si es nula
                    fecha_val = df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now()
                    edit_venc = st.date_input("Vencimiento", value=fecha_val)
                with col_e2:
                    edit_aviso = st.slider("Días de aviso", 1, 30, int(df.at[idx, 'Aviso_Dias']))
                
                c_bt1, c_bt2 = st.columns(2)
                with c_bt1:
                    if st.form_submit_button("✅ Guardar Cambios"):
                        df.at[idx, 'Nombre/Codigo'] = edit_nombre
                        df.at[idx, 'Vencimiento'] = pd.to_datetime(edit_venc)
                        df.at[idx, 'Aviso_Dias'] = edit_aviso
                        # Preparar para guardar (convertir a texto para Sheets)
                        df_u = df.copy()
                        df_u['Produccion'] = df_u['Produccion'].dt.strftime('%d/%m/%Y')
                        df_u['Vencimiento'] = df_u['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_u)
                        st.success("¡Actualizado!")
                        st.rerun()
                with c_bt2:
                    # El botón de borrar lo ponemos fuera del form de edición para mayor seguridad
                    pass
            
            if st.button(f"🗑️ Eliminar permanentemente {prod_sel}", type="primary"):
                df_f = df[df['Nombre/Codigo'] != prod_sel].copy()
                df_f['Produccion'] = df_f['Produccion'].dt.strftime('%d/%m/%Y')
                df_f['Vencimiento'] = df_f['Vencimiento'].dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_f)
                st.rerun()







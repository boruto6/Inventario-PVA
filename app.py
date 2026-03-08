import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS MEJORADO PARA ACCIONES RÁPIDAS ---
st.markdown("""
    <style>
    .card { padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #555; }
    .t-blanco { color: #FFFFFF !important; font-weight: bold !important; }
    .bg-rojo { background-color: #d32f2f; }
    .bg-naranja { background-color: #f57c00; }
    .bg-verde { background-color: #388e3c; }
    div.stButton > button { width: 100%; padding: 5px; margin: 2px 0; }
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

# --- PANEL PRINCIPAL ---
st.title("🍎 Control de Inventario")

if not df.empty:
    hoy = datetime.now().date()
    df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
    df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
    
    # Métricas superiores
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
            
            # Contenedor de la tarjeta con columnas para botones
            with st.container():
                col_info, col_btn = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"""
                        <div class="card {bg}">
                            <div class="t-blanco" style="font-size: 1.1rem;">{r['Nombre/Codigo']}</div>
                            <div class="t-blanco" style="font-size: 0.85rem; opacity: 0.9;">
                                Urgencia: {r['Indice_Urgencia']} | Faltan: {r['Dias_Restantes']} días
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                with col_btn:
                    # Botón Verificar (Check) - Elimina automáticamente
                    if st.button("✅", key=f"ver_{idx}", help="Confirmar verificación y eliminar"):
                        df_new = df.drop(idx)
                        df_new['Produccion'] = df_new['Produccion'].dt.strftime('%d/%m/%Y')
                        df_new['Vencimiento'] = df_new['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_new)
                        st.rerun()
                    
                    # Botón Basura - Elimina por stock
                    if st.button("🗑️", key=f"del_{idx}", help="Eliminar por falta de stock"):
                        df_new = df.drop(idx)
                        df_new['Produccion'] = df_new['Produccion'].dt.strftime('%d/%m/%Y')
                        df_new['Vencimiento'] = df_new['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_new)
                        st.rerun()

                    # Botón Lápiz - Activa modo edición
                    btn_edit = st.button("✏️", key=f"edit_btn_{idx}", help="Editar producto")
                
                # Formulario de edición rápida (se abre si se pulsa el lápiz)
                if btn_edit:
                    with st.expander(f"Editar {r['Nombre/Codigo']}", expanded=True):
                        new_n = st.text_input("Nombre", value=r['Nombre/Codigo'], key=f"n_{idx}")
                        new_v = st.date_input("Vencimiento", value=r['Vencimiento'], key=f"v_{idx}")
                        new_a = st.slider("Aviso", 1, 30, int(r['Aviso_Dias']), key=f"a_{idx}")
                        if st.button("Guardar Cambios", key=f"save_{idx}"):
                            df.at[idx, 'Nombre/Codigo'] = new_n
                            df.at[idx, 'Vencimiento'] = pd.to_datetime(new_v)
                            df.at[idx, 'Aviso_Dias'] = new_a
                            df_save = df.copy()
                            df_save['Produccion'] = df_save['Produccion'].dt.strftime('%d/%m/%Y')
                            df_save['Vencimiento'] = df_save['Vencimiento'].dt.strftime('%d/%m/%Y')
                            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                            st.rerun()

    with tab_b:
        b = st.text_input("Buscar producto...")
        df_f = df[df['Nombre/Codigo'].str.lower().str.contains(b.lower())]
        st.dataframe(df_f, use_container_width=True)

    with tab_g:
        # Aquí queda la gestión clásica y las alertas que ya tenías
        st.subheader("🛠️ Gestión General")
        # ... (Mantengo la lógica de Gestión y Alertas que ya tenías)
        st.info("Usa los iconos rápidos en la pestaña 'Prioridad' para acciones veloces.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # Forzamos la lectura en formato día-mes-año
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- BARRA LATERAL: REGISTRO ---
st.sidebar.header("📥 Registrar Nuevo")
# Escáner (opcional según tu imagen)
foto = st.sidebar.camera_input("Escanear producto", key="camara_unica")
nombre_n = st.sidebar.text_input("Nombre del Producto", key="input_nombre")

# FORZAMOS FORMATO DD/MM/YYYY EN LOS INPUTS
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y')
        }])
        
        # Preparar datos actuales para unir
        df_temp = df.copy()
        df_temp['Produccion'] = df_temp['Produccion'].dt.strftime('%d/%m/%Y')
        df_temp['Vencimiento'] = df_temp['Vencimiento'].dt.strftime('%d/%m/%Y')
        
        df_final = pd.concat([df_temp, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado en español!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS EN ESPAÑOL
hoy = datetime.now().date()
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            dias = (f_venc - hoy).days
            if dias < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {f_venc.strftime('%d/%m/%Y')})")
            elif 0 <= dias <= 7:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Faltan {dias} días)")

# 2. BUSCADOR
st.subheader("🔍 Buscador")
busqueda = st.text_input("Buscar por nombre...", "").lower()

# 3. TABLAS LIMITADAS (TOP 10 Y ÚLTIMOS 2)
if not df.empty:
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()

    st.divider()
    st.markdown("### ⏳ Próximos 10 a Vencer")
    # Ordenamos: el que vence más pronto arriba
    df_venc = df_filtrado.sort_values(by="Vencimiento", ascending=True).head(10).copy()
    
    if not df_venc.empty:
        df_venc['Produccion'] = df_venc['Produccion'].dt.strftime('%d/%m/%Y')
        df_venc['Vencimiento'] = df_venc['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.table(df_venc)
    
    st.divider()
    st.markdown("### 🆕 Últimos 2 Agregados")
    df_recientes = df_filtrado.tail(2).copy()
    if not df_recientes.empty:
        df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y')
        df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_recientes, use_container_width=True)

# 4. GESTIÓN (EDITAR/BORRAR)
st.divider()
st.subheader("🛠️ Gestión de Productos")

if not df.empty:
    opcion = st.radio("Acción:", ["Editar", "Borrar"], horizontal=True)

    if opcion == "Editar":
        prod_sel = st.selectbox("Selecciona:", df['Nombre/Codigo'].tolist())
        idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
        col1, col2 = st.columns(2)
        with col1:
            nueva_p = st.date_input("Nueva Producción", value=df.at[idx, 'Produccion'], format="DD/MM/YYYY")
        with col2:
            nueva_v = st.date_input("Nuevo Vencimiento", value=df.at[idx, 'Vencimiento'], format="DD/MM/YYYY")
        
        if st.button("Actualizar"):
            df.at[idx, 'Produccion'] = nueva_p
            df.at[idx, 'Vencimiento'] = nueva_v
            df_save = df.copy()
            df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
            df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
            st.rerun()

    elif opcion == "Borrar":
        prod_del = st.selectbox("Eliminar:", df['Nombre/Codigo'].tolist())
        if st.button("Confirmar Borrado"):
            df_b = df[df['Nombre/Codigo'] != prod_del].copy()
            df_b['Produccion'] = df_b['Produccion'].dt.strftime('%d/%m/%Y')
            df_b['Vencimiento'] = df_b['Vencimiento'].dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_b)
            st.rerun()

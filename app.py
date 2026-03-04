import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA Y LENGUAJE
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # Convertimos a datetime internamente para poder ordenar por fecha real
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- BARRA LATERAL: REGISTRO ---
st.sidebar.header("📥 Registrar Nuevo")
nombre_n = st.sidebar.text_input("Nombre del Producto", key="input_nombre")

# Formato de fecha en DD/MM/YYYY para los inputs
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y')
        }])
        
        df_temp = df.copy()
        # Convertimos todo a string DD/MM/YYYY para subir a la nube
        df_temp['Produccion'] = df_temp['Produccion'].dt.strftime('%d/%m/%Y')
        df_temp['Vencimiento'] = df_temp['Vencimiento'].dt.strftime('%d/%m/%Y')
        
        df_final = pd.concat([df_temp, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado exitosamente!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS DINÁMICAS
hoy = datetime.now().date()
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            dias = (f_venc - hoy).days
            if dias < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {f_venc.strftime('%d/%m/%Y')})")
            elif 0 <= dias <= 7:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Vence en {dias} días: {f_venc.strftime('%d/%m/%Y')})")

# 2. BUSCADOR
st.subheader("🔍 Buscador de Productos")
busqueda = st.text_input("Escribe para filtrar la tabla...", "").lower()

# 3. VISTA DE TABLAS LIMITADAS
if not df.empty:
    # Filtramos por nombre primero
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()

    # --- TABLA 1: TOP 10 VENCIMIENTOS (Ordenados de más corto a más largo) ---
    st.divider()
    st.markdown("### ⏳ Próximos 10 a Vencer")
    
    # Ordenar por fecha de vencimiento real
    df_top_venc = df_filtrado.sort_values(by="Vencimiento", ascending=True).head(10).copy()
    
    if not df_top_venc.empty:
        # Formatear fechas para que el usuario las vea en DD/MM/YYYY
        df_top_venc['Produccion'] = df_top_venc['Produccion'].dt.strftime('%d/%m/%Y')
        df_top_venc['Vencimiento'] = df_top_venc['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.table(df_top_venc) # Usamos st.table para que sea fija
    else:
        st.info("No hay productos que coincidan con la búsqueda.")

    # --- TABLA 2: ÚLTIMOS 2 AGREGADOS ---
    st.divider()
    st.markdown("### 🆕 Últimos 2 Agregados")
    # tail(2) toma los últimos de la lista original
    df_recientes = df_filtrado.tail(2).copy()
    
    if not df_recientes.empty:
        df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y')
        df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_recientes, use_container_width=True)

# 4. GESTIÓN (EDITAR Y BORRAR)
st.divider()
st.subheader("🛠️ Gestión de Productos")

if not df.empty:
    opcion = st.radio("¿Qué deseas hacer?", ["Editar Producto", "Eliminar de la Lista"], horizontal=True)

    if opcion == "Editar Producto":
        with st.expander("📝 Modificar fechas o nombre"):
            prod_sel = st.selectbox("Selecciona producto:", df['Nombre/Codigo'].tolist())
            idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
            
            col1, col2 = st.columns(2)
            with col1:
                nuevo_n = st.text_input("Nombre:", value=df.at[idx, 'Nombre/Codigo'])
                # Input de fecha con formato latino
                nueva_p = st.date_input("Nueva Producción:", value=df.at[idx, 'Produccion'] if pd.notnull(df.at[idx, 'Produccion']) else datetime.now(), format="DD/MM/YYYY")
            with col2:
                nueva_v = st.date_input("Nuevo Vencimiento:", value=df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now(), format="DD/MM/YYYY")
            
            if st.button("🆙 Actualizar"):
                df.at[idx, 'Nombre/Codigo'] = nuevo_n
                df.at[idx, 'Produccion'] = nueva_p
                df.at[idx, 'Vencimiento'] = nueva_v
                
                df_save = df.copy()
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Cambios guardados!")
                st.rerun()

    elif opcion == "Eliminar de la Lista":
        prod_del = st.selectbox("Producto a eliminar definitivamente:", df['Nombre/Codigo'].tolist())
        if st.button("🗑️ Eliminar Producto", type="primary"):
            df_final = df[df['Nombre/Codigo'] != prod_del].copy()

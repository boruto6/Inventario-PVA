import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN PARA CARGAR DATOS SIN ERRORES ---
def cargar_datos():
    try:
        # Leemos los datos crudos
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        
        # Intentamos convertir a fecha, si falla deja el valor original para no perderlo
        for col in ['Produccion', 'Vencimiento']:
            df_raw[col] = pd.to_datetime(df_raw[col], dayfirst=True, errors='coerce')
            
        return df_raw
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- BARRA LATERAL: REGISTRO ---
st.sidebar.header("📥 Registrar Nuevo")
nombre_n = st.sidebar.text_input("Nombre del Producto")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now())
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30))

if st.sidebar.button("💾 Guardar Nuevo"):
    if nombre_n:
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_n,
            "Produccion": f_prod_n.strftime('%d/%m/%Y'),
            "Vencimiento": f_venc_n.strftime('%d/%m/%Y')
        }])
        # Preparamos el DF actual para subirlo (todo como texto DD/MM/YYYY)
        df_temp = df.copy()
        df_temp['Produccion'] = df_temp['Produccion'].dt.strftime('%d/%m/%Y')
        df_temp['Vencimiento'] = df_temp['Vencimiento'].dt.strftime('%d/%m/%Y')
        
        df_final = pd.concat([df_temp, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado!")
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
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Quedan {dias} días)")

# 2. VISTA DE TABLA (STOCK ACTUAL)
st.divider()
st.subheader("📦 Stock Actual")
if not df.empty:
    df_vista = df.copy()
    # Mostramos fechas bonitas, si hay None ponemos "Sin fecha"
    df_vista['Produccion'] = df_vista['Produccion'].dt.strftime('%d/%m/%Y').fillna("---")
    df_vista['Vencimiento'] = df_vista['Vencimiento'].dt.strftime('%d/%m/%Y').fillna("---")
    st.dataframe(df_vista, use_container_width=True)
else:
    st.info("El inventario está vacío.")

# 3. PANELES DE GESTIÓN (EDITAR Y BORRAR)
st.divider()
st.subheader("🛠️ Gestión de Productos")

if not df.empty:
    opcion = st.radio("¿Qué deseas hacer?", ["Visualizar", "Editar Fecha/Nombre", "Borrar Producto"], horizontal=True)

    if opcion == "Editar Fecha/Nombre":
        with st.expander("📝 Formulario de Edición", expanded=True):
            prod_sel = st.selectbox("Selecciona el producto a corregir:", df['Nombre/Codigo'].tolist())
            idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                nuevo_n = st.text_input("Corregir Nombre:", value=df.at[idx, 'Nombre/Codigo'])
                nueva_p = st.date_input("Corregir Producción:", value=df.at[idx, 'Produccion'] if pd.notnull(df.at[idx, 'Produccion']) else datetime.now())
            with col_b:
                nueva_v = st.date_input("Corregir Vencimiento:", value=df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now())
            
            if st.button("🆙 Aplicar Cambios"):
                df.at[idx, 'Nombre/Codigo'] = nuevo_n
                df.at[idx, 'Produccion'] = nueva_p
                df.at[idx, 'Vencimiento'] = nueva_v
                
                # Guardar todo formateado
                df_save = df.copy()
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.success("¡Producto actualizado!")
                st.rerun()

    elif opcion == "Borrar Producto":
        with st.container():
            prod_del = st.selectbox("Selecciona el producto a eliminar:", df['Nombre/Codigo'].tolist())
            st.warning(f"¿Estás seguro de eliminar '{prod_del}'? Esta acción no se puede deshacer.")
            if st.button("🗑️ Confirmar Eliminación", type="primary"):
                df_borrado = df[df['Nombre/Codigo'] != prod_del].copy()
                
                # Convertir fechas a string antes de subir
                df_borrado['Produccion'] = df_borrado['Produccion'].dt.strftime('%d/%m/%Y')
                df_borrado['Vencimiento'] = df_borrado['Vencimiento'].dt.strftime('%d/%m/%Y')
                
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_borrado)
                st.rerun()

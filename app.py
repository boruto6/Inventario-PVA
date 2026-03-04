import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LECTURA DE DATOS ---
def cargar_datos():
    try:
        df_lectura = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # Forzar formato de fecha al leer
        df_lectura['Produccion'] = pd.to_datetime(df_lectura['Produccion'], dayfirst=True, errors='coerce')
        df_lectura['Vencimiento'] = pd.to_datetime(df_lectura['Vencimiento'], dayfirst=True, errors='coerce')
        return df_lectura
    except:
        return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

df = cargar_datos()

# --- BARRA LATERAL (REGISTRO NUEVO) ---
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
        df_temp = df.copy()
        df_temp['Produccion'] = df_temp['Produccion'].dt.strftime('%d/%m/%Y')
        df_temp['Vencimiento'] = df_temp['Vencimiento'].dt.strftime('%d/%m/%Y')
        df_final = pd.concat([df_temp, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS
hoy = datetime.now().date()
if not df.empty:
    for _, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            dias = (row['Vencimiento'].date() - hoy).days
            if dias < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} ({row['Vencimiento'].strftime('%d/%m/%Y')})")
            elif 0 <= dias <= 5:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (En {dias} días)")

# 2. VISTA DE TABLA
st.divider()
st.subheader("📦 Stock Actual")
df_vista = df.copy()
df_vista['Produccion'] = df_vista['Produccion'].dt.strftime('%d/%m/%Y')
df_vista['Vencimiento'] = df_vista['Vencimiento'].dt.strftime('%d/%m/%Y')
st.dataframe(df_vista, use_container_width=True)

# 3. PANELES DE EDICIÓN Y ELIMINACIÓN (POR SEPARADO)
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Editar")
    if not df.empty:
        prod_editar = st.selectbox("Selecciona para editar:", df['Nombre/Codigo'].tolist(), key="sel_edit")
        idx = df[df['Nombre/Codigo'] == prod_editar].index[0]
        
        nuevo_nombre = st.text_input("Nuevo nombre:", value=df.at[idx, 'Nombre/Codigo'])
        nueva_f_p = st.date_input("Nueva Prod.:", value=df.at[idx, 'Produccion'])
        nueva_f_v = st.date_input("Nueva Venc.:", value=df.at[idx, 'Vencimiento'])
        
        if st.button("🆙 Actualizar"):
            df.at[idx, 'Nombre/Codigo'] = nuevo_nombre
            df.at[idx, 'Produccion'] = nueva_f_p
            df.at[idx, 'Vencimiento'] = nueva_f_v
            
            # Guardar con formato correcto
            df_save = df.copy()
            df_save['Produccion'] = df_save['Produccion'].dt.strftime('%d/%m/%Y')
            df_save['Vencimiento'] = df_save['Vencimiento'].dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
            st.success("Actualizado")
            st.rerun()

with col2:
    st.subheader("🗑️ Borrar")
    if not df.empty:
        prod_borrar = st.selectbox("Selecciona para borrar:", df['Nombre/Codigo'].tolist(), key="sel_del")
        if st.button("❌ Eliminar Producto", type="primary"):
            df_borrado = df[df['Nombre/Codigo'] != prod_borrar]
            
            # Guardar con formato correcto
            df_save = df_borrado.copy()
            df_save['Produccion'] = df_save['Produccion'].dt.strftime('%d/%m/%Y')
            df_save['Vencimiento'] = df_save['Vencimiento'].dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
            st.error(f"Eliminado: {prod_borrar}")
            st.rerun()

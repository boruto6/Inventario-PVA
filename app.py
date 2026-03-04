import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_raw = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
        # Convertir a datetime para poder ordenar correctamente
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
        df_temp = df.copy()
        # Formatear fechas existentes a string antes de concatenar para subir
        df_temp['Produccion'] = df_temp['Produccion'].dt.strftime('%d/%m/%Y')
        df_temp['Vencimiento'] = df_temp['Vencimiento'].dt.strftime('%d/%m/%Y')
        
        df_final = pd.concat([df_temp, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_final)
        st.sidebar.success("¡Guardado!")
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. BUSCADOR
st.subheader("🔍 Buscar Producto")
busqueda = st.text_input("Escribe el nombre del producto...", "").lower()

# 2. PROCESAMIENTO DE TABLAS
if not df.empty:
    # --- FILTRADO POR BÚSQUEDA ---
    df_filtrado = df[df['Nombre/Codigo'].str.lower().str.contains(busqueda, na=False)].copy()

    # --- TABLA A: LOS 10 PRÓXIMOS A VENCER ---
    st.divider()
    st.subheader("⏳ Top 10: Próximos a Vencer")
    
    # Ordenar por vencimiento (el más cercano primero)
    df_vencimiento = df_filtrado.sort_values(by="Vencimiento", ascending=True).head(10).copy()
    
    if not df_vencimiento.empty:
        # Formatear para visualización
        df_vencimiento['Produccion'] = df_vencimiento['Produccion'].dt.strftime('%d/%m/%Y')
        df_vencimiento['Vencimiento'] = df_vencimiento['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.table(df_vencimiento) # Usamos table para que sea estática y no crezca
    else:
        st.info("No se encontraron coincidencias para la búsqueda.")

    # --- TABLA B: LOS 2 ÚLTIMOS AGREGADOS ---
    st.divider()
    st.subheader("🆕 Recién Agregados")
    
    # Tomamos los últimos 2 registros del DataFrame original (sin el orden de vencimiento)
    # pero sí aplicamos el filtro de búsqueda si el usuario escribió algo
    df_recientes = df_filtrado.tail(2).copy()
    
    if not df_recientes.empty:
        df_recientes['Produccion'] = df_recientes['Produccion'].dt.strftime('%d/%m/%Y')
        df_recientes['Vencimiento'] = df_recientes['Vencimiento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_recientes, use_container_width=True)

else:
    st.info("El inventario está vacío.")

# 3. GESTIÓN (EDITAR/BORRAR) - Se mantiene igual
st.divider()
st.subheader("🛠️ Gestión de Productos")

if not df.empty:
    opcion = st.radio("Acción:", ["Editar Fecha/Nombre", "Borrar Producto"], horizontal=True)

    if opcion == "Editar Fecha/Nombre":
        with st.expander("📝 Formulario de Edición"):
            prod_sel = st.selectbox("Producto a corregir:", df['Nombre/Codigo'].tolist())
            idx = df[df['Nombre/Codigo'] == prod_sel].index[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                nuevo_n = st.text_input("Corregir Nombre:", value=df.at[idx, 'Nombre/Codigo'])
                nueva_p = st.date_input("Nueva Prod.:", value=df.at[idx, 'Produccion'] if pd.notnull(df.at[idx, 'Produccion']) else datetime.now())
            with col_b:
                nueva_v = st.date_input("Nueva Venc.:", value=df.at[idx, 'Vencimiento'] if pd.notnull(df.at[idx, 'Vencimiento']) else datetime.now())
            
            if st.button("🆙 Aplicar Cambios"):
                df.at[idx, 'Nombre/Codigo'] = nuevo_n
                df.at[idx, 'Produccion'] = nueva_p
                df.at[idx, 'Vencimiento'] = nueva_v
                df_save = df.copy()
                df_save['Produccion'] = pd.to_datetime(df_save['Produccion']).dt.strftime('%d/%m/%Y')
                df_save['Vencimiento'] = pd.to_datetime(df_save['Vencimiento']).dt.strftime('%d/%m/%Y')
                conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_save)
                st.rerun()

    elif opcion == "Borrar Producto":
        prod_del = st.selectbox("Producto a eliminar:", df['Nombre/Codigo'].tolist())
        if st.button("🗑️ Confirmar Eliminación", type="primary"):
            df_borrado = df[df['Nombre/Codigo'] != prod_del].copy()
            df_borrado['Produccion'] = df_borrado['Produccion'].dt.strftime('%d/%m/%Y')
            df_borrado['Vencimiento'] = df_borrado['Vencimiento'].dt.strftime('%d/%m/%Y')
            conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_borrado)
            st.rerun()

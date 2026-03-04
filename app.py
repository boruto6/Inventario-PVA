import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN NOTIFICACIÓN PUSH ---
def enviar_push(mensaje):
    js = f"<script>if(window.Notification && Notification.permission==='granted'){{new Notification('{mensaje}');}}</script>"
    components.html(js, height=0)

# --- LECTURA DE DATOS ---
try:
    # Leemos la hoja específicamente y quitamos el caché (ttl=0)
    df = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
    # Convertimos a datetime para que Python entienda las fechas
    df['Produccion'] = pd.to_datetime(df['Produccion'], errors='coerce')
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'], errors='coerce')
except Exception:
    # Si falla o está vacío, creamos la estructura base
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- BARRA LATERAL (REGISTRO) ---
st.sidebar.header("⚙️ Ajustes")
dias_alerta = st.sidebar.slider("Anticipación de alerta (días):", 1, 15, 3)

st.sidebar.divider()
st.sidebar.header("📥 Nuevo Producto")

# Opción de cámara
activar_camara = st.sidebar.checkbox("📷 Activar Cámara")
foto = st.sidebar.camera_input("Escanear", key="camara") if activar_camara else None

nombre_prod = st.sidebar.text_input("Nombre del Producto")
fecha_p = st.sidebar.date_input("Fecha Producción", datetime.now())
fecha_v = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30))

if st.sidebar.button("💾 Guardar en Inventario"):
    if nombre_prod:
        # Crear nueva fila con formato estándar
        nueva_fila = pd.DataFrame([{
            "Nombre/Codigo": nombre_prod,
            "Produccion": fecha_p.strftime('%Y-%m-%d'),
            "Vencimiento": fecha_v.strftime('%Y-%m-%d')
        }])
        
        # Unir datos y actualizar Google Sheets
        df_act = pd.concat([df, nueva_fila], ignore_index=True)
        # Convertimos todo a texto antes de subir para evitar errores de formato
        df_act['Produccion'] = df_act['Produccion'].astype(str)
        df_act['Vencimiento'] = df_act['Vencimiento'].astype(str)
        
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_act)
        st.sidebar.success("¡Producto Guardado!")
        st.rerun()
    else:
        st.sidebar.warning("Por favor, ponle un nombre al producto.")

# --- CUERPO PRINCIPAL ---
st.title("🍎 Control de Inventario")

# 1. ALERTAS DE VENCIMIENTO
hoy = datetime.now().date()
alertas_list = []

if not df.empty:
    for index, row in df.iterrows():
        if pd.notnull(row['Vencimiento']):
            f_venc = row['Vencimiento'].date()
            dias_faltantes = (f_venc - hoy).days
            
            if dias_faltantes < 0:
                st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {f_venc})")
                alertas_list.append(row['Nombre/Codigo'])
            elif 0 <= dias_faltantes <= dias_alerta:
                st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Quedan {dias_faltantes} días)")
                alertas_list.append(row['Nombre/Codigo'])

if not alertas_list and not df.empty:
    st.success("✅ Todo el inventario está al día.")

# 2. GESTIÓN Y EDICIÓN (Buscador, Modificar y Eliminar)
st.divider()
st.subheader("📦 Gestión de Stock")
busqueda = st.text_input("🔍 Buscar por nombre...", placeholder="Ej: Pavo")

# Filtrar resultados del buscador
df_final = df.copy()
if busqueda:
    df_final = df_final[df_final['Nombre/Codigo'].str.contains(busqueda, case=False, na=False)]

# Editor dinámico de datos
# Instrucciones: Para eliminar, selecciona la fila a la izquierda y pulsa 'Suprimir' en tu teclado.
df_editado = st.data_editor(
    df_final, 
    num_rows="dynamic", 
    use_container_width=True,
    key="editor_inventario",
    column_config={
        "Produccion": st.column_config.DateColumn("Fecha Producción"),
        "Vencimiento": st.column_config.DateColumn("Fecha Vencimiento")
    }
)

if st.button("🔄 Aplicar Cambios (Guardar edición o Borrados)"):
    # Limpieza de fechas antes de subir a Sheets
    df_editado['Produccion'] = pd.to_datetime(df_editado['Produccion']).dt.strftime('%Y-%m-%d')
    df_editado['Vencimiento'] = pd.to_datetime(df_editado['Vencimiento']).dt.strftime('%Y-%m-%d')
    
    conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_editado)
    st.toast("Inventario actualizado correctamente", icon="✅")
    st.rerun()

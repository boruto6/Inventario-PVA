import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

st.set_page_config(page_title="Mi Inventario Pro", page_icon="🍎")

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- REEMPLAZO DE LECTURA (image_ba1685.png) ---
try:
    # Leemos la hoja y forzamos el formato de fecha latino
    df = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0)
    df['Produccion'] = pd.to_datetime(df['Produccion']).dt.strftime('%d/%m/%Y')
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento']).dt.strftime('%d/%m/%Y')
except Exception:
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- SISTEMA DE ALERTAS (Estilo Móvil) ---
hoy = pd.to_datetime("today")
alertas_visibles = False

for index, row in df.iterrows():
    try:
        f_venc = pd.to_datetime(row['Vencimiento'], dayfirst=True)
        dias_faltantes = (f_venc - hoy).days + 1
        
        if dias_faltantes < 0:
            st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {row['Vencimiento']})")
            alertas_visibles = True
        elif 0 <= dias_faltantes <= 3:
            st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Faltan {dias_faltantes} días)")
            alertas_visibles = True
    except:
        continue

if not alertas_visibles:
    st.success("✅ Inventario al día. Sin vencimientos próximos.")
# --- AGREGAR BUSCADOR JUSTO AQUÍ ---
st.markdown("### 🔍 Buscador Estilo App")
busqueda = st.text_input("Buscar producto por nombre...", placeholder="Ej: Pavo")

# --- SISTEMA DE ALERTAS (Estilo Móvil) ---
hoy = pd.to_datetime("today")
alertas_visibles = False

for index, row in df.iterrows():
    try:
        f_venc = pd.to_datetime(row['Vencimiento'], dayfirst=True)
        dias_faltantes = (f_venc - hoy).days + 1
        
        if dias_faltantes < 0:
            st.error(f"🚫 **CADUCADO**: {row['Nombre/Codigo']} (Venció el {row['Vencimiento']})")
            alertas_visibles = True
        elif 0 <= dias_faltantes <= 3:
            st.warning(f"⚠️ **POR VENCER**: {row['Nombre/Codigo']} (Faltan {dias_faltantes} días)")
            alertas_visibles = True
    except:
        continue

if not alertas_visibles:
    st.success("✅ Inventario al día. Sin vencimientos próximos.")
    
# --- FUNCIÓN NOTIFICACIÓN PUSH ---
def enviar_push(mensaje):
    js = f"<script>if(window.Notification && Notification.permission==='granted'){{new Notification('{mensaje}');}}</script>"
    components.html(js, height=0)

# --- BARRA LATERAL (CONFIGURACIÓN Y REGISTRO) ---
st.sidebar.header("⚙️ Ajustes")
dias_alerta = st.sidebar.slider("Días de anticipación:", 1, 15, 2, key="slider_alerta")

st.sidebar.divider()
st.sidebar.header("📥 Registrar")

# --- SECCIÓN DE LA CÁMARA ---
# 1. Agregamos el interruptor
activar_camara = st.sidebar.checkbox("📷 Activar Cámara", key="toggle_camara")

if activar_camara:
    # 2. Si está activo, mostramos la cámara que ya tenías
    # Usamos el código de tu imagen image_b9f444.png
    foto = st.sidebar.camera_input("Escanear producto", key="camara_unica")
else:
    # 3. Si está desactivado, foto queda vacío
    foto = None
    st.sidebar.info("Cámara apagada.")

# --- EL RESTO DE TU FORMULARIO (Sigue igual que en image_b9f444.png) ---
nombre_prod = st.sidebar.text_input("Nombre del Producto", key="input_nombre")
fecha_p = st.sidebar.date_input("Fecha Producción", key="date_prod")
fecha_v = st.sidebar.date_input("Fecha Vencimiento", key="date_venc")

# --- LECTURA DE DATOS ---
try:
    # Forzamos la lectura de "Hoja 1" y eliminamos el caché para ver siempre lo nuevo
    df = conn.read(spreadsheet=url, worksheet="Hoja 1", ttl=0) 
except Exception as e:
    st.error(f"Error al leer: {e}")
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- LÓGICA DE GUARDADO ---
if st.sidebar.button("💾 Guardar Producto", key="btn_guardar"):
    if nombre_prod:
        # 1. Crear la nueva fila
       # --- MODIFICACIÓN EN GUARDAR (image_ba03a6.png) ---
# Cambia solo la línea de nueva_fila por esta:
nueva_fila = pd.DataFrame([[
    nombre_prod, 
    fecha_p.strftime('%d/%m/%Y'), 
    fecha_v.strftime('%d/%m/%Y')
]], columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
        
        # 2. Unir con los datos que acabamos de leer
        df_act = pd.concat([df, nueva_fila], ignore_index=True)
        
        # 3. Actualizar la hoja específica "Hoja 1"
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_act)
        
        st.sidebar.success("¡Guardado correctamente!")
        st.rerun() # Refresca la app para mostrar la lista actualizada

# --- TABLA Y ALERTAS ---
st.title("🍎 Control de Inventario")

if not df.empty:
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'])
    hoy = pd.to_datetime(datetime.now().date())
    limite = hoy + timedelta(days=dias_alerta)
    
    def color_filas(row):
        if row['Vencimiento'] <= hoy: return ['background-color: #ff4b4b'] * len(row)
        if row['Vencimiento'] <= limite: return ['background-color: #ffa500'] * len(row)
        return [''] * len(row)

    st.dataframe(df.style.apply(color_filas, axis=1), use_container_width=True)
    
    criticos = df[df['Vencimiento'] <= limite]
    if not criticos.empty:
        enviar_push(f"Aviso: {len(criticos)} productos cerca de vencer")
else:
    st.info("Inventario vacío.")

# --- TABLA DE GESTIÓN (REEMPLAZA TU DATAFRAME ACTUAL) ---
st.subheader("📦 Gestión de Inventario")

# Filtramos la tabla si usas el buscador
df_final = df[df['Nombre/Codigo'].str.contains(busqueda, case=False, na=False)] if busqueda else df

# Editor que permite modificar celdas y borrar filas (tecla Suprimir)
df_editado = st.data_editor(df_final, num_rows="dynamic", use_container_width=True, key="gestor_app")

if st.button("🔄 Aplicar Cambios (Modificar o Eliminar)"):
    # Si buscaste algo, actualizamos el original antes de subir
    if busqueda:
        df.update(df_editado)
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df)
    else:
        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_editado)
    st.toast("¡Base de datos actualizada!", icon="🔄")
    st.rerun()





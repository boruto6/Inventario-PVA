import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Nombre del archivo donde se guardarán los datos
DB_FILE = "inventario.csv"

# Función para cargar datos
def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# Configuración de la página
st.set_page_config(page_title="Control de Vencimientos", layout="wide")
st.title("🍎 Gestor de Inventario con Alertas")

df = cargar_datos()

# --- SECCIÓN 1: INSERTAR PRODUCTOS ---
with st.sidebar:
    st.header("➕ Nuevo Producto")
    nombre = st.text_input("Nombre o Código")
    f_prod = st.date_input("Fecha de Producción", datetime.now())
    f_venc = st.date_input("Fecha de Vencimiento", datetime.now() + timedelta(days=30))
    
    if st.button("Guardar"):
        nueva_fila = pd.DataFrame([[nombre, f_prod, f_venc]], 
                                 columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
        df = pd.concat([df, nueva_fila], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success("¡Registrado!")

# --- SECCIÓN 2: ALERTAS Y VISUALIZACIÓN ---
st.subheader("📋 Inventario Actual")

if not df.empty:
    # Convertir fechas para poder comparar
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'])
    hoy = datetime.now()
    en_dos_dias = hoy + timedelta(days=2)

    # Función para resaltar filas
    def resaltar_vencimiento(row):
        color = ''
        if row['Vencimiento'] <= hoy:
            color = 'background-color: #ff4b4b; color: white' # Vencido
        elif row['Vencimiento'] <= en_dos_dias:
            color = 'background-color: #ffa500; color: black' # Alerta 2 días
        return [color] * len(row)

    # Mostrar tabla con formato
    st.dataframe(df.style.apply(resaltar_vencimiento, axis=1), use_container_width=True)
    
    # Mostrar alertas críticas
    proximos = df[df['Vencimiento'] <= en_dos_dias]
    if not proximos.empty:
        st.warning(f"⚠️ ¡Atención! Tienes {len(proximos)} productos vencidos o a 2 días de vencer.")
else:
    st.info("Aún no hay productos registrados.")
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Control de Inventario Personalizable", page_icon="🍎")

st.title("🍎 Gestor de Inventario con Alertas Configurables")

# URL de tu Google Sheet
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"

# Establecer conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer datos actuales
try:
    df = conn.read(spreadsheet=url)
except:
    df = pd.DataFrame(columns=["Nombre/Codigo", "Produccion", "Vencimiento"])

# --- CONFIGURACIÓN DE ALERTAS (NUEVO) ---
st.sidebar.header("⚙️ Configuración de Alertas")
dias_alerta = st.sidebar.slider("¿Con cuántos días de anticipación quieres la alerta?", 1, 15, 2)

# --- SECCIÓN DE ENTRADA ---
st.sidebar.divider()
st.sidebar.header("📥 Registrar Producto")

foto = st.sidebar.camera_input("Escanear producto/código")

nombre = st.sidebar.text_input("Nombre o Código del Producto")
f_prod = st.sidebar.date_input("Fecha de Producción", datetime.now())
f_venc = st.sidebar.date_input("Fecha de Vencimiento", datetime.now() + timedelta(days=30))

if st.sidebar.button("💾 Guardar en Inventario"):
    if nombre:
        nueva_fila = pd.DataFrame([[nombre, str(f_prod), str(f_venc)]], 
                                 columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
        df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
        conn.update(spreadsheet=url, data=df_actualizado)
        st.sidebar.success(f"✅ '{nombre}' guardado correctamente")
        st.rerun()
    else:
        st.sidebar.error("⚠️ Por favor escribe un nombre o código")

# --- SECCIÓN DE VISUALIZACIÓN Y ALERTAS ---
st.subheader(f"📋 Productos (Alerta configurada a {dias_alerta} días)")

if not df.empty:
    # Convertir fechas para comparar
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'])
    hoy = pd.to_datetime(datetime.now().date())
    
    # Calculamos el límite basado en lo que elijas en el slider
    limite_alerta = hoy + timedelta(days=dias_alerta)

    # Función para dar color a las filas
    def aplicar_color(row):
        color = ''
        if row['Vencimiento'] <= hoy:
            color = 'background-color: #ff4b4b; color: white' # Rojo: Vencido
        elif row['Vencimiento'] <= limite_alerta:
            color = 'background-color: #ffa500; color: black' # Naranja: Según configuración
        return [color] * len(row)

    # Mostrar la tabla estilizada
    st.dataframe(df.style.apply(aplicar_color, axis=1), use_container_width=True)
    
    # Mensajes de alerta dinámicos
    vencidos = df[df['Vencimiento'] <= hoy]
    por_vencer = df[(df['Vencimiento'] > hoy) & (df['Vencimiento'] <= limite_alerta)]
    
    if not vencidos.empty:
        st.error(f"🚨 Tienes {len(vencidos)} productos VENCIDOS.")
    if not por_vencer.empty:
        st.warning(f"⚠️ Tienes {len(por_vencer)} productos que vencen en {dias_alerta} días o menos.")
else:
    st.info("El inventario está vacío. Usa el menú lateral para agregar productos.")
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

st.set_page_config(page_title="Inventario con Notificaciones", page_icon="🔔")

# --- TRUCO DE NOTIFICACIONES PUSH (JavaScript) ---
def enviar_notificacion_push(mensaje):
    # Este código le pide permiso al navegador y lanza la alerta
    js_code = f"""
    <script>
    function notifyMe() {{
      if (!("Notification" in window)) {{
        alert("Este navegador no soporta notificaciones de escritorio");
      }} else if (Notification.permission === "granted") {{
        new Notification("{mensaje}");
      }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then(function (permission) {{
          if (permission === "granted") {{
            new Notification("{mensaje}");
          }}
        }});
      }}
    }}
    notifyMe();
    </script>
    """
    components.html(js_code, height=0)

# --- CONEXIÓN A GOOGLE SHEETS ---
url = "https://docs.google.com/spreadsheets/d/1i-P14r4Avk21vuLfqskBKcoj_fgscPYTczrn-8w8C08/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(spreadsheet=url)

# --- CONFIGURACIÓN ---
st.sidebar.header("⚙️ Alertas")
dias_alerta = st.sidebar.slider("Avisarme antes de (días):", 1, 15, 2)

# --- REVISIÓN DE VENCIMIENTOS ---
if not df.empty:
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento'])
    hoy = pd.to_datetime(datetime.now().date())
    limite = hoy + timedelta(days=dias_alerta)
    
    criticos = df[(df['Vencimiento'] <= limite) & (df['Vencimiento'] > hoy)]
    
    if not criticos.empty:
        msg = f"⚠️ Tienes {len(criticos)} productos por vencer en {dias_alerta} días."
        st.warning(msg)
        # Lanzamos la notificación al sistema del celular
        enviar_notificacion_push(msg)

# --- RESTO DE TU APP (CÁMARA Y REGISTRO) ---
st.title("🍎 Mi Inventario Inteligente")
foto = st.sidebar.camera_input("Capturar producto")
nombre = st.sidebar.text_input("Nombre/Código")
f_venc = st.sidebar.date_input("Fecha Vencimiento")

if st.sidebar.button("💾 Guardar"):
    nueva_fila = pd.DataFrame([[nombre, str(datetime.now().date()), str(f_venc)]], 
                             columns=["Nombre/Codigo", "Produccion", "Vencimiento"])
    df_act = pd.concat([df, nueva_fila], ignore_index=True)
    conn.update(spreadsheet=url, data=df_act)
    st.success("¡Guardado!")
    st.rerun()

st.dataframe(df, use_container_width=True)
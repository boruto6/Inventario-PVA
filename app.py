# --- BARRA LATERAL: REGISTRO ---
st.sidebar.header("📥 Registrar Nuevo")

# 1. Lógica del Interruptor de Cámara
if "camara_activa" not in st.session_state:
    st.session_state.camara_activa = False  # Por defecto apagada

# Botón para alternar estado
texto_boton = "🔴 Desactivar Cámara" if st.session_state.camara_activa else "📷 Activar Cámara"
if st.sidebar.button(texto_boton):
    st.session_state.camara_activa = not st.session_state.camara_activa
    st.rerun()

# Mostrar cámara solo si está activa
foto = None
if st.session_state.camara_activa:
    foto = st.sidebar.camera_input("Encuadra el producto", key="camara_unica")
    if foto:
        st.sidebar.image(foto, caption="Foto capturada", width=150)

# 2. Campos de texto y fecha (Se mantienen igual)
nombre_n = st.sidebar.text_input("Nombre del Producto", key="input_nombre")
f_prod_n = st.sidebar.date_input("Fecha Producción", datetime.now(), format="DD/MM/YYYY")
f_venc_n = st.sidebar.date_input("Fecha Vencimiento", datetime.now() + timedelta(days=30), format="DD/MM/YYYY")

# ... resto del código del botón Guardar ...

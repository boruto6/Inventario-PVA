import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Pro", page_icon="🍎", layout="wide")

# --- CSS MEJORADO ---
st.markdown("""
    <style>
    .prioridad-alta { border-left: 8px solid #ff4b4b; background-color: #ffe5e5; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
    .prioridad-media { border-left: 8px solid #ffa500; background-color: #fff4e5; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
    .prioridad-baja { border-left: 8px solid #28a745; background-color: #e5f4e9; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
    .texto-pequeno { font-size: 0.85rem; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
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

# --- LÓGICA DE PRIORIDAD ---
if not df.empty:
    hoy = datetime.now().date()
    
    # Calculamos días restantes
    df['Dias_Restantes'] = df['Vencimiento'].dt.date.apply(lambda x: (x - hoy).days if pd.notnull(x) else 999)
    
    # CALCULAMOS EL ÍNDICE DE URGENCIA
    # Si Dias_Restantes < Aviso_Dias, el valor es negativo (Urgente)
    # Entre más negativo sea el número, más prioridad tiene.
    df['Indice_Urgencia'] = df['Dias_Restantes'] - df['Aviso_Dias']
    
    # Ordenamos: Primero los que ya caducaron (Días restantes < 0) 
    # y luego por el Índice de Urgencia más bajo.
    df_priorizado = df.sort_values(by=['Dias_Restantes', 'Indice_Urgencia'], ascending=[True, True])

# --- INTERFAZ ---
st.title("🍎 Control de Inventario Inteligente")

# Métricas rápidas
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total", len(df))
with c2:
    vencidos = len(df[df['Dias_Restantes'] < 0])
    st.metric("Caducados", vencidos)
with c3:
    en_alerta = len(df[(df['Indice_Urgencia'] <= 0) & (df['Dias_Restantes'] >= 0)])
    st.metric("En Alerta (Aviso)", en_alerta)

st.divider()

# --- LISTADO PRIORIZADO ---
st.subheader("🚀 Orden de Retiro Prioritario")
st.caption("Los productos aparecen primero según sus días de aviso y cercanía al vencimiento.")

for _, row in df_priorizado.iterrows():
    # Definir clase visual según urgencia
    if row['Dias_Restantes'] < 0:
        clase = "prioridad-alta"
        estado = "🚫 CADUCADO"
    elif row['Indice_Urgencia'] <= 0:
        clase = "prioridad-media"
        estado = "⚠️ PRIORIDAD DE RETIRO"
    else:
        clase = "prioridad-baja"
        estado = "✅ OK"

    st.markdown(f"""
        <div class="{clase}">
            <strong>{row['Nombre/Codigo']}</strong> | {estado}<br>
            <span class="texto-pequeno">
                Vence: {row['Vencimiento'].strftime('%d/%m/%Y')} | 
                <b>Faltan: {row['Dias_Restantes']} días</b> | 
                Margen configurado: {row['Aviso_Dias']} días
            </span>
        </div>
    """, unsafe_allow_html=True)



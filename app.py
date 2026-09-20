import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Reportes", layout="wide")
st.title("📊 Visualizador de Datos y Reportes")

archivo = st.file_uploader("Sube tu archivo de Excel (.xlsx) o CSV", type=["xlsx", "csv"])

if archivo:
    df = pd.read_excel(archivo) if archivo.name.endswith(".xlsx") else pd.read_csv(archivo)
    
    st.success("¡Archivo cargado con éxito!")
    
    st.subheader("Métricas Generales")
    col1, col2 = st.columns(2)
    col1.metric("Total de Registros (Filas)", len(df))
    col2.metric("Total de Columnas", len(df.columns))
    
    st.subheader("Vista Previa de los Datos")
    st.dataframe(df.head(50), use_container_width=True)
    
    columnas_numericas = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    columnas_texto = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    if columnas_texto and columnas_numericas:
        st.subheader("Generador Rápido de Gráficos")
        col_x = st.selectbox("Eje X (Categoría):", columnas_texto)
        col_y = st.selectbox("Eje Y (Monto / Cantidad):", columnas_numericas)
        
        fig = px.bar(df, x=col_x, y=col_y, title=f"{col_y} por {col_x}")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Por favor, sube un archivo para comenzar a visualizar los datos.")

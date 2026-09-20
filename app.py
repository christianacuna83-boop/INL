import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Contable y de Gestión", layout="wide")
st.title("📊 Panel de Control y Reportes")

# Soporte para xlsx, xlsm y csv
archivo = st.file_uploader("Sube tu archivo de Excel (.xlsx, .xlsm) o CSV", type=["xlsx", "xlsm", "csv"])

if archivo:
    try:
        # Si es un libro de Excel (xlsx o xlsm), listamos todas sus hojas
        if archivo.name.endswith((".xlsx", ".xlsm")):
            excel_file = pd.ExcelFile(archivo)
            hojas = excel_file.sheet_names
            hoja_seleccionada = st.selectbox("📂 Selecciona la hoja a visualizar:", hojas)
            df = pd.read_excel(archivo, sheet_name=hoja_seleccionada)
        else:
            df = pd.read_csv(archivo)

        st.success("¡Datos cargados correctamente!")

        # Tarjetas de resumen
        col1, col2 = st.columns(2)
        col1.metric("Total de Registros", len(df))
        col2.metric("Total de Columnas", len(df.columns))

        # Filtros rápidos si existen columnas de texto
        columnas_texto = df.select_dtypes(include=['object', 'string']).columns.tolist()
        columnas_numericas = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

        if columnas_texto:
            col_filtro = st.sidebar.selectbox("Filtrar por columna:", ["(Sin filtro)"] + columnas_texto)
            if col_filtro != "(Sin filtro)":
                valores_unicos = df[col_filtro].dropna().unique().tolist()
                seleccion = st.sidebar.multiselect(f"Valores en {col_filtro}:", valores_unicos, default=valores_unicos[:10])
                if seleccion:
                    df = df[df[col_filtro].isin(seleccion)]

        # Tabla de datos
        st.subheader("📋 Detalle de la Hoja")
        st.dataframe(df, use_container_width=True)

        # Gráfico interactivo
        if columnas_texto and columnas_numericas:
            st.subheader("📈 Gráfico de Resumen")
            col_x = st.selectbox("Eje X (Categoría):", columnas_texto, key="graf_x")
            col_y = st.selectbox("Eje Y (Monto / Importe):", columnas_numericas, key="graf_y")
            
            fig = px.bar(df, x=col_x, y=col_y, title=f"{col_y} por {col_x}", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error al leer la hoja: {e}")
else:
    st.info("Por favor, sube un archivo para comenzar a analizar la información.")

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Panel de Control y Gestión", layout="wide")
st.title("📊 Panel de Control y Reportes de Gestión")

# Selector de archivo
archivo = st.file_uploader("Sube tu archivo de Excel (.xlsx, .xlsm) o CSV", type=["xlsx", "xlsm", "csv"])

if archivo:
    try:
        # Carga de hojas
        if archivo.name.endswith((".xlsx", ".xlsm")):
            excel_file = pd.ExcelFile(archivo)
            hoja_seleccionada = st.selectbox("📂 Selecciona la hoja a visualizar:", excel_file.sheet_names, index=excel_file.sheet_names.index("Formulario") if "Formulario" in excel_file.sheet_names else 0)
            df = pd.read_excel(archivo, sheet_name=hoja_seleccionada)
        else:
            df = pd.read_csv(archivo)

        # Si los nombres de columnas vienen con "Unnamed", tomamos la primera fila como encabezado
        if any("Unnamed" in str(col) for col in df.columns):
            df.columns = df.iloc[0].fillna("Columna").astype(str)
            df = df.iloc[1:].reset_index(drop=True)

        # Limpiar espacios en los nombres de las columnas
        df.columns = [str(c).strip() for c in df.columns]

        st.sidebar.header("🔍 Filtros de Gestión")

        # Filtros laterales automáticos según las columnas existentes
        df_filtrado = df.copy()

        filtros_posibles = ["Supervisor", "Empleado", "Periodo", "Cliente", "Estado", "Sistema"]
        for f in filtros_posibles:
            if f in df.columns:
                opciones = sorted(list(df[f].dropna().unique().astype(str)))
                seleccion = st.sidebar.multiselect(f"Filtrar por {f}:", opciones, default=[])
                if seleccion:
                    df_filtrado = df_filtrado[df_filtrado[f].astype(str).isin(seleccion)]

        # --- SECCIÓN 1: INDICADORES CLAVE (KPIs) ---
        st.subheader("📌 Indicadores Clave")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        kpi1.metric("Total Tareas / Registros", f"{len(df_filtrado):,}")
        if "Cliente" in df_filtrado.columns:
            kpi2.metric("Clientes Únicos", df_filtrado["Cliente"].nunique())
        if "Empleado" in df_filtrado.columns:
            kpi3.metric("Personal Asignado", df_filtrado["Empleado"].nunique())
        if "Supervisor" in df_filtrado.columns:
            kpi4.metric("Supervisores", df_filtrado["Supervisor"].nunique())

        st.divider()

        # --- SECCIÓN 2: GRÁFICOS DE GESTIÓN ---
        st.subheader("📈 Estado y Distribución de Cargas de Trabajo")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            if "Estado" in df_filtrado.columns:
                df_estado = df_filtrado["Estado"].value_counts().reset_index()
                df_estado.columns = ["Estado", "Cantidad"]
                fig_estado = px.pie(df_estado, names="Estado", values="Cantidad", title="Distribución por Estado de Trabajo", hole=0.4)
                st.plotly_chart(fig_estado, use_container_width=True)
            elif "Tipo" in df_filtrado.columns:
                df_tipo = df_filtrado["Tipo"].value_counts().head(10).reset_index()
                df_tipo.columns = ["Tipo", "Cantidad"]
                fig_tipo = px.bar(df_tipo, x="Cantidad", y="Tipo", orientation='h', title="Top Tareas por Tipo")
                st.plotly_chart(fig_tipo, use_container_width=True)

        with col_g2:
            if "Empleado" in df_filtrado.columns:
                df_emp = df_filtrado["Empleado"].value_counts().reset_index()
                df_emp.columns = ["Empleado", "Tareas"]
                fig_emp = px.bar(df_emp, x="Empleado", y="Tareas", title="Carga de Tareas por Empleado", text_auto=True)
                st.plotly_chart(fig_emp, use_container_width=True)
            elif "Supervisor" in df_filtrado.columns:
                df_sup = df_filtrado["Supervisor"].value_counts().reset_index()
                df_sup.columns = ["Supervisor", "Tareas"]
                fig_sup = px.bar(df_sup, x="Supervisor", y="Tareas", title="Tareas por Supervisor", text_auto=True)
                st.plotly_chart(fig_sup, use_container_width=True)

        # --- SECCIÓN 3: TABLA DETALLADA ---
        st.subheader("📋 Detalle de Tareas Filtradas")
        st.dataframe(df_filtrado, use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando la información: {e}")
else:
    st.info("Por favor, sube tu archivo para generar el panel de control.")

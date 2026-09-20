import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Panel de Control - Grado de Avance", layout="wide")
st.title("📊 Panel de Control y Reportes de Gestión")

# Selector de archivo
archivo = st.file_uploader("Sube tu archivo de Excel (.xlsx, .xlsm) o CSV", type=["xlsx", "xlsm", "csv"])

if archivo:
    try:
        # Carga de hojas
        if archivo.name.endswith((".xlsx", ".xlsm")):
            excel_file = pd.ExcelFile(archivo)
            hoja_defecto = "Formulario" if "Formulario" in excel_file.sheet_names else excel_file.sheet_names[0]
            hoja = st.sidebar.selectbox("📂 Hoja de trabajo:", excel_file.sheet_names, index=excel_file.sheet_names.index(hoja_defecto))
            df = pd.read_excel(archivo, sheet_name=hoja)
        else:
            df = pd.read_csv(archivo)

        # Si los nombres de columnas vienen con "Unnamed", tomamos la primera fila como encabezado
        if any("Unnamed" in str(col) for col in df.columns):
            df.columns = df.iloc[0].fillna("Columna").astype(str)
            df = df.iloc[1:].reset_index(drop=True)

        df.columns = [str(c).strip() for c in df.columns]

        # Evitar columnas duplicadas añadiendo un sufijo automático
        columnas_unicas = []
        contador = {}
        for col in df.columns:
            if col in contador:
                contador[col] += 1
                columnas_unicas.append(f"{col}_{contador[col]}")
            else:
                contador[col] = 0
                columnas_unicas.append(col)
        df.columns = columnas_unicas

        # FILTRO PRINCIPAL: Solo registros donde Reporte sea 'Si' o 'SI'
        col_rep = next((c for c in df.columns if c.lower() == "reporte"), None)
        if col_rep:
            df = df[df[col_rep].astype(str).str.strip().str.lower().isin(["si", "sí"])]

        # Filtros laterales opcionales
        st.sidebar.header("🔍 Filtros de Gestión")
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

        # Identificar columnas de puntajes
        col_req = next((c for c in ["Puntaje requerido acumulado", "Puntaje requerido"] if c in df_filtrado.columns), None)
        cols_po = [c for c in df_filtrado.columns if c.startswith("PO ")]
        col_po = cols_po[-1] if cols_po else None

        if cols_po:
            col_po = st.sidebar.selectbox("Periodo a evaluar (Puntaje Obtenido):", cols_po, index=len(cols_po)-1)

        if col_req:
            df_filtrado[col_req] = pd.to_numeric(df_filtrado[col_req], errors="coerce").fillna(0)
        if col_po:
            df_filtrado[col_po] = pd.to_numeric(df_filtrado[col_po], errors="coerce").fillna(0)

        # --- SECCIÓN 2: DONA Y TACÓMETRO (VELOCÍMETRO) ---
        col_sup1, col_sup2 = st.columns([1, 1])

        with col_sup1:
            col_sector = next((c for c in ["SECTOR", "Sector", "Regimen", "Sistema"] if c in df_filtrado.columns), None)
            if col_sector:
                df_sec = df_filtrado[col_sector].value_counts().reset_index()
                df_sec.columns = ["Sector", "Cantidad"]
                fig_dona = px.pie(
                    df_sec, names="Sector", values="Cantidad",
                    hole=0.55, title="Distribución por Sector / Régimen",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_dona.update_traces(textinfo="label+value", textposition="outside")
                fig_dona.update_layout(showlegend=False, margin=dict(t=50, b=30, l=30, r=30))
                st.plotly_chart(fig_dona, use_container_width=True)

        with col_sup2:
            if col_req and col_po and df_filtrado[col_req].sum() > 0:
                total_req = df_filtrado[col_req].sum()
                total_po = df_filtrado[col_po].sum()
                porcentaje_global = (total_po / total_req) * 100

                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=round(porcentaje_global, 1),
                    number={'suffix': "%", 'font': {'size': 36}},
                    title={'text': f"<b>Grado de Avance Global</b><br><span style='font-size:14px;color:gray'>{total_po:,.0f} de {total_req:,.0f} pts</span>"},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': "#1e293b", 'thickness': 0.25},
                        'steps': [
                            {'range': [0, 60], 'color': '#ef4444'},
                            {'range': [60, 80], 'color': '#facc15'},
                            {'range': [80, 100], 'color': '#22c55e'}
                        ],
                    }
                ))
                fig_gauge.update_layout(margin=dict(t=50, b=30, l=30, r=30), height=350)
                st.plotly_chart(fig_gauge, use_container_width=True)

        st.divider()

        # --- SECCIÓN 3: BARRAS HORIZONTALES (ALCANZADO VS REQUERIDO) ---
        def graficar_barras_avance(grupo_col, titulo):
            if grupo_col not in df_filtrado.columns or not col_req or not col_po:
                return None
            resumen = df_filtrado.groupby(grupo_col)[[col_req, col_po]].sum().reset_index()
            resumen["Porcentaje"] = (resumen[col_po] / resumen[col_req] * 100).fillna(0).round(1)
            resumen = resumen.sort_values(by=col_po, ascending=True)

            fig = go.Figure()
            # Barra Requerido (naranja)
            fig.add_trace(go.Bar(
                y=resumen[grupo_col],
                x=resumen[col_req],
                name="Puntaje requerido",
                orientation='h',
                marker_color='#f97316',
                opacity=0.85
            ))
            # Barra Alcanzado (azul)
            fig.add_trace(go.Bar(
                y=resumen[grupo_col],
                x=resumen[col_po],
                name="Puntaje alcanzado",
                orientation='h',
                marker_color='#38bdf8',
                text=[f"{p}%" for p in resumen["Porcentaje"]],
                textposition='inside'
            ))
            fig.update_layout(
                barmode='overlay',
                title=f"<b>{titulo}</b>",
                margin=dict(t=40, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=400
            )
            return fig

        col_inf1, col_inf2 = st.columns([1.2, 1])

        with col_inf1:
            fig_emp = graficar_barras_avance("Empleado", "Grado de avance por contador")
            if fig_emp:
                st.plotly_chart(fig_emp, use_container_width=True)

        with col_inf2:
            fig_sup = graficar_barras_avance("Supervisor", "Grado de avance por Manager")
            if fig_sup:
                st.plotly_chart(fig_sup, use_container_width=True)

            col_empresa = next((c for c in ["SECTOR", "Sector"] if c in df_filtrado.columns), None)
            if col_empresa:
                fig_sec = graficar_barras_avance(col_empresa, "Grado de avance por tipo de empresa")
                if fig_sec:
                    st.plotly_chart(fig_sec, use_container_width=True)

        # --- SECCIÓN 4: TABLA DETALLADA ---
        st.subheader("📋 Detalle de Tareas Filtradas")
        st.dataframe(df_filtrado, use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando la información: {e}")
else:
    st.info("Por favor, sube tu archivo para generar el panel de control.")

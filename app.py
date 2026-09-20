import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Panel de Control - Grado de Avance", layout="wide")
st.title("📊 Panel de Control y Reportes de Gestión")

# Selector de archivo
archivo = st.file_uploader("Sube tu archivo de Excel (.xlsx, .xlsm) o CSV", type=["xlsx", "xlsm", "csv"])
if not archivo:
    archivo = "Estudio contable - Control de tareas 2026-06 Nuevo.xlsx"  # Pon aquí el nombre exacto de tu archivo en GitHub

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

        # Manejo de nombres repetidos guardando orden original
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

        # FILTRO OBLIGATORIO: Solo filas donde Reporte == 'Si' o 'SI'
        col_rep = next((c for c in df.columns if c.lower().startswith("reporte")), None)
        if col_rep:
            df = df[df[col_rep].astype(str).str.strip().str.lower().isin(["si", "sí"])]

        # Identificar la columna de avance: el último "2026-08" (o variantes generadas por duplicados)
        cols_periodo = [c for c in df.columns if "2026-08" in c and not c.startswith("PO")]
        col_avance_mes = cols_periodo[-1] if cols_periodo else None

        # Identificar la columna requerida acumulada
        col_req = next((c for c in df.columns if "puntaje requerido acumulado" in c.lower()), None)
        if not col_req:
            col_req = next((c for c in df.columns if "puntaje requerido" in c.lower()), None)

        # Convertir ambas a números
        if col_avance_mes:
            df[col_avance_mes] = pd.to_numeric(df[col_avance_mes], errors="coerce").fillna(0)
        if col_req:
            df[col_req] = pd.to_numeric(df[col_req], errors="coerce").fillna(0)

        # Filtros laterales opcionales
        st.sidebar.header("🔍 Filtros de Gestión")
        df_filtrado = df.copy()

        filtros_posibles = ["Supervisor", "Empleado", "Periodo", "Cliente", "Estado", "Sistema"]
        for f in filtros_posibles:
            col_f = next((c for c in df.columns if c.lower() == f.lower()), None)
            if col_f:
                opciones = sorted(list(df[col_f].dropna().unique().astype(str)))
                seleccion = st.sidebar.multiselect(f"Filtrar por {f}:", opciones, default=[])
                if seleccion:
                    df_filtrado = df_filtrado[df_filtrado[col_f].astype(str).isin(seleccion)]

        # --- SECCIÓN 1: INDICADORES CLAVE (KPIs) ---
        st.subheader("📌 Indicadores Clave")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        col_cli = next((c for c in df_filtrado.columns if c.lower() == "cliente"), None)
        col_emp = next((c for c in df_filtrado.columns if c.lower() == "empleado"), None)
        col_sup = next((c for c in df_filtrado.columns if c.lower() == "supervisor"), None)

        kpi1.metric("Total Tareas / Registros", f"{len(df_filtrado):,}")
        kpi2.metric("Clientes Únicos", df_filtrado[col_cli].nunique() if col_cli else "-")
        kpi3.metric("Personal Asignado", df_filtrado[col_emp].nunique() if col_emp else "-")
        kpi4.metric("Supervisores", df_filtrado[col_sup].nunique() if col_sup else "-")

        st.divider()

        # --- SECCIÓN 2: DONAS (SECTOR Y RÉGIMEN TRIBUTARIO) Y VELOCÍMETRO ---
        col_sup1, col_sup2, col_sup3 = st.columns([1, 1, 1.2])

        # 1. DONA: Sector (Empresas Únicas)
        with col_sup1:
            col_sector = next((c for c in df_filtrado.columns if c.strip().upper() == "SECTOR"), None)
            if not col_sector:
                col_sector = next((c for c in df_filtrado.columns if "sector" in c.lower()), None)

            if col_sector and col_cli:
                df_unicos_sec = df_filtrado[[col_cli, col_sector]].dropna().drop_duplicates(subset=[col_cli])
                df_sec = df_unicos_sec[col_sector].value_counts().reset_index()
                df_sec.columns = ["Sector", "Cantidad"]

                fig_dona_sec = px.pie(
                    df_sec, names="Sector", values="Cantidad",
                    hole=0.55, title="<b>Distribución por Sector</b><br><span style='font-size:12px;color:gray'>Empresas Únicas</span>",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_dona_sec.update_traces(textinfo="label+value", textposition="outside")
                fig_dona_sec.update_layout(showlegend=False, margin=dict(t=50, b=20, l=20, r=20))
                st.plotly_chart(fig_dona_sec, use_container_width=True)

        # 2. DONA: Régimen Tributario (Empresas Únicas)
        with col_sup2:
            # Busca columnas con nombres como Regimen, Tributario, Tipo Empresa, Sistema, etc.
            col_regimen = next((c for c in df_filtrado.columns if any(k in c.lower() for k in ["regimen", "tribut", "tipo empresa", "clasificacion", "subsector"])), None)
            
            # Si no la encuentra con esos nombres, busca cualquier columna que contenga Mype, General, RER, etc.
            if not col_regimen:
                for c in df_filtrado.columns:
                    if c not in [col_cli, col_sector]:
                        valores_muestra = df_filtrado[c].astype(str).str.lower().unique().tolist()
                        if any(r in " ".join(valores_muestra) for r in ["mype", "general", "rer", "agrario", "rus", "p. natural"]):
                            col_regimen = c
                            break

            if col_regimen and col_cli:
                df_unicos_reg = df_filtrado[[col_cli, col_regimen]].dropna().drop_duplicates(subset=[col_cli])
                df_reg = df_unicos_reg[col_regimen].value_counts().reset_index()
                df_reg.columns = ["Régimen", "Cantidad"]

                fig_dona_reg = px.pie(
                    df_reg, names="Régimen", values="Cantidad",
                    hole=0.55, title="<b>Distribución por Régimen</b><br><span style='font-size:12px;color:gray'>Empresas Únicas</span>",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_dona_reg.update_traces(textinfo="label+value", textposition="outside")
                fig_dona_reg.update_layout(showlegend=False, margin=dict(t=50, b=20, l=20, r=20))
                st.plotly_chart(fig_dona_reg, use_container_width=True)

        # 3. VELOCÍMETRO: Grado de Avance Global
        with col_sup3:
            if col_req and col_avance_mes and df_filtrado[col_req].sum() > 0:
                total_alcanzado = df_filtrado[col_avance_mes].sum()
                total_req = df_filtrado[col_req].sum()
                porcentaje_global = min(100.0, (total_alcanzado / total_req) * 100)

                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=round(porcentaje_global, 1),
                    number={'suffix': "%", 'font': {'size': 38}},
                    title={'text': f"<b>Grado de Avance Global</b><br><span style='font-size:13px;color:gray'>{total_alcanzado:,.0f} de {total_req:,.0f} pts</span>"},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': "#0f172a", 'thickness': 0.25},
                        'steps': [
                            {'range': [0, 60], 'color': '#ef4444'},     # Rojo
                            {'range': [60, 80], 'color': '#facc15'},    # Amarillo
                            {'range': [80, 100], 'color': '#22c55e'}    # Verde
                        ],
                    }
                ))
                fig_gauge.update_layout(margin=dict(t=50, b=20, l=20, r=20), height=350)
                st.plotly_chart(fig_gauge, use_container_width=True)
                
        st.divider()

        # --- SECCIÓN 3: BARRAS HORIZONTALES (ALCANZADO VS REQUERIDO) ---
        def graficar_barras_avance(grupo_col, titulo):
            if not grupo_col or grupo_col not in df_filtrado.columns or not col_req or not col_avance_mes:
                return None
            resumen = df_filtrado.groupby(grupo_col)[[col_req, col_avance_mes]].sum().reset_index()
            resumen["Porcentaje"] = (resumen[col_avance_mes] / resumen[col_req] * 100).fillna(0).round(1)
            resumen = resumen.sort_values(by=col_avance_mes, ascending=True)

            fig = go.Figure()
            # Barra Requerido (fondo naranja)
            fig.add_trace(go.Bar(
                y=resumen[grupo_col],
                x=resumen[col_req],
                name="Puntaje requerido",
                orientation='h',
                marker_color='#ea580c',
                opacity=0.85
            ))
            # Barra Alcanzado (frente celeste)
            fig.add_trace(go.Bar(
                y=resumen[grupo_col],
                x=resumen[col_avance_mes],
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
            if col_emp:
                fig_emp = graficar_barras_avance(col_emp, "Grado de avance por contador")
                if fig_emp:
                    st.plotly_chart(fig_emp, use_container_width=True)

        with col_inf2:
            if col_sup:
                fig_sup = graficar_barras_avance(col_sup, "Grado de avance por Manager")
                if fig_sup:
                    st.plotly_chart(fig_sup, use_container_width=True)

            col_sec_bar = next((c for c in df_filtrado.columns if c.lower() == "sector"), None)
            if col_sec_bar:
                fig_sec = graficar_barras_avance(col_sec_bar, "Grado de avance por tipo de empresa")
                if fig_sec:
                    st.plotly_chart(fig_sec, use_container_width=True)

        # --- SECCIÓN 4: TABLA DETALLADA ---
        st.subheader("📋 Detalle de Tareas Filtradas")
        st.dataframe(df_filtrado, use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando la información: {e}")
else:
    st.info("Por favor, sube tu archivo para generar el panel de control.")

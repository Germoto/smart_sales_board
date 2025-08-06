import streamlit as st
import pandas as pd
import os
import json

# IMPORTA TUS MODULOS COMO ESTÁN
import informe_ventas
import prediccion_ventas_clima

# =========== CONFIGURACIÓN ===========
try:
    with open("config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "api_key": os.environ.get("API_KEY", ""),
        "latitude": float(os.environ.get("LATITUDE", "0.0")),
        "longitude": float(os.environ.get("LONGITUDE", "0.0"))
    }

LAT = config["latitude"]
LON = config["longitude"]
API_KEY = config["api_key"]

st.set_page_config(page_title="Dashboard Ventas y Clima", layout="wide")

# =========== ESTILO CSS PERSONALIZADO ===========
st.markdown("""
<style>
    /* Agrandar el ancho del sidebar */
    .css-1d391kg {
        width: 350px;
    }
    .css-1lcbmhc {
        width: 350px;
    }
    .css-17eq0hr {
        width: 350px;
    }
    
    /* Versión más nueva de Streamlit */
    section[data-testid="stSidebar"] {
        width: 350px !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 350px !important;
    }
    
    /* Ajustar el contenido principal para compensar el sidebar más ancho */
    .main .block-container {
        margin-left: 370px;
    }
</style>
""", unsafe_allow_html=True)

# =========== FUNCIÓN AUXILIAR PARA DESCARGAS ===========
def mostrar_archivos_recientes():
    """Muestra un panel con los archivos generados recientemente"""
    carpeta_reportes = "reportes"
    if os.path.exists(carpeta_reportes):
        archivos = []
        for archivo in os.listdir(carpeta_reportes):
            if archivo.endswith(('.pdf', '.xlsx', '.png')):
                ruta_completa = os.path.join(carpeta_reportes, archivo)
                archivos.append({
                    'nombre': archivo,
                    'ruta': ruta_completa,
                    'tamaño': os.path.getsize(ruta_completa) / 1024,  # KB
                    'fecha': os.path.getmtime(ruta_completa)
                })
        
        if archivos:
            # Ordenar por fecha (más recientes primero)
            archivos.sort(key=lambda x: x['fecha'], reverse=True)
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("📁 Archivos Recientes")
            
            for archivo in archivos[:5]:  # Mostrar solo los 5 más recientes
                with st.sidebar.expander(f"📄 {archivo['nombre'][:35]}..." if len(archivo['nombre']) > 35 else archivo['nombre']):
                    import datetime
                    fecha_mod = datetime.datetime.fromtimestamp(archivo['fecha']).strftime("%d/%m %H:%M")
                    st.write(f"**Tamaño:** {archivo['tamaño']:.1f} KB")
                    st.write(f"**Creado:** {fecha_mod}")
                    
                    # Botón de descarga en el sidebar
                    try:
                        with open(archivo['ruta'], "rb") as file:
                            file_data = file.read()
                        
                        if archivo['nombre'].endswith('.pdf'):
                            mime_type = "application/pdf"
                        elif archivo['nombre'].endswith('.xlsx'):
                            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        else:
                            mime_type = "image/png"
                        
                        st.download_button(
                            label="⬇️ Descargar",
                            data=file_data,
                            file_name=archivo['nombre'],
                            mime=mime_type,
                            key=f"sidebar_download_{archivo['nombre']}"
                        )
                    except:
                        st.write("Error al leer archivo")

# =========== SIDEBAR ===========
st.sidebar.title("Opciones")
uploaded_file = st.sidebar.file_uploader("Cargar archivo Excel", type=["xlsx"])

# =========== FUNCIONES DE NAVEGACIÓN ===========
opciones = [
    "Ver métricas rápidas",
    "Filtrar por fechas",
    "Ver tendencia diaria",
    "Ver top clientes y gráficos",
    "Generar PDF informe ventas",
    "Descargar clima histórico",
    "Correlación clima-ventas",
    "Entrenar modelo y predecir",
    "Ver predicción gráfica",
    "Exportar predicción a Excel",
    "Generar PDF informe predicción"
]
opcion = st.sidebar.selectbox("¿Qué deseas hacer?", opciones)

# Mostrar archivos recientes en el sidebar (después de las opciones)
mostrar_archivos_recientes()

if uploaded_file:
    # ----- Cargar y exponer ventas -----
    df = informe_ventas.cargar_excel(uploaded_file)
    informe_ventas.df_ventas_original = df
    informe_ventas.df_ventas_filtrado = df

    # --------- Filtrado por fechas ---------
    if opcion == "Filtrar por fechas":
        st.subheader("Filtrar por rango de fechas")
        fecha_min = df['fecha'].min()
        fecha_max = df['fecha'].max()
        fecha_inicio, fecha_fin = st.date_input("Rango de fechas:",
                                                [fecha_min, fecha_max],
                                                min_value=fecha_min,
                                                max_value=fecha_max)
        df_filtro = df[(df['fecha'] >= pd.to_datetime(fecha_inicio)) & (df['fecha'] <= pd.to_datetime(fecha_fin))]
        informe_ventas.df_ventas_filtrado = df_filtro
        st.write(f"Mostrando {len(df_filtro)} operaciones.")
        st.dataframe(df_filtro)
    else:
        df_filtro = informe_ventas.df_ventas_filtrado

    # --------- Métricas rápidas ---------
    if opcion == "Ver métricas rápidas":
        st.subheader("Métricas rápidas de ventas")
        resumen = informe_ventas.calcular_resumen(df_filtro)
        st.json(resumen)
        st.write("Total por día:")
        st.dataframe(df_filtro.groupby(df_filtro['fecha'].dt.date)['total'].sum())

    # --------- Tendencia diaria ---------
    elif opcion == "Ver tendencia diaria":
        st.subheader("Tendencia diaria de ventas")
        ventas_diarias = df_filtro.groupby(df_filtro['fecha'].dt.date)['total'].sum()
        st.line_chart(ventas_diarias)
        informe_ventas.generar_tendencia_diaria(para_pdf=False)

    # --------- Top clientes ---------
    elif opcion == "Ver top clientes y gráficos":
        st.subheader("Top clientes por ventas, descuentos y cantidades")
        top_clientes = df_filtro.groupby('cliente').agg({'total':'sum','descuento':'sum','cantidad':'sum'})
        top_ventas = top_clientes[['total']].sort_values(by='total', ascending=False).head(10)
        top_desc = top_clientes[['descuento']].sort_values(by='descuento', ascending=False).head(10)
        top_cant = top_clientes[['cantidad']].sort_values(by='cantidad', ascending=False).head(10)
        st.write("Top 10 Ventas:")
        st.dataframe(top_ventas)
        st.write("Top 10 Descuentos:")
        st.dataframe(top_desc)
        st.write("Top 10 Cantidades:")
        st.dataframe(top_cant)
        ventas_img, desc_img, cant_img = informe_ventas.generar_graficos(top_ventas, top_desc, top_cant)
        
        # Mostrar gráficos con botones de descarga
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.image(ventas_img, caption="Top 10 por ventas")
            if os.path.exists(ventas_img):
                with open(ventas_img, "rb") as img_file:
                    st.download_button(
                        label="📥 Descargar",
                        data=img_file.read(),
                        file_name=os.path.basename(ventas_img),
                        mime="image/png",
                        key="download_ventas_graph"
                    )
        
        with col2:
            st.image(desc_img, caption="Top 10 por descuentos")
            if os.path.exists(desc_img):
                with open(desc_img, "rb") as img_file:
                    st.download_button(
                        label="📥 Descargar",
                        data=img_file.read(),
                        file_name=os.path.basename(desc_img),
                        mime="image/png",
                        key="download_desc_graph"
                    )
        
        with col3:
            st.image(cant_img, caption="Top 10 por cantidades")
            if os.path.exists(cant_img):
                with open(cant_img, "rb") as img_file:
                    st.download_button(
                        label="📥 Descargar",
                        data=img_file.read(),
                        file_name=os.path.basename(cant_img),
                        mime="image/png",
                        key="download_cant_graph"
                    )

    # --------- PDF informe ventas ---------
    elif opcion == "Generar PDF informe ventas":
        with st.spinner("Generando informe PDF de ventas..."):
            pdf_path = informe_ventas.generar_pdf(con_graficos=True)
        st.success("PDF generado en la carpeta reportes.")
        
        # Botón de descarga del PDF de ventas
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            
            st.download_button(
                label="📥 Descargar Informe de Ventas",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                key="download_pdf_ventas"
            )
            
            st.info("""
            📄 **El informe de ventas incluye:**
            - 📊 Resumen de métricas principales
            - 🏆 Top 10 clientes por ventas, descuentos y cantidades
            - 📈 Gráficos y tendencias de ventas
            """)

    # ========= CLIMA Y PREDICCIONES =========

    # ----- Descargar clima histórico -----
    elif opcion == "Descargar clima histórico":
        ventas_diarias = df_filtro.groupby(df_filtro['fecha'].dt.date)['total'].sum().reset_index()
        ventas_diarias.columns = ['ds','y']
        ventas_diarias['ds'] = pd.to_datetime(ventas_diarias['ds'])  # Convertir a datetime
        clima_df = prediccion_ventas_clima.obtener_clima_historico(ventas_diarias['ds'].min(), ventas_diarias['ds'].max())
        st.write(clima_df)
        prediccion_ventas_clima.clima_df = clima_df

    # ----- Correlación clima-ventas -----
    elif opcion == "Correlación clima-ventas":
        ventas_diarias = df_filtro.groupby(df_filtro['fecha'].dt.date)['total'].sum().reset_index()
        ventas_diarias.columns = ['ds','y']
        ventas_diarias['ds'] = pd.to_datetime(ventas_diarias['ds'])  # Convertir a datetime
        if prediccion_ventas_clima.clima_df is None:
            st.warning("Primero descarga el clima histórico.")
        else:
            st.subheader("🌡️ Análisis de Correlación Clima-Ventas")
            with st.spinner("Analizando correlación..."):
                prediccion_ventas_clima.analizar_correlacion(ventas_diarias, prediccion_ventas_clima.clima_df)
            if prediccion_ventas_clima.grafico_correlacion:
                st.image(prediccion_ventas_clima.grafico_correlacion, caption="Correlación entre clima y ventas")
                
                # Botón de descarga del gráfico de correlación
                if os.path.exists(prediccion_ventas_clima.grafico_correlacion):
                    with open(prediccion_ventas_clima.grafico_correlacion, "rb") as img_file:
                        img_bytes = img_file.read()
                    
                    st.download_button(
                        label="📥 Descargar Gráfico de Correlación",
                        data=img_bytes,
                        file_name=os.path.basename(prediccion_ventas_clima.grafico_correlacion),
                        mime="image/png",
                        key="download_correlacion"
                    )
            else:
                st.error("Error al generar el gráfico de correlación.")

    # ----- Entrenar modelo y predecir -----
    elif opcion == "Entrenar modelo y predecir":
        ventas_diarias = df_filtro.groupby(df_filtro['fecha'].dt.date)['total'].sum().reset_index()
        ventas_diarias.columns = ['ds','y']
        ventas_diarias['ds'] = pd.to_datetime(ventas_diarias['ds'])  # Convertir a datetime
        if prediccion_ventas_clima.clima_df is None:
            st.warning("Primero descarga el clima histórico.")
        else:
            prediccion_ventas_clima.ventas_diarias = ventas_diarias
            prediccion_ventas_clima.entrenar_modelo(ventas_diarias, prediccion_ventas_clima.clima_df)
            st.success("Modelo entrenado y predicciones generadas.")

    # ----- Ver predicción gráfica -----
    elif opcion == "Ver predicción gráfica":
        if prediccion_ventas_clima.forecast is None:
            st.warning("Primero entrena el modelo y genera la predicción.")
        else:
            st.subheader("📈 Pronóstico de Ventas")
            with st.spinner("Generando gráficos de predicción..."):
                # Limpiar figuras anteriores
                prediccion_ventas_clima.limpiar_figuras()
                fig1, fig2 = prediccion_ventas_clima.graficar_prediccion_streamlit()
            
            if fig1 is not None:
                st.pyplot(fig1)
                
                # Botón de descarga del gráfico principal
                if prediccion_ventas_clima.grafico_prediccion and os.path.exists(prediccion_ventas_clima.grafico_prediccion):
                    with open(prediccion_ventas_clima.grafico_prediccion, "rb") as img_file:
                        img_bytes = img_file.read()
                    
                    st.download_button(
                        label="📥 Descargar Gráfico de Predicción",
                        data=img_bytes,
                        file_name=os.path.basename(prediccion_ventas_clima.grafico_prediccion),
                        mime="image/png",
                        key="download_prediccion_main"
                    )
                
                st.subheader("🔍 Componentes del Modelo")
                st.pyplot(fig2)
                
                # Botón de descarga del gráfico de componentes (necesitamos la ruta)
                # Vamos a obtener la ruta del gráfico de componentes
                carpeta = prediccion_ventas_clima.crear_carpeta_reportes()
                archivos_componentes = [f for f in os.listdir(carpeta) if f.startswith("componentes_prediccion_") and f.endswith(".png")]
                if archivos_componentes:
                    archivo_componentes = os.path.join(carpeta, max(archivos_componentes))  # El más reciente
                    with open(archivo_componentes, "rb") as img_file:
                        img_bytes = img_file.read()
                    
                    st.download_button(
                        label="📥 Descargar Gráfico de Componentes",
                        data=img_bytes,
                        file_name=os.path.basename(archivo_componentes),
                        mime="image/png",
                        key="download_componentes"
                    )
                
                # Limpiar figuras después de mostrarlas
                prediccion_ventas_clima.limpiar_figuras()
            else:
                st.error("Error al generar los gráficos de predicción.")

    # ----- Exportar predicción a Excel -----
    elif opcion == "Exportar predicción a Excel":
        if prediccion_ventas_clima.forecast is None:
            st.warning("Primero entrena el modelo y genera la predicción.")
        else:
            with st.spinner("Exportando predicciones a Excel..."):
                excel_path = prediccion_ventas_clima.exportar_predicciones_excel()
            st.success("Predicciones exportadas a Excel.")
            
            # Botón de descarga del Excel
            if excel_path and os.path.exists(excel_path):
                with open(excel_path, "rb") as excel_file:
                    excel_bytes = excel_file.read()
                
                st.download_button(
                    label="📥 Descargar Excel de Predicciones",
                    data=excel_bytes,
                    file_name=os.path.basename(excel_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_prediccion"
                )
                
                st.info("""
                📊 **El archivo Excel incluye:**
                - Predicciones de ventas para los próximos días
                - Histórico de ventas con datos climáticos
                - Datos climáticos históricos
                - Pronóstico climático
                """)

    # ----- Generar PDF informe predicción -----
    elif opcion == "Generar PDF informe predicción":
        if prediccion_ventas_clima.ventas_diarias is None or prediccion_ventas_clima.clima_df is None:
            st.warning("Primero carga datos de ventas y descarga el clima histórico.")
        else:
            with st.spinner("Generando informe PDF completo..."):
                pdf_path = prediccion_ventas_clima.generar_pdf()
            st.success("✅ PDF generado en la carpeta reportes.")
            
            # Botón de descarga del PDF
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                st.download_button(
                    label="📥 Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key="download_pdf_prediccion"
                )
            
            # Mostrar información detallada sobre el contenido del PDF
            st.info("""
            📄 **El informe incluye:**
            - 🌡️ Gráficos de correlación clima-ventas
            - 📈 Pronóstico de ventas ajustado al clima
            - 🔍 Componentes del modelo (tendencias estacionales)
            - 📊 Predicciones numéricas para los próximos 7 días
            - 📋 Análisis de días más cálidos/lluviosos y su impacto en ventas
            """)
            
            st.markdown("🎯 **Tip:** Usa este informe para tomar decisiones de inventario basadas en el clima pronosticado.")

else:
    st.info("Carga primero el archivo Excel de ventas para comenzar.")

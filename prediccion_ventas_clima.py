import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
import requests
import datetime
import os
import json
from utilidades import timestamp, crear_carpeta_reportes
from meteostat import Point, Daily
from fpdf import FPDF

# Cargar configuración desde config.json
try:
    with open("config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "api_key": os.environ.get("API_KEY", ""),
        "latitude": float(os.environ.get("LATITUDE", "0.0")),
        "longitude": float(os.environ.get("LONGITUDE", "0.0"))
    }

# Coordenadas de Iquitos
LAT = config["latitude"]
LON = config["longitude"]
API_KEY = config["api_key"]

ventas_diarias = None
clima_df = None
modelo = None
forecast = None
grafico_correlacion = None
grafico_prediccion = None

# ==============================
# 🧹 Función de limpieza de figuras
# ==============================
def limpiar_figuras():
    """Limpia todas las figuras de matplotlib para liberar memoria"""
    plt.close('all')

# ==============================
# 1️⃣ Cargar ventas desde Excel
# ==============================
def cargar_datos_excel(path):
    excel_data = pd.ExcelFile(path)
    df = pd.read_excel(path, sheet_name='Compras', skiprows=7)
    df.columns = df.iloc[0]
    df = df[1:]

    df = df.rename(columns={
        'Cliente': 'cliente',
        'Descuento': 'descuento',
        'Productos': 'productos',
        'Total': 'total',
        'Fecha Emisión': 'fecha'
    })
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['total'] = pd.to_numeric(df['total'], errors='coerce')
    df = df[df['cliente'].notna() & ~df['cliente'].astype(str).str.contains("Totales", case=False, na=False)]

    ventas = df.groupby(df['fecha'].dt.date)['total'].sum().reset_index()
    ventas.columns = ['ds', 'y']
    ventas['ds'] = pd.to_datetime(ventas['ds'])
    return ventas

# ==============================
# 2️⃣ Clima histórico (Meteostat)
# ==============================
def obtener_clima_historico(fecha_inicio, fecha_fin):
    print("⏳ Descargando clima histórico desde Meteostat...")

    if isinstance(fecha_inicio, datetime.date) and not isinstance(fecha_inicio, datetime.datetime):
        fecha_inicio = datetime.datetime.combine(fecha_inicio, datetime.time.min)
    if isinstance(fecha_fin, datetime.date) and not isinstance(fecha_fin, datetime.datetime):
        fecha_fin = datetime.datetime.combine(fecha_fin, datetime.time.min)

    punto = Point(LAT, LON)
    data = Daily(punto, fecha_inicio, fecha_fin).fetch()

    if data.empty:
        print("⚠ No se encontraron datos climáticos históricos.")
        return pd.DataFrame(columns=["ds", "temp", "lluvia"])

    df = pd.DataFrame({
        "ds": pd.to_datetime(data.index.date),
        "temp": data["tavg"],
        "lluvia": data["prcp"]
    }).reset_index(drop=True)

    print(f"✅ Clima histórico obtenido: {len(df)} días.")
    return df

# ==============================
# 3️⃣ Clima futuro (OpenWeatherMap)
# ==============================
def obtener_clima_pronostico(dias=7):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY}&lang=es"
    res = requests.get(url).json()
    datos = {}

    for item in res['list']:
        fecha = item['dt_txt'].split(" ")[0]
        temp = item['main']['temp']
        lluvia = item.get('rain', {}).get('3h', 0)
        if fecha not in datos:
            datos[fecha] = {"temp": [], "lluvia": []}
        datos[fecha]["temp"].append(temp)
        datos[fecha]["lluvia"].append(lluvia)

    promedios = []
    for fecha, valores in datos.items():
        promedios.append([pd.to_datetime(fecha),
                          sum(valores["temp"]) / len(valores["temp"]),
                          sum(valores["lluvia"])])
    return pd.DataFrame(promedios, columns=["ds", "temp", "lluvia"])

# ==============================
# 4️⃣ Entrenar modelo con clima
# ==============================
def entrenar_modelo(ventas, clima):
    global modelo, forecast
    # Asegurar que ambas columnas 'ds' sean del mismo tipo (datetime)
    ventas = ventas.copy()
    clima = clima.copy()
    ventas['ds'] = pd.to_datetime(ventas['ds'])
    clima['ds'] = pd.to_datetime(clima['ds'])
    
    df = ventas.merge(clima, on="ds", how="left")

    # Convertir columnas numéricas de manera más robusta
    df['temp'] = pd.to_numeric(df['temp'], errors='coerce').astype('float64')
    df['lluvia'] = pd.to_numeric(df['lluvia'], errors='coerce').astype('float64')

    if df['temp'].isnull().sum() > 0 or df['lluvia'].isnull().sum() > 0:
        print(f"⚠ Se encontraron datos climáticos faltantes. Serán rellenados con la media.")
    df['temp'] = df['temp'].fillna(df['temp'].mean())
    df['lluvia'] = df['lluvia'].fillna(df['lluvia'].mean())

    # Asegurar que las columnas sean float64
    df['temp'] = df['temp'].astype('float64')
    df['lluvia'] = df['lluvia'].astype('float64')
    df['y'] = df['y'].astype('float64')

    modelo = Prophet(daily_seasonality=True)
    modelo.add_regressor('temp')
    modelo.add_regressor('lluvia')
    modelo.fit(df)

    # Preparar datos futuros
    dias_futuros = 14
    futuro_fechas = modelo.make_future_dataframe(periods=dias_futuros)
    futuro_fechas['ds'] = pd.to_datetime(futuro_fechas['ds'])

    clima['ds'] = pd.to_datetime(clima['ds'])
    clima_futuro = obtener_clima_pronostico(dias_futuros)
    clima_futuro['ds'] = pd.to_datetime(clima_futuro['ds'])

    futuro = futuro_fechas.merge(pd.concat([clima, clima_futuro]), on="ds", how="left")

    # ✅ Mantener solo las columnas necesarias para Prophet
    futuro = futuro[['ds', 'temp', 'lluvia']].copy()

    # Convertir todas las columnas numéricas y rellenar NaN con tipo explícito
    for col in ['temp', 'lluvia']:
        futuro[col] = pd.to_numeric(futuro[col], errors='coerce').astype('float64')
    
    # Rellenar valores faltantes con la media de cada columna
    futuro['temp'] = futuro['temp'].fillna(futuro['temp'].mean())
    futuro['lluvia'] = futuro['lluvia'].fillna(futuro['lluvia'].mean())
    
    # Asegurar que no hay valores infinitos o NaN
    futuro = futuro.replace([float('inf'), float('-inf')], float('nan'))
    futuro = futuro.ffill().bfill().fillna(0)

    forecast = modelo.predict(futuro)
    print("\n✅ Modelo entrenado con clima histórico y pronóstico.")
    return forecast

# ==============================
# 5️⃣ Correlación clima-ventas
# ==============================
def analizar_correlacion(ventas, clima):
    global grafico_correlacion
    # Asegurar que ambas columnas 'ds' sean del mismo tipo (datetime)
    ventas = ventas.copy()
    clima = clima.copy()
    ventas['ds'] = pd.to_datetime(ventas['ds'])
    clima['ds'] = pd.to_datetime(clima['ds'])
    
    df = ventas.merge(clima, on="ds", how="left")
    corr_temp = df['y'].corr(df['temp'])
    corr_lluvia = df['y'].corr(df['lluvia'])

    print("\n📊 CORRELACIÓN ENTRE CLIMA Y VENTAS")
    print(f"- Correlación Ventas vs Temperatura: {corr_temp:.3f} {'(Positiva)' if corr_temp > 0 else '(Negativa)'}")
    print(f"- Correlación Ventas vs Lluvia: {corr_lluvia:.3f} {'(Positiva)' if corr_lluvia > 0 else '(Negativa)'}")

    carpeta = crear_carpeta_reportes()
    ts = timestamp()

    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.scatter(df['temp'], df['y'], color='orange')
    plt.xlabel("Temperatura (°C)")
    plt.ylabel("Ventas (S/.)")
    plt.title("Ventas vs Temperatura")

    plt.subplot(1, 2, 2)
    plt.scatter(df['lluvia'], df['y'], color='blue')
    plt.xlabel("Lluvia (mm)")
    plt.ylabel("Ventas (S/.)")
    plt.title("Ventas vs Lluvia")

    plt.tight_layout()
    grafico_correlacion = os.path.join(carpeta, f"correlacion_clima_ventas_{ts}.png")
    plt.savefig(grafico_correlacion, dpi=150, bbox_inches='tight')
    plt.close()  # Cerrar la figura para liberar memoria y evitar problemas en Streamlit

# ==============================
# 6️⃣ Graficar predicción
# ==============================
def graficar_prediccion():
    global modelo, forecast, grafico_prediccion
    carpeta = crear_carpeta_reportes()
    ts = timestamp()

    # Crear el gráfico principal de predicción
    fig1 = modelo.plot(forecast)
    plt.title("Pronóstico de ventas ajustado al clima")
    plt.xlabel("Fecha")
    plt.ylabel("Ventas (S/.)")
    grafico_prediccion = os.path.join(carpeta, f"prediccion_ventas_{ts}.png")
    plt.savefig(grafico_prediccion, dpi=150, bbox_inches='tight')
    plt.close()  # Cerrar la figura para liberar memoria

    # Crear el gráfico de componentes
    fig2 = modelo.plot_components(forecast)
    grafico_componentes = os.path.join(carpeta, f"componentes_prediccion_{ts}.png")
    plt.savefig(grafico_componentes, dpi=150, bbox_inches='tight')
    plt.close()  # Cerrar la figura para liberar memoria
    
    return grafico_prediccion, grafico_componentes

# ==============================
# 6.1️⃣ Graficar predicción para Streamlit
# ==============================
def graficar_prediccion_streamlit():
    global modelo, forecast, grafico_prediccion
    if modelo is None or forecast is None:
        return None, None
    
    # Limpiar figuras existentes
    plt.close('all')
    
    # Crear el gráfico principal de predicción
    fig1 = modelo.plot(forecast)
    plt.title("Pronóstico de ventas ajustado al clima")
    plt.xlabel("Fecha")
    plt.ylabel("Ventas (S/.)")
    
    # Guardar la figura principal para el PDF
    carpeta = crear_carpeta_reportes()
    ts = timestamp()
    grafico_prediccion = os.path.join(carpeta, f"prediccion_ventas_{ts}.png")
    plt.savefig(grafico_prediccion, dpi=150, bbox_inches='tight')
    
    # Crear el gráfico de componentes en una nueva figura
    fig2 = modelo.plot_components(forecast)
    componentes_prediccion = os.path.join(carpeta, f"componentes_prediccion_{ts}.png")
    plt.savefig(componentes_prediccion, dpi=150, bbox_inches='tight')
    
    return fig1, fig2

# ==============================
# 7️⃣ Exportar Excel
# ==============================
def exportar_predicciones_excel():
    global forecast, ventas_diarias, clima_df
    if forecast is None:
        print("⚠ Genera predicciones primero.")
        return

    carpeta = crear_carpeta_reportes()
    ts = timestamp()
    archivo = os.path.join(carpeta, f"predicciones_clima_{ts}.xlsx")

    pred = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    pred.columns = ['Fecha', 'Predicción', 'Límite Inferior', 'Límite Superior']

    # Asegurar que las columnas 'ds' sean del mismo tipo antes del merge
    ventas_temp = ventas_diarias.copy()
    clima_temp = clima_df.copy()
    ventas_temp['ds'] = pd.to_datetime(ventas_temp['ds'])
    clima_temp['ds'] = pd.to_datetime(clima_temp['ds'])
    
    clima_ventas = ventas_temp.merge(clima_temp, on="ds", how="left")
    clima_ventas.columns = ['Fecha', 'Ventas (S/)', 'Temp (°C)', 'Lluvia (mm)']

    clima_futuro = obtener_clima_pronostico(7)
    clima_futuro.columns = ['Fecha', 'Temp (°C)', 'Lluvia (mm)']

    with pd.ExcelWriter(archivo) as writer:
        pred.to_excel(writer, sheet_name="Predicciones Ventas", index=False)
        clima_ventas.to_excel(writer, sheet_name="Histórico Ventas+Clima", index=False)
        clima_df.to_excel(writer, sheet_name="Clima Histórico", index=False)
        clima_futuro.to_excel(writer, sheet_name="Clima Pronóstico", index=False)

    print(f"✅ Archivo exportado: {archivo}")
    return archivo  # Retornar la ruta del archivo generado

# ==============================
# 8️⃣ Generar PDF
# ==============================
def generar_pdf():
    global grafico_correlacion, grafico_prediccion, ventas_diarias, clima_df, modelo, forecast
    
    # Verificar que tenemos todos los datos necesarios
    if ventas_diarias is None or clima_df is None:
        print("⚠ Faltan datos de ventas o clima. Carga los datos primero.")
        return
    
    # Generar gráfico de correlación si no existe
    if not grafico_correlacion:
        print("📊 Generando gráfico de correlación...")
        analizar_correlacion(ventas_diarias, clima_df)
    
    # Generar gráfico de predicción si no existe y tenemos modelo
    grafico_componentes = None
    if not grafico_prediccion and modelo is not None and forecast is not None:
        print("📈 Generando gráficos de predicción...")
        grafico_prediccion, grafico_componentes = graficar_prediccion()
    elif modelo is not None and forecast is not None:
        # Si ya existe el gráfico principal, generar también el de componentes
        carpeta = crear_carpeta_reportes()
        ts = timestamp()
        # Generar gráfico de componentes
        fig2 = modelo.plot_components(forecast)
        grafico_componentes = os.path.join(carpeta, f"componentes_prediccion_{ts}.png")
        plt.savefig(grafico_componentes, dpi=150, bbox_inches='tight')
        plt.close()
    
    if not grafico_correlacion:
        print("⚠ No se pudo generar el gráfico de correlación.")
        return
        
    if not grafico_prediccion and modelo is not None:
        print("⚠ No se pudo generar el gráfico de predicción.")
        return

    carpeta = crear_carpeta_reportes()
    ts = timestamp()
    pdf_file = os.path.join(carpeta, f"Informe_Prediccion_Clima_{ts}.pdf")

    # Asegurar que las columnas 'ds' sean del mismo tipo antes del merge
    ventas_temp = ventas_diarias.copy()
    clima_temp = clima_df.copy()
    ventas_temp['ds'] = pd.to_datetime(ventas_temp['ds'])
    clima_temp['ds'] = pd.to_datetime(clima_temp['ds'])
    
    clima_ventas = ventas_temp.merge(clima_temp, on="ds", how="left")
    top_calidos = clima_ventas.sort_values(by="temp", ascending=False).head(5)
    top_lluviosos = clima_ventas.sort_values(by="lluvia", ascending=False).head(5)

    dias_secos = clima_ventas[clima_ventas['lluvia'] == 0]
    dias_lluviosos = clima_ventas[clima_ventas['lluvia'] > 0]

    prom_secos = dias_secos['y'].mean() if not dias_secos.empty else 0
    prom_lluviosos = dias_lluviosos['y'].mean() if not dias_lluviosos.empty else 0

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Informe de Predicción de Ventas con Clima", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, "Este informe muestra la correlación entre clima y ventas, y el pronóstico de ventas ajustado según el clima (Iquitos, Perú).")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Gráfico de Correlación Clima-Ventas", ln=True)
    pdf.image(grafico_correlacion, x=10, w=180)
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Top 5 días más cálidos y sus ventas", ln=True)
    pdf.set_font("Arial", "", 12)
    for _, fila in top_calidos.iterrows():
        pdf.cell(0, 8, f"{fila['ds'].date()} | Temp: {fila['temp']}°C | Ventas: S/. {fila['y']:.2f}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Top 5 días más lluviosos y sus ventas", ln=True)
    pdf.set_font("Arial", "", 12)
    for _, fila in top_lluviosos.iterrows():
        pdf.cell(0, 8, f"{fila['ds'].date()} | Lluvia: {fila['lluvia']}mm | Ventas: S/. {fila['y']:.2f}", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Promedio de ventas según condición climática", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Días secos (lluvia = 0mm): S/. {prom_secos:.2f}", ln=True)
    pdf.cell(0, 8, f"Días lluviosos (lluvia > 0mm): S/. {prom_lluviosos:.2f}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Pronóstico de Ventas Ajustado al Clima", ln=True)
    if grafico_prediccion and os.path.exists(grafico_prediccion):
        pdf.image(grafico_prediccion, x=10, w=180)
        pdf.ln(5)
    
    # Agregar gráfico de componentes del modelo si existe
    if grafico_componentes and os.path.exists(grafico_componentes):
        pdf.add_page()  # Nueva página para el gráfico de componentes
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Componentes del Modelo de Predicción", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 8, "Los componentes del modelo muestran las tendencias estacionales, semanales y la influencia de los factores climáticos en las ventas.")
        pdf.ln(5)
        pdf.image(grafico_componentes, x=10, w=180)
    
    # Agregar sección de predicciones numéricas si tenemos forecast
    if forecast is not None:
        pdf.add_page()  # Nueva página para las predicciones numéricas
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Predicciones Numéricas - Próximos 7 días", ln=True)
        pdf.ln(5)
        
        # Obtener las últimas predicciones (futuras)
        ultima_fecha_historica = ventas_diarias['ds'].max()
        predicciones_futuras = forecast[forecast['ds'] > ultima_fecha_historica].head(7)
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(60, 8, "Fecha", 1, 0, "C")
        pdf.cell(40, 8, "Predicción (S/.)", 1, 0, "C")
        pdf.cell(45, 8, "Límite Inferior (S/.)", 1, 0, "C")
        pdf.cell(45, 8, "Límite Superior (S/.)", 1, 1, "C")
        
        for _, fila in predicciones_futuras.iterrows():
            pdf.cell(60, 8, f"{fila['ds'].date()}", 1, 0, "C")
            pdf.cell(40, 8, f"{fila['yhat']:.2f}", 1, 0, "C")
            pdf.cell(45, 8, f"{fila['yhat_lower']:.2f}", 1, 0, "C")
            pdf.cell(45, 8, f"{fila['yhat_upper']:.2f}", 1, 1, "C")

    pdf.output(pdf_file)
    print(f"✅ Informe PDF generado: {pdf_file}")
    return pdf_file  # Retornar la ruta del archivo generado

# ==============================
# 9️⃣ Menú principal
# ==============================
def menu():
    global ventas_diarias, clima_df
    while True:
        print("\n====== MENÚ PREDICCIÓN CON CLIMA ======")
        print("1. Cargar ventas desde Excel")
        print("2. Descargar clima histórico (Meteostat)")
        print("3. Analizar correlación clima-ventas")
        print("4. Entrenar modelo y predecir")
        print("5. Ver gráficos de predicción")
        print("6. Exportar predicciones a Excel")
        print("7. Generar informe PDF")
        print("8. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            ruta = input("\n📂 Ruta Excel: ")
            ventas_diarias = cargar_datos_excel(ruta)
            print(f"✅ Ventas cargadas: {len(ventas_diarias)} días.")
        elif opcion == "2":
            if ventas_diarias is None:
                print("⚠ Primero carga ventas.")
            else:
                inicio = ventas_diarias['ds'].min()
                fin = ventas_diarias['ds'].max()
                clima_df = obtener_clima_historico(inicio, fin)
        elif opcion == "3":
            if ventas_diarias is not None and clima_df is not None:
                analizar_correlacion(ventas_diarias, clima_df)
            else:
                print("⚠ Carga ventas y clima histórico primero.")
        elif opcion == "4":
            if ventas_diarias is not None and clima_df is not None:
                entrenar_modelo(ventas_diarias, clima_df)
            else:
                print("⚠ Carga ventas y clima histórico primero.")
        elif opcion == "5":
            graficar_prediccion()
        elif opcion == "6":
            exportar_predicciones_excel()
        elif opcion == "7":
            generar_pdf()
        elif opcion == "8":
            print("👋 Saliendo...")
            break
        else:
            print("⚠ Opción inválida.")

if __name__ == "__main__":
    menu()

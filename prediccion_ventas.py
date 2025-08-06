import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
import datetime
import os
from utilidades import timestamp, crear_carpeta_reportes

ventas_diarias = None
modelo = None
forecast = None

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

    ventas_diarias = df.groupby(df['fecha'].dt.date)['total'].sum().reset_index()
    ventas_diarias.columns = ['ds', 'y']
    return ventas_diarias

def predecir_ventas(dias_futuros=30):
    global ventas_diarias, modelo, forecast
    if ventas_diarias is None:
        print("\n⚠ Primero carga el archivo.")
        return

    modelo = Prophet(daily_seasonality=True)
    modelo.fit(ventas_diarias)
    futuro = modelo.make_future_dataframe(periods=dias_futuros)
    forecast = modelo.predict(futuro)
    print(f"\n✅ Predicciones generadas para {dias_futuros} días.")

def graficar_prediccion():
    global modelo, forecast
    if forecast is None:
        print("\n⚠ Genera predicciones primero.")
        return

    modelo.plot(forecast)
    plt.title("Pronóstico de ventas (histórico + futuro)")
    plt.xlabel("Fecha")
    plt.ylabel("Ventas (S/.)")
    plt.show()

    modelo.plot_components(forecast)
    plt.show()

def mostrar_predicciones_tabla(dias=10):
    global forecast
    if forecast is None:
        print("\n⚠ Genera predicciones primero.")
        return

    predicciones = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(dias)
    print("\n📅 Pronóstico (próximos días):")
    for _, fila in predicciones.iterrows():
        print(f"{fila['ds'].date()}: S/. {fila['yhat']:.2f} (rango: {fila['yhat_lower']:.2f} - {fila['yhat_upper']:.2f})")

def exportar_predicciones_excel():
    global forecast
    if forecast is None:
        print("\n⚠ Genera predicciones primero.")
        return

    carpeta = crear_carpeta_reportes()
    ts = timestamp()
    nombre_archivo = os.path.join(carpeta, f"predicciones_ventas_{ts}.xlsx")

    predicciones = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    predicciones.columns = ['Fecha', 'Predicción', 'Límite Inferior', 'Límite Superior']
    predicciones.to_excel(nombre_archivo, index=False)
    print(f"\n✅ Predicciones exportadas: {nombre_archivo}")

def menu():
    global ventas_diarias
    while True:
        print("\n====== MENÚ PREDICCIÓN DE VENTAS ======")
        print("1. Cargar archivo Excel de ventas")
        print("2. Entrenar modelo y predecir ventas")
        print("3. Ver gráficos del pronóstico")
        print("4. Mostrar tabla de predicciones")
        print("5. Exportar predicciones a Excel")
        print("6. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == "1": 
            path = input("\n📂 Ruta del Excel: ")
            ventas_diarias = cargar_datos_excel(path)
            print(f"✅ Datos cargados: {len(ventas_diarias)} días históricos.")
        elif opcion == "2":
            dias = int(input("\n⏳ ¿Cuántos días predecir? "))
            predecir_ventas(dias)
        elif opcion == "3": graficar_prediccion()
        elif opcion == "4":
            dias = int(input("\n📊 ¿Cuántos días mostrar?: "))
            mostrar_predicciones_tabla(dias)
        elif opcion == "5": exportar_predicciones_excel()
        elif opcion == "6": print("\n👋 Saliendo..."); break
        else: print("\n⚠ Opción inválida.")

if __name__ == "__main__":
    menu()

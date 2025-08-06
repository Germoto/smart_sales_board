import pandas as pd
import re
from fpdf import FPDF
import datetime
import matplotlib.pyplot as plt
import os
from utilidades import timestamp, crear_carpeta_reportes

df_ventas_original = None
df_ventas_filtrado = None
archivo_excel = None

def cargar_excel(path):
    global df_ventas_original, df_ventas_filtrado, archivo_excel
    archivo_excel = path
    excel_data = pd.ExcelFile(path)
    df_ventas = pd.read_excel(path, sheet_name='Compras', skiprows=7)
    df_ventas.columns = df_ventas.iloc[0]
    df_ventas = df_ventas[1:]

    df_ventas = df_ventas.rename(columns={
        'Cliente': 'cliente',
        'Descuento': 'descuento',
        'Productos': 'productos',
        'Total': 'total',
        'Fecha Emisión': 'fecha',
    })

    df_ventas['descuento'] = pd.to_numeric(df_ventas['descuento'], errors='coerce')
    df_ventas['total'] = pd.to_numeric(df_ventas['total'], errors='coerce')

    def extraer_cantidad(texto):
        if isinstance(texto, str):
            match = re.search(r'Cantidad:\s*(\d+)', texto)
            if match:
                return int(match.group(1))
        return 0
    df_ventas['cantidad'] = df_ventas['productos'].apply(extraer_cantidad)

    df_ventas = df_ventas[df_ventas['cliente'].notna() & ~df_ventas['cliente'].astype(str).str.contains("Totales", case=False, na=False)]
    df_ventas['fecha'] = pd.to_datetime(df_ventas['fecha'])

    df_ventas_original = df_ventas
    df_ventas_filtrado = df_ventas
    print("\n✅ Archivo cargado correctamente.")
    return df_ventas_filtrado

def filtrar_por_rango_fechas():
    global df_ventas_original, df_ventas_filtrado
    if df_ventas_original is None:
        print("\n⚠ Primero debes cargar un archivo Excel.")
        return

    print("\n📅 Filtrar por rango de fechas")
    fecha_inicio = input("Fecha inicio (YYYY-MM-DD): ")
    fecha_fin = input("Fecha fin (YYYY-MM-DD): ")

    try:
        inicio = pd.to_datetime(fecha_inicio)
        fin = pd.to_datetime(fecha_fin)
        df_ventas_filtrado = df_ventas_original[(df_ventas_original['fecha'] >= inicio) & (df_ventas_original['fecha'] <= fin)]
        print(f"\n✅ Filtro aplicado: {fecha_inicio} hasta {fecha_fin}. Registros: {len(df_ventas_filtrado)}")
    except Exception as e:
        print(f"⚠ Error: {e}")

def calcular_resumen(df):
    return {
        'Total ventas (S/.)': df['total'].sum(),
        'Total descuentos (S/.)': df['descuento'].sum(),
        'Total unidades vendidas': df['cantidad'].sum(),
        'Total operaciones': len(df)
    }

def mostrar_metricas_rapidas():
    global df_ventas_filtrado
    if df_ventas_filtrado is None or df_ventas_filtrado.empty:
        print("\n⚠ No hay datos cargados o filtrados.")
        return
    
    resumen = calcular_resumen(df_ventas_filtrado)
    print("\n📊 MÉTRICAS RÁPIDAS DE VENTAS")
    print(f"- Total ventas: S/. {resumen['Total ventas (S/.)']:.2f}")
    print(f"- Total descuentos: S/. {resumen['Total descuentos (S/.)']:.2f}")
    print(f"- Total unidades vendidas: {resumen['Total unidades vendidas']}")
    print(f"- Total operaciones: {resumen['Total operaciones']}")
    if resumen['Total operaciones'] > 0:
        print(f"- Promedio por operación: S/. {(resumen['Total ventas (S/.)']/resumen['Total operaciones']):.2f}")

    top_ventas = df_ventas_filtrado.groupby('cliente')['total'].sum().sort_values(ascending=False).head(5)
    print("\n🏆 Top 5 Clientes por Ventas:")
    for cliente, total in top_ventas.items():
        print(f"   - {cliente}: S/. {total:.2f}")

    top_cantidades = df_ventas_filtrado.groupby('cliente')['cantidad'].sum().sort_values(ascending=False).head(5)
    print("\n📦 Top 5 Clientes por Cantidades:")
    for cliente, cantidad in top_cantidades.items():
        print(f"   - {cliente}: {cantidad} unidades")

    ventas_diarias = df_ventas_filtrado.groupby(df_ventas_filtrado['fecha'].dt.date)['total'].sum()
    if not ventas_diarias.empty:
        mejor_dia = ventas_diarias.idxmax()
        mejor_dia_monto = ventas_diarias.max()
        print(f"\n📅 Día con mayor venta: {mejor_dia} con S/. {mejor_dia_monto:.2f}")

    print("\n🗓 Ventas por día:")
    for fecha, monto in ventas_diarias.items():
        print(f"   - {fecha}: S/. {monto:.2f}")

def generar_graficos(top_ventas, top_descuentos, top_cantidades):
    carpeta = crear_carpeta_reportes()
    ts = timestamp()

    def grafico(nombre, df, columna, titulo):
        archivo = os.path.join(carpeta, nombre)
        plt.figure(figsize=(8, 4))
        plt.barh(df.index, df[columna], color='skyblue')
        plt.xlabel(columna)
        plt.title(titulo)
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(archivo)
        plt.close()
        return archivo

    ventas_img = grafico(f"ventas_{ts}.png", top_ventas, 'total', 'Top 10 Clientes por Ventas (S/)')
    descuentos_img = grafico(f"descuentos_{ts}.png", top_descuentos, 'descuento', 'Top 10 Clientes por Descuentos (S/)')
    cantidades_img = grafico(f"cantidades_{ts}.png", top_cantidades, 'cantidad', 'Top 10 Clientes por Cantidades')

    return ventas_img, descuentos_img, cantidades_img

def generar_tendencia_diaria(para_pdf=False):
    global df_ventas_filtrado
    if df_ventas_filtrado is None or df_ventas_filtrado.empty:
        print("\n⚠ No hay datos cargados.")
        return None

    ts = timestamp()
    ventas_diarias = df_ventas_filtrado.groupby(df_ventas_filtrado['fecha'].dt.date)['total'].sum()
    carpeta = crear_carpeta_reportes()

    plt.figure(figsize=(12, 6))
    plt.plot(ventas_diarias.index, ventas_diarias.values, marker='o', linestyle='-', color='b')
    plt.title("Tendencia diaria de ventas")
    plt.xlabel("Fecha")
    plt.ylabel("Ventas (S/)")
    plt.grid(True)
    plt.xticks(rotation=45)

    for fecha, monto in zip(ventas_diarias.index, ventas_diarias.values):
        plt.annotate(f"S/. {monto:.2f}\n{fecha}", (fecha, monto), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8, color='black')

    plt.tight_layout()
    file_name = os.path.join(carpeta, f"tendencia_diaria_{ts}.png")
    plt.savefig(file_name)
    if not para_pdf:
        plt.show()
    plt.close()
    return file_name

def generar_pdf(con_graficos=True):
    global df_ventas_filtrado
    if df_ventas_filtrado is None or df_ventas_filtrado.empty:
        print("\n⚠ No hay datos cargados.")
        return
    
    ts = timestamp()
    resumen = calcular_resumen(df_ventas_filtrado)
    top_clientes = df_ventas_filtrado.groupby('cliente').agg({'total':'sum','descuento':'sum','cantidad':'sum'})
    top_ventas = top_clientes[['total']].sort_values(by='total', ascending=False).head(10)
    top_descuentos = top_clientes[['descuento']].sort_values(by='descuento', ascending=False).head(10)
    top_cantidades = top_clientes[['cantidad']].sort_values(by='cantidad', ascending=False).head(10)

    if con_graficos:
        ventas_img, descuentos_img, cantidades_img = generar_graficos(top_ventas, top_descuentos, top_cantidades)
        tendencia_img = generar_tendencia_diaria(para_pdf=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'Resumen de Ventas - {datetime.datetime.now().strftime("%B %Y")}', ln=True)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 10, f"""
RESUMEN GENERAL:
- Total ventas: S/ {resumen['Total ventas (S/.)']:.2f}
- Total descuentos: S/ {resumen['Total descuentos (S/.)']:.2f}
- Total unidades vendidas: {resumen['Total unidades vendidas']}
- Total operaciones: {resumen['Total operaciones']}
""")

    if con_graficos:
        pdf.image(ventas_img, x=10, w=180)
        pdf.ln(5)
        pdf.image(descuentos_img, x=10, w=180)
        pdf.ln(5)
        pdf.image(cantidades_img, x=10, w=180)
        pdf.ln(5)
        pdf.image(tendencia_img, x=10, w=180)

    carpeta = crear_carpeta_reportes()
    pdf_name = os.path.join(carpeta, f"Informe_Mensual_Ventas_{ts}.pdf")
    pdf.output(pdf_name)
    print(f"\n✅ PDF generado: {pdf_name}")
    return pdf_name  # Retornar la ruta del archivo generado

def menu():
    while True:
        print("\n====== MENÚ DE INFORMES ======")
        print("1. Cargar archivo Excel")
        print("2. Filtrar por rango de fechas")
        print("3. Ver métricas rápidas")
        print("4. Generar informe PDF con gráficos")
        print("5. Generar informe PDF sin gráficos")
        print("6. Mostrar gráfico de tendencia diaria")
        print("7. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == "1": path = input("\nRuta Excel: "); cargar_excel(path)
        elif opcion == "2": filtrar_por_rango_fechas()
        elif opcion == "3": mostrar_metricas_rapidas()
        elif opcion == "4": generar_pdf(con_graficos=True)
        elif opcion == "5": generar_pdf(con_graficos=False)
        elif opcion == "6": generar_tendencia_diaria()
        elif opcion == "7": print("\n👋 Saliendo..."); break
        else: print("\n⚠ Opción inválida.")

if __name__ == "__main__":
    menu()

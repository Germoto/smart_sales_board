# 📊 Sistema de Gestión Comercial con Análisis Climático

Una herramienta completa para analizar ventas, generar informes y predecir tendencias basadas en datos climáticos.

## 🚀 Características Principales

### 📈 **Análisis de Ventas**
- ✅ Métricas rápidas y resúmenes estadísticos
- ✅ Filtrado por rangos de fechas
- ✅ Top clientes por ventas, descuentos y cantidades
- ✅ Tendencias diarias con gráficos interactivos
- ✅ Exportación a PDF con gráficos profesionales

### 🌡️ **Análisis Climático**
- ✅ Descarga automática de datos climáticos históricos
- ✅ Correlación entre clima y ventas
- ✅ Predicciones de ventas basadas en pronóstico del tiempo
- ✅ Modelo Prophet con factores climáticos (temperatura y lluvia)

### 📋 **Informes y Reportes**
- ✅ PDFs profesionales con gráficos
- ✅ Archivos Excel con múltiples hojas de datos
- ✅ Gráficos PNG descargables
- ✅ Panel de archivos recientes en dashboard
- ✅ Botones de descarga directa

## 🛠️ Instalación

### 1. **Clonar el repositorio**
```bash
git clone [URL_DEL_REPOSITORIO]
cd "Herramientas gestion comercial/tools"
```

### 2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

### 3. **Configurar API del clima**
1. Copia `config.json.example` a `config.json`
2. Regístrate en [OpenWeatherMap](https://openweathermap.org/api) para obtener API key gratuita
3. Edita `config.json` con tu API key y coordenadas

```json
{
  "latitude": -3.7437,
  "longitude": -73.2516, 
  "api_key": "tu_api_key_aqui"
}
```

## 🎯 Uso

### **Dashboard Web (Recomendado)**
```bash
streamlit run dashboard.py
```

### **Módulos Independientes**
```bash
# Solo análisis de ventas
python informe_ventas.py

# Solo predicciones con clima
python prediccion_ventas_clima.py

# Solo predicciones básicas
python prediccion_ventas.py
```

## 📁 Estructura del Proyecto

```
tools/
├── dashboard.py              # 🎛️ Dashboard principal con Streamlit
├── informe_ventas.py         # 📊 Análisis de ventas y reportes
├── prediccion_ventas.py      # 📈 Predicciones básicas con Prophet
├── prediccion_ventas_clima.py # 🌡️ Predicciones con factores climáticos
├── utilidades.py             # 🔧 Funciones auxiliares
├── config.json               # ⚙️ Configuración (no versionado)
├── config.json.example       # 📋 Plantilla de configuración
├── requirements.txt          # 📦 Dependencias de Python
└── reportes/                 # 📂 Archivos generados (no versionado)
    ├── *.pdf                 # Informes en PDF
    ├── *.xlsx                # Datos en Excel
    └── *.png                 # Gráficos
```

## 📊 Funcionalidades del Dashboard

### **🔹 Análisis de Ventas**
1. **Ver métricas rápidas** - Resumen estadístico instantáneo
2. **Filtrar por fechas** - Análisis de períodos específicos
3. **Ver tendencia diaria** - Gráfico de líneas interactivo
4. **Top clientes y gráficos** - Rankings con visualizaciones
5. **Generar PDF informe ventas** - Reporte profesional completo

### **🔹 Predicciones Climáticas**
6. **Descargar clima histórico** - Datos de temperatura y lluvia
7. **Correlación clima-ventas** - Análisis de impacto climático
8. **Entrenar modelo y predecir** - Machine Learning con Prophet
9. **Ver predicción gráfica** - Visualización de pronósticos
10. **Exportar predicción a Excel** - Datos numéricos detallados
11. **Generar PDF informe predicción** - Reporte completo con ML

## 🎨 Características del Dashboard

- ✅ **Sidebar ampliado** para mejor navegación
- ✅ **Panel de archivos recientes** con descarga directa
- ✅ **Botones de descarga** en cada sección
- ✅ **Spinners de carga** para mejor UX
- ✅ **Información contextual** sobre cada archivo
- ✅ **Layout responsive** con columnas adaptables

## 📋 Dependencias Principales

- **streamlit** - Framework web para el dashboard
- **pandas** - Manipulación de datos
- **matplotlib** - Generación de gráficos
- **prophet** - Modelos de predicción de series temporales
- **meteostat** - Datos climáticos históricos
- **requests** - API calls para pronóstico del tiempo
- **fpdf** - Generación de PDFs
- **openpyxl** - Manejo de archivos Excel

## 🔒 Seguridad

- ❌ **config.json** no se versiona (contiene API keys)
- ❌ **reportes/** no se versiona (pueden contener datos sensibles)
- ✅ **config.json.example** como plantilla segura
- ✅ **.gitignore** completo para proteger datos

## 🚀 Características Avanzadas

### **🤖 Machine Learning**
- Modelo Prophet con regresores climáticos
- Predicciones con bandas de confianza
- Análisis de componentes estacionales
- Validación cruzada temporal

### **📊 Visualizaciones**
- Gráficos de correlación scatter
- Pronósticos con tendencias
- Componentes del modelo (estacionalidad)
- Gráficos de barras para rankings

### **📄 Reportes Profesionales**
- PDFs multi-página con gráficos
- Excel con múltiples hojas organizadas
- Análisis estadístico detallado
- Recomendaciones basadas en datos

## 🛟 Soporte

Para problemas o sugerencias:
1. Revisa que `config.json` esté configurado correctamente
2. Verifica que todos los paquetes estén instalados
3. Asegúrate de tener conexión a internet para datos climáticos

## 📈 Próximas Funcionalidades

- [ ] Integración con más APIs climáticas
- [ ] Predicciones por categoría de producto
- [ ] Dashboard con métricas en tiempo real
- [ ] Alertas automáticas por email
- [ ] Análisis de estacionalidad avanzado

---

**Desarrollado para optimizar decisiones comerciales basadas en datos** 🎯

import os
import datetime

def timestamp():
    """Genera un timestamp único para nombres de archivo."""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def crear_carpeta_reportes():
    """Crea la carpeta 'reportes' si no existe y devuelve la ruta."""
    carpeta = "reportes"
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
    return carpeta

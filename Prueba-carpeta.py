import logging
import subprocess
import shutil
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime

def setup_logger(mission_path):
    """Configura el archivo log de la misión."""
    log_file = mission_path / f"alicia_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logging.basicConfig(filename=log_file, level=logging.INFO, 
                        format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger()

def count_valid_images(source_folder):
    """Detecta y cuenta fotografías válidas."""
    valid_ext = {".jpg", ".jpeg", ".png"}
    images = [f for f in source_folder.iterdir() if f.is_file() and f.suffix.lower() in valid_ext]
    return len(images), images

def create_mission_structure(base_path, mission_name):
    """Crea automáticamente las carpetas modulares para el procesamiento."""
    mission_dir = base_path / mission_name
    folders = ["01_images", "02_sparse", "03_dense", "04_mesh", "05_textures"]
    for folder in folders:
        (mission_dir / folder).mkdir(parents=True, exist_ok=True)
    return mission_dir

def run_external_command(command, logger):
    """Ejecuta programas externos (COLMAP/OpenMVS) desde la terminal."""
    try:
        logger.info(f"Ejecutando comando: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info("Comando finalizado con éxito.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en el proceso: {e.stderr}")
        return False

def init_mission(source_str, dest_str, mission_name):
    """Orquestador principal de la arquitectura A.L.I.C.I.A."""
    source_folder = Path(source_str)
    base_path = Path(dest_str)
    
    # 1. Crear estructura y log
    mission_dir = create_mission_structure(base_path, mission_name)
    logger = setup_logger(mission_dir)
    logger.info("=== INICIO DE PREPARACIÓN AUTOMATIZADA A.L.I.C.I.A. ===")
    
    # 2. Verificar fotografías
    count, images = count_valid_images(source_folder)
    logger.info(f"Fotografías válidas detectadas en origen: {count}")
    
    if count == 0:
        logger.warning("No se encontraron fotografías. Abortando misión.")
        return
        
    # 3. Copiar imágenes al entorno de trabajo
    logger.info("Copiando imágenes al directorio de trabajo...")
    images_dest = mission_dir / "01_images"
    for img in images:
        shutil.copy(img, images_dest / img.name)
    logger.info("Imágenes preparadas correctamente.")

    # 4. Prueba modular de COLMAP
    logger.info("Verificando conexión con el motor fotogramétrico (COLMAP)...")
    comando_prueba = ["colmap", "help"]
    conexion_exitosa = run_external_command(comando_prueba, logger)
    
    if conexion_exitosa:
        logger.info("=== PREPARACIÓN FINALIZADA CON ÉXITO ===")
        logger.info("El entorno está listo para iniciar la reconstrucción 3D.")
    else:
        logger.error("=== ERROR CRÍTICO: No se pudo comunicar con COLMAP ===")


# --- Bloque principal de ejecución ---
if __name__ == "__main__":
    # Ocultar la ventana principal de tkinter
    root = tk.Tk()
    root.withdraw()
    
    print("Por favor, selecciona la carpeta ORIGEN (donde están tus fotografías)...")
    carpeta_origen = filedialog.askdirectory(title="Selecciona la carpeta de las fotografías")
    
    if not carpeta_origen:
        print("Operación cancelada. No seleccionaste la carpeta de origen.")
    else:
        print("Por favor, selecciona la carpeta DESTINO (donde se guardará el procesamiento)...")
        carpeta_destino = filedialog.askdirectory(title="Selecciona dónde guardar la misión")
        
        if not carpeta_destino:
            print("Operación cancelada. No seleccionaste la carpeta de destino.")
        else:
            # Pedir el nombre de la misión en la terminal
            nombre_mision = input("Escribe el nombre de la misión (ej. Mision_A001): ")
            
            print(f"\nIniciando el sistema...")
            init_mission(carpeta_origen, carpeta_destino, nombre_mision)
            print(f"¡Listo! Revisa la carpeta en tu destino seleccionado.")
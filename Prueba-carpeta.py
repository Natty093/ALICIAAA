import logging
import subprocess
import shutil
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime

# CONFIGURACIÓN DE EJECUTABLES
COLMAP_EXE = "colmap"


def find_executable(name):
    """Busca un ejecutable en el PATH del sistema. Devuelve la ruta o None."""
    return shutil.which(name)


def check_dependencies(logger):
    """Verifica que COLMAP esté disponible antes de empezar a procesar nada."""
    logger.info("Verificando dependencias externas (COLMAP)...")
    colmap_path = find_executable(COLMAP_EXE)
    if colmap_path:
        logger.info(f"  ✔ COLMAP encontrado en: {colmap_path}")
    else:
        logger.error("  ✘ COLMAP no fue encontrado en el PATH.")
    return colmap_path

# UTILIDADES BASE (misión, logging, imágenes)

def setup_logger(mission_path):
    """Configura el archivo log de la misión y la salida en terminal."""
    log_file = mission_path / f"alicia_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()


def count_valid_images(source_folder):
    """Detecta y cuenta fotografías válidas."""
    valid_ext = {".jpg", ".jpeg", ".png"}
    images = [f for f in source_folder.iterdir() if f.is_file() and f.suffix.lower() in valid_ext]
    return len(images), images


def create_mission_structure(base_path, mission_name):
    """Crea automáticamente las carpetas modulares para el procesamiento.
    Se dejan ya las carpetas 03/04/05 aunque no se usen todavía, para no
    tener que rehacer la estructura cuando integremos OpenMVS."""
    mission_dir = base_path / mission_name
    folders = ["01_images", "02_sparse", "03_dense", "04_mesh", "05_textures"]
    for folder in folders:
        (mission_dir / folder).mkdir(parents=True, exist_ok=True)
    return mission_dir


def run_external_command(command, logger, cwd=None):
    """Ejecuta programas externos (por ahora, COLMAP) desde la terminal."""
    try:
        logger.info(f"Ejecutando comando: {' '.join(str(c) for c in command)}")
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, cwd=cwd
        )
        if result.stdout.strip():
            logger.info(result.stdout.strip()[-1500:])  # evita logs gigantes
        logger.info("Comando finalizado con éxito.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en el proceso: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"No se encontró el ejecutable: {command[0]}")
        return False


# ---------------------------------------------------------------------------
# PIPELINE COLMAP
# ---------------------------------------------------------------------------
# Etapas estándar de COLMAP por CLI:
#   1. feature_extractor   -> detecta puntos característicos en cada foto
#   2. sequential_matcher  -> compara fotos vecinas en la secuencia (vuelo)
#   3. mapper              -> reconstrucción dispersa (sparse) + poses de cámara
#   4. model_converter     -> exporta el modelo a formato texto/PLY

def run_colmap_pipeline(mission_dir, logger):
    """Ejecuta el pipeline completo de COLMAP: features -> matching -> sparse."""
    images_path = mission_dir / "01_images"
    sparse_path = mission_dir / "02_sparse"
    database_path = mission_dir / "database.db"

    logger.info("=== INICIANDO PIPELINE COLMAP ===")

    # 1. Feature extraction (CPU, no GPU: evita errores de OpenGL/Wayland
    #    en equipos sin GPU dedicada o con drivers no compatibles)
    ok = run_external_command([
        COLMAP_EXE, "feature_extractor",
        "--database_path", str(database_path),
        "--image_path", str(images_path),
        "--ImageReader.single_camera", "1",
        "--FeatureExtraction.use_gpu", "0",
    ], logger)
    if not ok:
        logger.error("Falló feature_extractor. Abortando pipeline COLMAP.")
        return False

    # 2. Matching secuencial (ideal para fotos de vuelo tomadas en orden)
    #    También en CPU por la misma razón.
    ok = run_external_command([
        COLMAP_EXE, "sequential_matcher",
        "--database_path", str(database_path),
        "--FeatureMatching.use_gpu", "0",
    ], logger)
    if not ok:
        logger.error("Falló sequential_matcher. Abortando pipeline COLMAP.")
        return False

    # 3. Sparse reconstruction (mapper)
    sparse_output = sparse_path / "0"
    ok = run_external_command([
        COLMAP_EXE, "mapper",
        "--database_path", str(database_path),
        "--image_path", str(images_path),
        "--output_path", str(sparse_path),
    ], logger)
    if not ok or not sparse_output.exists():
        logger.error("Falló mapper (reconstrucción dispersa). Abortando pipeline COLMAP.")
        return False

    # 4. Exportar el modelo en formato texto (útil para inspección y para
    #    cuando integremos OpenMVS más adelante)
    ok = run_external_command([
        COLMAP_EXE, "model_converter",
        "--input_path", str(sparse_output),
        "--output_path", str(sparse_output),
        "--output_type", "TXT",
    ], logger)
    if not ok:
        logger.error("Falló model_converter.")
        return False

    logger.info("=== PIPELINE COLMAP FINALIZADO CON ÉXITO ===")
    return True


# ---------------------------------------------------------------------------
# ORQUESTADOR PRINCIPAL
# ---------------------------------------------------------------------------

def init_mission(source_str, dest_str, mission_name):
    """Orquestador principal de la arquitectura A.L.I.C.I.A. (solo COLMAP)."""
    source_folder = Path(source_str)
    base_path = Path(dest_str)

    # 1. Verificar fotografías PRIMERO (antes de crear nada)
    count, images = count_valid_images(source_folder)

    if count == 0:
        print("\nError: No se encontraron fotografías válidas en la carpeta de origen.")
        print("Abortando misión. No se generaron archivos ni directorios basura.")
        return

    # 2. Crear estructura y log
    mission_dir = create_mission_structure(base_path, mission_name)
    logger = setup_logger(mission_dir)
    logger.info("=== INICIO DE PREPARACIÓN AUTOMATIZADA A.L.I.C.I.A. ===")
    logger.info(f"Fotografías válidas detectadas en origen: {count}")

    # 3. Verificar dependencias
    colmap_path = check_dependencies(logger)
    if not colmap_path:
        logger.error("COLMAP no fue encontrado. Corrige la instalación antes de continuar.")
        return

    # 4. Copiar imágenes al entorno de trabajo
    logger.info("Copiando imágenes al directorio de trabajo...")
    images_dest = mission_dir / "01_images"
    for img in images:
        shutil.copy(img, images_dest / img.name)
    logger.info("Imágenes preparadas correctamente.")

    # 5. Pipeline COLMAP
    if not run_colmap_pipeline(mission_dir, logger):
        logger.error("=== ERROR CRÍTICO: el pipeline se detuvo en la etapa de COLMAP ===")
        return

    logger.info("=== MISIÓN COMPLETADA (COLMAP / sparse reconstruction) ===")
    logger.info(f"Resultado disponible en: {mission_dir / '02_sparse'}")
    logger.info("OpenMVS todavía no está integrado; se agregará en una etapa posterior.")


# ---------------------------------------------------------------------------
# BLOQUE PRINCIPAL DE EJECUCIÓN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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
            nombre_mision = input("Escribe el nombre de la misión (ej. Mision_A001): ")

            print("\nIniciando el sistema...")
            init_mission(carpeta_origen, carpeta_destino, nombre_mision)
            print("¡Listo! Revisa la carpeta en tu destino seleccionado.")
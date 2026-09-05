# A.L.I.C.I.A.

**A**nálisis y **L**ocalización **I**nteligente para **C**artografía e **I**nterpretación **A**utónoma

Sistema de automatización para el procesamiento fotogramétrico de misiones aéreas: recibe fotografías, arma la estructura de trabajo, y ejecuta el pipeline de reconstrucción 3D (COLMAP, con OpenMVS planeado a futuro).

## Estado actual del proyecto

- ✅ Preparación automática de misión (detección de fotos, estructura de carpetas, logging)
- ✅ Pipeline de COLMAP integrado (feature extraction → matching → sparse reconstruction)
- ⏳ Integración de OpenMVS (densificación, malla, texturizado) — pendiente, en progreso
- ⏳ Integración de GPS/sensores adicionales — pendiente

## Concepto general

```
ADQUISICIÓN → RECONSTRUCCIÓN → ANÁLISIS
```

```
Vuelo → Fotografías + posición → Fotogrametría → Nube de puntos →
Malla 3D → Modelo del terreno → Mediciones → Inteligencia artificial
```

La cámara y los sensores obtienen información. COLMAP (y más adelante OpenMVS) transforman esa información en geometría tridimensional. Las herramientas posteriores de procesamiento e IA interpretarán esa geometría.

## Requisitos

### Sistema
- Linux (probado en Ubuntu) o windows
- Python 3.10+

### Dependencias de Python
```bash
pip install --break-system-packages tk
```
(`tkinter` suele venir preinstalado en la mayoría de distribuciones; si falta, en Ubuntu: `sudo apt install python3-tk`)

## Instalación de COLMAP según sistema operativo

### Linux (Ubuntu)
Debe estar instalado y accesible en el `PATH` del sistema:
```bash
colmap --help
```
Si el comando no se reconoce, instálalo siguiendo la [documentación oficial de COLMAP](https://colmap.github.io/install.html).

> **Nota sobre GPU:** si tu instalación de COLMAP no tiene soporte GPU (CUDA) o tu equipo no tiene un contexto OpenGL funcional, el script ya fuerza el uso de CPU automáticamente (`--FeatureExtraction.use_gpu 0` y `--FeatureMatching.use_gpu 0`). Es más lento que con GPU, pero evita errores de tipo `Shader not supported by your hardware`.


### Windows
El script no necesita ningún cambio de código para correr en Windows: usa `pathlib` (maneja rutas de ambos sistemas) y `tkinter` (incluido en el instalador oficial de Python para Windows).

### OpenMVS (no integrado todavía)
Ver sección [Próximos pasos](#próximos-pasos).

## Uso

```bash
python3 alicia_pipeline_colmap.py
```

El programa te pedirá, en este orden:
1. **Carpeta origen**: donde están las fotografías de la misión.
2. **Carpeta destino**: donde se creará la estructura de la misión.
3. **Nombre de la misión** (ej. `Mision_A001`).

### Qué hace internamente

1. Verifica que existan fotografías válidas (`.jpg`, `.jpeg`, `.png`) en la carpeta origen. Si no hay ninguna, se aborta sin crear archivos ni carpetas.
2. Crea la estructura de la misión:
   ```
   <destino>/<nombre_mision>/
   ├── 01_images/
   ├── 02_sparse/
   ├── 03_dense/      (reservado para OpenMVS)
   ├── 04_mesh/        (reservado para OpenMVS)
   └── 05_textures/    (reservado para OpenMVS)
   ```
3. Verifica que COLMAP esté instalado.
4. Copia las fotografías a `01_images/`.
5. Ejecuta el pipeline de COLMAP:
   - `feature_extractor`
   - `sequential_matcher`
   - `mapper` (reconstrucción dispersa)
   - `model_converter` (exporta a formato TXT)
6. Genera un log (`alicia_log_<fecha>_<hora>.txt`) dentro de la carpeta de la misión, con cada paso ejecutado y cualquier error.

## Requisitos de las fotografías

COLMAP necesita fotos del **mismo objeto o escena**, tomadas desde ángulos cercanos entre sí, con **al menos 60-80% de solape visual** entre una foto y la siguiente. Fotos sin relación entre sí (de objetos distintos) no producirán ninguna reconstrucción — no es un error del programa, es un requisito fundamental de la fotogrametría.

Para un vuelo: recorrido continuo, sin saltos grandes de posición, idealmente 20+ fotos por zona de interés.

## Estructura del código

| Función | Responsabilidad |
|---|---|
| `find_executable` / `check_dependencies` | Localiza y valida que COLMAP esté disponible antes de procesar nada |
| `count_valid_images` | Detecta y cuenta fotografías válidas en la carpeta origen |
| `create_mission_structure` | Crea la jerarquía de carpetas de la misión |
| `setup_logger` | Configura el log en archivo + consola |
| `run_external_command` | Wrapper genérico para ejecutar cualquier programa externo vía CLI |
| `run_colmap_pipeline` | Orquesta las 4 etapas de COLMAP en orden, deteniéndose ante cualquier fallo |
| `init_mission` | Orquestador principal que conecta todo lo anterior |

El código está dividido en funciones independientes a propósito, para poder agregar OpenMVS, GPS u otros sensores como módulos nuevos sin reescribir lo existente.

## Próximos pasos

- **Integrar OpenMVS**: `InterfaceCOLMAP` → `DensifyPointCloud` → `ReconstructMesh` → `RefineMesh` → `TextureMesh`. Requiere compilar OpenMVS desde código fuente (no hay paquete `apt` oficial estable); ver notas de instalación en el historial del proyecto.
- Exponer parámetros configurables de cada etapa (actualmente se usan los valores por defecto de COLMAP salvo el uso de GPU).
- Agregar validación automática post-`mapper` (verificar cuántas cámaras se registraron correctamente).
- Incorporar GPS y otros sensores al pipeline.
- Evaluar `pycolmap` para etapas donde se necesite leer resultados intermedios directamente en Python.

## Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Shader not supported by your hardware` / `SIGABRT` en `feature_extractor` | COLMAP intentando usar GPU/OpenGL sin soporte válido | Ya resuelto en el script con `--FeatureExtraction.use_gpu 0` |
| `unrecognised option '--SiftExtraction.use_gpu'` | Versión de COLMAP renombró el parámetro | Revisar `colmap feature_extractor --help \| grep -i gpu` y actualizar el nombre en el script |
| `Failed to create any sparse model` en `mapper` | Fotos sin suficiente solape/relación entre sí | Usar fotos reales del mismo objeto/escena con 60-80% de solape |
| `No se pudo bloquear /var/lib/dpkg/lock-frontend` al usar `apt` | `unattended-upgrades` corriendo en segundo plano | Esperar a que termine, o forzar con `sudo killall unattended-upgr && sudo rm /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock && sudo dpkg --configure -a` |

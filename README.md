# BeanCass AI

Clasificación orientativa de enfermedades foliares de **fréjol (Beans)** y **yuca (Cassava)** a partir de una fotografía.

Proyecto de Inteligencia Artificial, Universidad Estatal de Milagro (UNEMI), Grupo 1: *«Clasificación de enfermedades
foliares en cultivos de yuca y fréjol: estudio comparativo»*. Se compararon una CNN propia, MobileNetV2, EfficientNetB0 y
DenseNet121 por cultivo; esta aplicación usa los modelos que el estudio seleccionó con el conjunto de Validation.

> Herramienta educativa: los resultados son orientativos y **no constituyen un diagnóstico agronómico**.

| Cultivo | Modelo | Clases | Test (estudio) |
|---|---|---|---|
| Fréjol | MobileNetV2 (ajuste fino, época 6) | mancha angular, roya, hoja sana | exactitud 96,88 %, F1 macro 0,9690, 4 errores (todos entre enfermedades) |
| Yuca | EfficientNetB0 (ajuste fino, época 3) | CBB, CBSD, CGM, CMD, hoja sana | exactitud 82,28 %, F1 macro 0,7544, 40 hojas enfermas clasificadas como sanas |

---

## Contenido

```
BeanCass-AI/
├── beans/  cassava/         Notebooks y resultados del estudio (no se modifican)
├── api/                     Backend FastAPI de inferencia
│   ├── app/                 main.py (rutas), modelos.py (carga/inferencia), imagen.py (validación),
│   │                        calidad.py (avisos), multipart_memoria.py, config.py, schemas.py, errors.py
│   ├── models/              Los 2 checkpoints seleccionados + manifest.json + umbrales_calibrados.json
│   ├── scripts/             preparar_modelos.py, calibrar_umbrales.py, calibrar_hoja.py
│   ├── tests/               pytest (contrato, paridad, validaciones) + pruebas «slow» con datasets
│   └── Dockerfile
├── web/                     Next.js 16 + React 19 (interfaz y proxy /api/predict)
├── scripts/dev.ps1          Levanta API y web en dos ventanas
├── docker-compose.yml
└── .env.example
```

## Inicio rápido en Windows (PowerShell, VS Code)

Requisitos: **Python 3.12** (`winget install Python.Python.3.12`), **Node.js 20 o superior** (probado con 22) y Git.
Tiempo aproximado: 10 minutos (la instalación de TensorFlow es lo más lento).

```powershell
git clone https://github.com/D4N13L4002/BeanCass-AI.git
cd BeanCass-AI

# 1) API (Python 3.12)
py -3.12 -m venv api\.venv
api\.venv\Scripts\python.exe -m pip install --upgrade pip
api\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt

# 2) Web (pnpm a través de corepack; si corepack da error de permisos, usa: npm install -g pnpm@12.3.4)
corepack enable
cd web
pnpm install
Copy-Item .env.example .env.local
cd ..

# 3) Arrancar ambos servicios (abre dos ventanas)
.\scripts\dev.ps1
```

Abre <http://localhost:3000>. La documentación interactiva de la API está en <http://127.0.0.1:8000/docs>.

Arranque manual, en dos terminales:

```powershell
# Terminal 1 — API
cd api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log

# Terminal 2 — Web
cd web
pnpm dev          # o, en modo producción:  pnpm build ; pnpm start
```

Si `py` no existe, usa la ruta completa: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv api\.venv`.
Si PowerShell bloquea el script, ejecútalo con `powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1`.

## Variables de entorno

Todas son opcionales; los valores por defecto sirven para desarrollo local. Ver [.env.example](.env.example).

| Variable | Servicio | Defecto | Descripción |
|---|---|---|---|
| `API_URL` | web | `http://127.0.0.1:8000` | URL interna de la API (solo la usa el servidor de Next). |
| `NEXT_PUBLIC_MAX_UPLOAD_MB` | web | `8` | Límite validado en el navegador (igual a `MAX_UPLOAD_MB`). |
| `MAX_UPLOAD_MB` | api | `8` | Tamaño máximo del archivo. |
| `MAX_IMAGE_PIXELS` | api | `40000000` | Límite anti *decompression bomb*. |
| `MIN_IMAGE_SIDE` / `MAX_ASPECT_RATIO` | api | `64` / `5` | Dimensión mínima y proporción máxima. |
| `ALLOWED_ORIGINS` | api | `http://localhost:3000` | Lista blanca CORS (separada por comas). |
| `RATE_LIMIT` | api | `20/minute` | Límite por IP. |
| `TRUST_FORWARDED_FOR` | api | `false` | Usar `X-Forwarded-For` para el límite; solo si la API únicamente es accesible vía el proxy. |
| `INFERENCE_TIMEOUT_S` | api | `30` | Tiempo máximo de inferencia. |
| `TF_INTRA_OP_THREADS` / `TF_INTER_OP_THREADS` | api | `0` (auto) | Hilos de TensorFlow. |
| `BEAN_T_MIN`, `BEAN_T_WARN`, `BEAN_T_MARGIN`, `CASSAVA_T_*` | api | calibrados | Sobrescriben los umbrales del manifest. |
| `T_ENTROPY` / `MIN_LEAF_RATIO` | api | `0.85` / `0.12` | Heurísticas de entropía y de «posible no-hoja». |

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | `{status, models_loaded:{bean,cassava}, tf_version}`; 503 si algún modelo no cargó. |
| `GET` | `/api/v1/models` | Metadatos públicos: clases, métricas de Test del estudio, umbrales. |
| `POST` | `/api/v1/predict` | `multipart/form-data` con `crop` (`bean`\|`cassava`) y `file` (JPEG/PNG). |

```powershell
curl.exe -F crop=bean -F "file=@web/public/bean-leaf.png" http://127.0.0.1:8000/api/v1/predict
```

Respuesta (resumida):

```json
{
  "crop": "bean",
  "model": {"name": "MobileNetV2", "version": "ajuste_fino_20261121_181000_639966"},
  "prediction": {"class_id": 0, "label": "angular_leaf_spot", "label_es": "Mancha angular", "confidence": 0.85, "is_healthy": false},
  "probabilities": [{"class_id": 0, "label": "angular_leaf_spot", "label_es": "Mancha angular", "probability": 0.85}, "…"],
  "quality": {"level": "ok", "warnings": [], "signals": {"top1": 0.85, "margin": 0.71, "entropy": 0.40, "leaf_ratio": 0.98, "reasons": []}},
  "image": {"width": 1376, "height": 768, "resized_to": [224, 224]},
  "inference_ms": 230,
  "disclaimer": "Resultado orientativo; no constituye diagnóstico."
}
```

Los errores siempre tienen la forma `{"error": {"code": "...", "message": "..."}}`: 400 (parámetros o imagen inválida),
413 (archivo o píxeles en exceso), 415 (formato no soportado: se validan los *magic bytes*, no la extensión),
422 (imagen muy pequeña o alargada), 429 (límite de solicitudes), 500 (sin trazas internas), 503 (modelo no disponible).

En la web, el navegador habla con `web/app/api/predict` (proxy), que valida de nuevo y reenvía a la API; así no hay CORS
y la URL interna no se expone.

## Cómo funciona la inferencia

- **Modelos**: `api/models/manifest.json` (generado por `api/scripts/preparar_modelos.py`) registra archivo, SHA-256,
  forma de entrada, capas esperadas y orden de clases. Al arrancar, la API verifica todo y falla con un error claro si no coincide.
- **Orden de clases**: fréjol `0=angular_leaf_spot, 1=bean_rust, 2=healthy`; yuca `0=cbb, 1=cbsd, 2=cgm, 3=cmd, 4=healthy`.
  Verificado contra `protocolo.json`, las columnas `prob_*` de los CSV de predicciones y `metricas_test.json`.
- **Preprocesamiento**: RGB `float32` en 0–255 → `tf.image.resize_with_pad(224, 224, antialias=True)` → `clip(0, 255)`.
  **Sin** `/255` ni `preprocess_input`: la normalización está dentro de los modelos (EfficientNetB0 internamente; la
  `Rescaling(1/127.5, −1)` de MobileNetV2 es una capa del modelo). En fotos cuadradas, `resize_with_pad` es idéntico al
  `resize` usado para Beans (verificado en tests). Se respeta la orientación EXIF y la transparencia se compone sobre blanco.
- **Privacidad**: la imagen se procesa en memoria (el multipart se parsea sin archivos temporales) y se descarta; los logs
  solo registran método, ruta, estado y duración.

### Avisos de calidad (umbrales calibrados con Validation)

Un clasificador softmax siempre elige una clase. Por eso cada respuesta incluye `quality.level`:

- `inconclusive`: top-1 < `t_min`, margen top-1 − top-2 < `t_margin`, entropía alta o la foto no parece una hoja. La
  interfaz **no muestra una categoría** y pide repetir la foto.
- `low_confidence`: top-1 < `t_warn`.
- En yuca, toda predicción «Hoja sana» incluye el aviso de que el modelo dejó 40 hojas enfermas como sanas en Test.

Los umbrales se calibraron **solo con los CSV de Validation** del estudio (`api/scripts/calibrar_umbrales.py`; Test no se usó):

| Cultivo | `t_min` | `t_warn` | `t_margin` | Efecto en Validation |
|---|---|---|---|---|
| Yuca | 0,65 (calibrado) | 0,90 (calibrado) | 0,40 (calibrado) | 20 % no concluyente; exactitud 50,5 % en ese grupo frente a 90,2 % en el resto |
| Fréjol | 0,75 (calibrado con solo 6 casos: débil) | 0,80 (**no calibrado**) | 0,10 (**no calibrado**) | 6 de 133 no concluyentes |

La heurística «posible no-hoja» (proporción de píxeles amarillo-verde a verde, umbral 0,12; `calibrar_hoja.py`) no
afectó a ninguna de las 128 imágenes de Test de Beans ni a 400 de Validation de Cassava, y marcó 19 de 24 fotos
genéricas. **No detecta paisajes con vegetación**: en 2 de 48 pruebas con fotos que no eran hojas, el modelo de fréjol
dio una categoría con confianza alta.

## Pruebas

```powershell
cd api
.\.venv\Scripts\python.exe -m pytest            # 55 pruebas: contrato, paridad, validaciones, errores, rate limit
.\.venv\Scripts\python.exe -m pytest -m slow -s # opcional: imágenes reales de los datasets
cd ..\web
pnpm typecheck ; pnpm build
```

Pruebas `slow` (requieren datos):

- **Fréjol**: descarga `data/test.zip` y `data/validation.zip` de
  [AI-Lab-Makerere/beans](https://huggingface.co/datasets/AI-Lab-Makerere/beans) y descomprímelos en
  `~/beancass_datos/beans_test` y `~/beancass_datos/beans_val` (o define `BEANS_DIR`). El bucket de TFDS para beans
  devuelve 403.
- **Yuca**: `tensorflow-datasets` descarga `cassava` automáticamente con
  `python -c "import tensorflow_datasets as t; t.builder('cassava').download_and_prepare()"` (≈1,3 GB).

Resultados obtenidos (2026-11-25): fréjol Test 124/128 = 0,9688 (igual al estudio) y 133/133 predicciones de Validation
iguales a las del estudio; yuca: diferencia máxima con las probabilidades del estudio de 2,8e-6 en 80 imágenes de
Validation y exactitud de 0,827 en 150 imágenes de Test.

E2E y capturas con Playwright (no es dependencia del proyecto):

```powershell
npm i -g playwright ; npx playwright install chromium
node web/scripts/e2e.mjs http://localhost:3000 <carpeta-con-archivos-invalidos>
$env:API_OFF=1 ; node web/scripts/e2e.mjs http://localhost:3000   # con la API apagada
node web/scripts/capturas.mjs http://localhost:3000 capturas
```

## Docker

```powershell
Copy-Item .env.example .env   # opcional
docker compose up --build     # http://localhost:3000
```

`api` usa Python 3.12 + TensorFlow CPU, monta `api/models` en solo lectura y no se publica hacia el host (solo la
alcanza la web). Ambos servicios tienen *healthcheck*; la web espera a que la API esté sana.

## Despliegue

- **TensorFlow no corre en funciones serverless de Vercel** (tamaño y memoria). Si el frontend va a Vercel, despliega
  la API aparte (Render, Railway, Fly.io o una VM con ≥ 2 GB de RAM usando `api/Dockerfile`) y configura en Vercel
  `API_URL=https://tu-api…` y `NEXT_PUBLIC_MAX_UPLOAD_MB`. En la API, ajusta `ALLOWED_ORIGINS` y, si solo la llama
  Vercel, `TRUST_FORWARDED_FOR=true`.
- **Todo en un servidor**: `docker compose up -d --build` detrás de un proxy inverso con HTTPS (Caddy, Nginx).

## Limitaciones del modelo

- Yuca es el modelo más débil: exactitud ≈ 82 %, recall de CBB ≈ 0,61; CBB y CBSD se confunden; 40 hojas enfermas
  se clasificaron como sanas en Test. «Hoja sana» en yuca nunca es una garantía.
- Resultados válidos bajo las condiciones de los datasets (iCassava 2019, Makerere AI Lab Beans); no garantizan el mismo
  desempeño con cualquier fotografía nueva.
- No hubo repeticiones con distintas semillas; en Cassava hay 12/11 coincidencias exactas Train–Validation/Test (documentadas).
- Para fréjol existe una evaluación de Test registrada antes de la comparación final (limitación declarada en el estudio).
- Las imágenes de ejemplo de la web son ilustrativas y no pertenecen a los datasets; por eso no tienen etiqueta real.

## Créditos

Universidad Estatal de Milagro (UNEMI) — Inteligencia Artificial, Grupo 1: Daniela Geraldin Arriaga Alvarez,
Frank Obed Cedeño Peña y Laddy Lisset Rocha León.
Datasets: iCassava 2019 (Makerere AI Lab, desafío FGVC6) y Beans (Makerere AI Lab), ambos a través de TensorFlow Datasets.

---

## Notebooks del estudio

### Cómo ejecutar el notebook

1. Clona el repositorio y abre la carpeta principal en VS Code.
2. Con **Python 3.12** y las extensiones **Python** y **Jupyter** instaladas, ejecuta en la terminal de PowerShell:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Abre `cassava/Preparacion_Cassava.ipynb`, selecciona `.venv` como kernel y ejecuta los pasos 1 al 8. La primera vez, el Paso 2 descarga las imágenes de Cassava y puede tardar unos minutos.

4. Para fréjol, abre `beans/Preparacion_Beans.ipynb` con el mismo kernel y ejecuta las celdas en orden.

### DenseNet121 para Cassava

El notebook `cassava/DenseNet121.ipynb` conserva las salidas del entrenamiento y de la evaluación en validación. Los historiales, las curvas y las matrices de las cuatro corridas están en `cassava/resultados/densenet121/`.

Para volver a ejecutar las celdas que cargan modelos guardados, necesitas colocar el archivo `mejor_modelo.keras` en la carpeta de la corrida correspondiente.

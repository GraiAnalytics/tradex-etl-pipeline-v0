# TradeX – Data Pipeline ETL

Pipeline ETL profesional y escalable para **TradeX**, orientado a la ingestión, normalización y generación de **señales accionables para el mercado financiero** a partir de datos alternativos (redes sociales, noticias) y datos de mercado.

El pipeline está diseñado bajo una arquitectura **Bronze / Silver / Gold**, con foco en:

* reproducibilidad
* auditoría
* escalabilidad
* observabilidad
* data quality
* backfills seguros

---

## 📐 Arquitectura de alto nivel

```
FUENTES EXTERNAS
  (X, YouTube, Reddit, News, Market Data)
          │
          ▼
┌────────────────────┐
│      BRONZE        │  Raw, auditable, immutable
│  (jsonl/parquet)   │
└────────────────────┘
          │
          ▼
┌────────────────────┐
│      SILVER        │  Clean, normalized, canonical
│ (entity-resolved)  │
└────────────────────┘
          │
          ▼
┌────────────────────┐
│       GOLD         │  Metrics, features, signals
│ (serving-ready)   │
└────────────────────┘
          │
          ▼
 UI / API / ALERTS / ML MODELS
```

---

## 🎯 Objetivos del pipeline

* Ingestar múltiples fuentes heterogéneas sin perder información
* Normalizar y resolver entidades de forma consistente
* Calcular métricas relativas (baselines, deltas, z-scores)
* Detectar señales explicables (spikes, anomalías, divergencias)
* Servir datos listos para UI, alertas y modelos ML
* Permitir reprocesamiento y auditoría completa (run_id + manifests)

---

## 🧱 Capas de datos

### 🟤 Bronze (Raw / Ingest)

* Copia fiel de las fuentes externas
* Inmutable, versionada por `run_id`
* Incluye metadata técnica (`ingest_time`, `event_time`, `cursor`)
* Permite backfills y reprocesamiento sin volver a llamar a APIs

Ejemplos:

* `bronze/youtube/comments`
* `bronze/x/posts`
* `bronze/market/daily_prices`

---

### ⚪ Silver (Clean / Canonical)

* Datos tipados, limpios y normalizados
* Resolución de entidades (`entity_id`)
* Deduplicación semántica
* Manejo de late data y schema drift
* Base confiable para análisis y features

Tablas core:

* `silver_entity_master`
* `silver_social_events`
* `silver_market_daily`

---

### 🟡 Gold (Business / Signals)

* Métricas finales (market + social)
* Baselines y features versionadas
* Señales detectadas con drivers y confianza
* Tablas optimizadas para UI y alertas

Ejemplos:

* `gold_market_entity_day`
* `gold_social_entity_day`
* `gold_signal_events`
* `gold_entity_daily_summary`

---

## 🛠️ Stack tecnológico (default)

* **Lenguaje**: Python 3.11+
* **Orquestación**: Dagster (Python-first, asset-based)
* **Storage**: Object Storage (S3 / MinIO / GCS)
* **Formatos**: JSONL.gz (Bronze), Parquet + Iceberg/Delta (Silver/Gold)
* **Estado**: Postgres (prod) / SQLite (local)
* **Data Quality**: checks custom + contracts
* **Observabilidad**: logs estructurados + métricas por run

---

## 📁 Estructura del repositorio (resumen)

```
src/tradex_pipeline/
├─ sources/        # extractores por fuente
├─ bronze/         # ingest, envelopes, manifests
├─ silver/         # parsers, transforms, quality
├─ gold/           # metrics, baselines, signals
├─ contracts/      # schemas y llaves por dataset
├─ state/          # watermarks / cursors
├─ orchestration/  # dagster / jobs / schedules
├─ alerts/         # dispatch de alertas
└─ common/         # utils compartidos
```

La estructura completa está documentada en `/docs/architecture`.

---

## 🚀 Quickstart (local)

### 1️⃣ Requisitos

* Python 3.11+
* Docker + Docker Compose
* Make (opcional, pero recomendado)

---

### 2️⃣ Clonar el repo

```bash
git clone git@github.com:tradex-ai/tradex-pipeline-etl.git
cd tradex-pipeline-etl
```

---

### 3️⃣ Variables de entorno

```bash
cp .env.example .env
```

Completa:

* API keys (YouTube, X, Reddit, News, Market)
* credenciales de storage
* configuración de entorno

---

### 4️⃣ Levantar stack local

```bash
docker-compose up -d
```

Esto levanta:

* MinIO (object storage)
* Postgres (estado y metadata)
* Orquestador (Dagster)

---

### 5️⃣ Instalar dependencias

```bash
poetry install
poetry shell
```

---

## ▶️ Ejecución de pipelines

### Ingesta Bronze (ejemplo)

```bash
python -m tradex_pipeline.cli run bronze youtube_comments
```

### Construcción Silver

```bash
python -m tradex_pipeline.cli run silver social_events
```

### Construcción Gold (metrics + signals)

```bash
python -m tradex_pipeline.cli run gold detect_signals
```

---

## 🔁 Backfills

Ejemplo: reprocesar social data entre fechas

```bash
python -m tradex_pipeline.cli backfill \
  --layer bronze \
  --dataset youtube_comments \
  --start-date 2025-12-01 \
  --end-date 2025-12-15
```

Silver y Gold se pueden reprocesar a partir de Bronze sin tocar las fuentes externas.

---

## 🧪 Data Quality

* Cada dataset tiene **contracts** definidos en `contracts/`
* Silver y Gold aplican **quality gates**
* Registros inválidos se envían a **quarantine**
* Fallos críticos bloquean la publicación

---

## 📊 Observabilidad

Por cada `run_id` se registran:

* volumen de datos
* latencia
* errores por tipo
* lag de event_time
* drift de esquema
* costos estimados

Alertas automáticas ante:

* fallos consecutivos
* caídas de volumen
* schema drift significativo

---

## 🔐 Seguridad

* Secrets vía `.env` / Secret Manager
* Storage cifrado en reposo
* Acceso por roles a Bronze/Silver/Gold
* Retención configurable por capa

---

## 🧠 Filosofía de diseño

* **Bronze nunca se modifica**
* **Silver es la verdad canónica**
* **Gold es un data product**
* Todo es:

  * versionado
  * reproducible
  * explicable
  * auditable

---

## 📌 Próximos pasos recomendados

1. Revisar `docs/architecture/01_bronze.md`
2. Configurar `configs/base.yaml`
3. Implementar el primer extractor Bronze (YouTube o Market)
4. Construir la primera tabla Silver canónica
5. Habilitar la primera señal Gold

---

## 📬 Contacto / Proyecto

TradeX es una plataforma enfocada en **señales de mercado basadas en datos alternativos**, combinando ingeniería de datos, ML y AI agéntica.

```markdown
# TradeX – Data Pipeline ETL

Pipeline ETL profesional y escalable para **TradeX**, orientado a la ingestión, normalización y generación de **señales accionables para el mercado financiero** a partir de datos alternativos (X/Twitter, Reddit, YouTube, News/RS S, SEC, arXiv, journals) y datos de mercado (**Alpaca**).

El pipeline está diseñado bajo una arquitectura **Bronze / Silver / Gold**, con foco en:

- reproducibilidad
- auditoría
- escalabilidad
- observabilidad
- data quality
- backfills seguros
- idempotencia (re-ejecuciones sin duplicar)

---

## 📐 Arquitectura de alto nivel

```

FUENTES EXTERNAS
(X Basic API v2, Reddit, YouTube, RSS News/Journals, SEC, arXiv, Alpaca)
│
▼
┌────────────────────┐
│      BRONZE        │  Raw, auditable, immutable (run_id + manifest + _SUCCESS)
│     (JSONL.gz)     │  Particionado por ingest_date, commit atómico por run
└────────────────────┘
│
▼
┌────────────────────┐
│      SILVER        │  Clean, normalized, canonical (entity-resolved)
│ (Parquet/Iceberg)  │  Dedup semántico + late data + schema drift handling
└────────────────────┘
│
▼
┌────────────────────┐
│       GOLD         │  Data products: metrics, baselines, features, signals
│ (serving-ready)    │  Señales explicables (drivers + confidence)
└────────────────────┘
│
▼
UI / API / ALERTS / ML MODELS

```

---

## 🎯 Objetivos del pipeline

- Ingestar múltiples fuentes heterogéneas sin perder información (**raw payload preservado en Bronze**)
- Normalizar y resolver entidades de forma consistente (`entity_id`)
- Calcular métricas relativas (baselines, deltas, z-scores)
- Detectar señales explicables (spikes, anomalías, divergencias)
- Servir datos listos para UI, alertas y modelos ML (tablas Gold “serving-ready”)
- Permitir reprocesamiento y auditoría completa (**run_id + manifest + state store**)
- Soportar incremental + backfills con la misma lógica (sin hacks)

---

## 🧱 Capas de datos

### 🟤 Bronze (Raw / Ingest)

Bronze es un **log de ingestas** con commits atómicos por `run_id`.

- Copia fiel de las fuentes externas (con envelope estándar)
- Inmutable, versionada por `run_id`
- Incluye metadata técnica (`ingest_time`, `event_time`, `cursor`, `params`)
- Manifiesto por corrida (`manifest.json`) y marcador `_SUCCESS`
- Idempotencia: dedup in-run + dedup persistente (Postgres) para evitar duplicados en re-runs/backfills

Ejemplos (dataset_key → path):
- `x.posts` → `bronze/source_system=x/dataset=posts/...`
- `market.daily_prices` → `bronze/source_system=market/dataset=daily_prices/...`
- `sec.filings` → `bronze/source_system=sec/dataset=filings/...`

**Especificación exacta**: `docs/architecture/01_bronze.md`

---

### ⚪ Silver (Clean / Canonical)

Silver define el **modelo canónico**: tipado fuerte + normalización + consistencia inter-fuentes.

- Datos limpios, tipados y normalizados
- Resolución de entidades (`entity_id`) y mapeos consistentes
- Deduplicación semántica (además del dedup por ID)
- Manejo de late data (reprocessing window) y schema drift controlado
- Base confiable para análisis, features y entrenamiento ML

Tablas core:
- `silver_entity_master`
- `silver_social_events`
- `silver_market_daily`

---

### 🟡 Gold (Business / Signals)

Gold son **data products** listos para consumo.

- Métricas finales (market + social)
- Baselines y features versionadas (`feature_version`, `signal_version`)
- Señales detectadas con drivers, severidad y confianza
- Serving tables optimizadas para UI, feeds y alertas

Ejemplos:
- `gold_market_entity_day`
- `gold_social_entity_day`
- `gold_baselines_entity_day`
- `gold_signal_events`
- `gold_entity_daily_summary`

---

## 🧩 Datasets soportados (v0)

### Social / Alt-data
- **X (Twitter) – Basic (API v2)**:
  - `x.posts` (recent search con cursor `start_time` + lookback + dedup)
  - opcional: `x.counts`, `x.usage` (si los habilitas)
- `reddit.posts`
- `youtube.comments`
- `news.articles_rss`
- `journals.articles_rss`
- `sec.filings`
- `arxiv.papers`

### Market
- **Alpaca**:
  - `market.daily_prices`

---

## 🛠️ Stack tecnológico (default)

- **Lenguaje**: Python 3.11+
- **Orquestación**: Dagster (Python-first, asset/job based)
- **Storage**: S3-compatible (MinIO dev / S3 prod)
- **Formato**:
  - Bronze: **JSONL.gz** (run-based, auditable)
  - Silver/Gold: Parquet (+ Iceberg/Delta opcional según engine)
- **Estado/Metadata**: Postgres (prod y local via docker)
- **Data Quality**: contracts + quality gates + quarantine
- **Observabilidad**: logs estructurados + métricas por run (counts, latency, errors, drift)

---

## 📁 Estructura del repositorio (resumen)

```

src/tradex_pipeline/
├─ sources/        # extractores por fuente (X, Alpaca, SEC, RSS, etc.)
├─ bronze/         # runner genérico + envelopes + manifests + writer + dedup
├─ silver/         # parsers + transforms + quality + writer
├─ gold/           # metrics + baselines + features + signals + serving
├─ contracts/      # definición de datasets, llaves, particiones, versiones
├─ state/          # pipeline_state + bronze_runs + bronze_record_index (Postgres)
├─ orchestration/  # dagster resources/jobs/schedules
├─ alerts/         # dispatch de alertas (webhook/kafka/slack opcional)
└─ common/         # utils compartidos

````

La estructura completa y las decisiones están documentadas en `/docs/architecture`.

---

## 🚀 Quickstart (local)

### 1️⃣ Requisitos

- Python 3.11+
- Docker + Docker Compose
- Poetry
- Make (opcional, recomendado)

---

### 2️⃣ Clonar el repo

```bash
git clone git@github.com:tradex-ai/tradex-pipeline-etl.git
cd tradex-pipeline-etl
````

---

### 3️⃣ Variables de entorno

```bash
cp .env.example .env
```

Completa como mínimo:

* credenciales de X (Bearer Token) — **Basic API v2**
* credenciales de Alpaca (API Key / Secret + endpoint market data)
* credenciales de storage (MinIO/S3)
* configuración Postgres

---

### 4️⃣ Levantar stack local

```bash
docker-compose up -d
```

Esto levanta:

* MinIO (object storage S3-compatible)
* Postgres (state store + metadata)
* servicios auxiliares (según compose)

---

### 5️⃣ Instalar dependencias

```bash
poetry install
poetry shell
```

---

## ▶️ Ejecución de pipelines

> Nota: usamos `dataset_key` del estilo `source.dataset` (ej: `x.posts`, `market.daily_prices`).

### Ingesta Bronze

```bash
python -m tradex_pipeline.cli run bronze x.posts
python -m tradex_pipeline.cli run bronze market.daily_prices
```

### Construcción Silver

```bash
python -m tradex_pipeline.cli run silver social_events
python -m tradex_pipeline.cli run silver market_daily
```

### Construcción Gold

```bash
python -m tradex_pipeline.cli run gold build_metrics
python -m tradex_pipeline.cli run gold detect_signals
python -m tradex_pipeline.cli run gold build_serving
```

---

## 🔁 Backfills

Ejemplo: backfill de X posts por rango de fechas

```bash
python -m tradex_pipeline.cli backfill \
  --layer bronze \
  --dataset x.posts \
  --start-date 2025-12-01 \
  --end-date 2025-12-15
```

Reglas:

* Bronze crea nuevos `run_id` (no pisa runs previos)
* Dedup persistente evita duplicados
* Silver/Gold se regeneran desde Bronze sin tocar fuentes externas

---

## 🧪 Data Quality

* Cada dataset tiene **contracts** en `src/tradex_pipeline/contracts/`
* Silver y Gold aplican **quality gates**
* Registros inválidos van a **quarantine**
* Fallos críticos bloquean publicación aguas abajo (no “datos a medias”)

---

## 📊 Observabilidad

Por cada `run_id` se registran:

* volumen de datos (fetched / written / deduped)
* latencia por etapa (fetch / write / commit)
* errores por tipo (429, 5xx, timeout)
* lag de event_time (si aplica)
* drift de esquema (fingerprints)

Alertas automáticas ante:

* fallos consecutivos
* caídas bruscas de volumen
* schema drift significativo

---

## 🔐 Seguridad

* Secrets vía `.env` / Secret Manager
* Storage cifrado en reposo
* Acceso por roles a Bronze/Silver/Gold
* Retención configurable por capa (políticas por entorno)

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
* Agregar una nueva fuente debe ser mayormente:

  * extractor + config + contract (no “un script nuevo”)
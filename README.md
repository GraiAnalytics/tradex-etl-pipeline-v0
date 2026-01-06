````markdown
# TradeX – Data Pipeline ETL

Pipeline ETL **profesional y escalable** para **TradeX**, orientado a la ingestión, normalización y generación de **señales accionables para el mercado financiero** a partir de:

- datos alternativos (X/Twitter, Reddit, YouTube, News/RSS, SEC, arXiv, journals)
- datos de mercado (Alpaca)

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

```text
FUENTES EXTERNAS
(X, Reddit, YouTube, RSS, SEC, arXiv, Alpaca)
        |
        v
      BRONZE
   (raw / immutable)
        |
        v
      SILVER
 (clean / canonical)
        |
        v
       GOLD
 (metrics / signals)
        |
        v
 UI / API / ALERTS / ML
````

* **Bronze**: datos crudos, auditables y append-only (`JSONL.gz`, run_id + manifest + `_SUCCESS`)
* **Silver**: datos limpios y canónicos (`Parquet/Iceberg`, entity-resolved)
* **Gold**: data products y señales explicables, listos para serving

La especificación completa de cada capa está en `/docs/architecture`.

---

## 🎯 Objetivos del pipeline

* Ingestar múltiples fuentes heterogéneas sin perder información (**raw payload preservado en Bronze**)
* Normalizar y resolver entidades de forma consistente (`entity_id`)
* Calcular métricas relativas (baselines, deltas, z-scores)
* Detectar señales explicables (spikes, anomalías, divergencias)
* Servir datos listos para UI, alertas y modelos ML
* Permitir reprocesamiento y auditoría completa (**run_id + manifest + state store**)
* Soportar incremental y backfills con la misma lógica (sin hacks)

---

## 🧱 Capas de datos

### 🟤 Bronze (Raw / Ingest)

Bronze es un **log de ingestas inmutable** con commit atómico por `run_id`.

* Copia fiel de las fuentes externas (con envelope estándar)
* Versionado y auditabilidad total
* Metadata técnica (`ingest_time`, `event_time`, `cursor`, `params`)
* Manifiesto por corrida (`manifest.json`) y marcador `_SUCCESS`
* Deduplicación in-run + persistente (Postgres)

Ejemplos de datasets:

* `x.posts`
* `market.daily_prices`
* `reddit.posts`
* `youtube.comments`
* `sec.filings`

📄 Especificación: `docs/architecture/01_bronze.md`

---

### ⚪ Silver (Clean / Canonical)

Silver define la **verdad estructural** del sistema.

* Datos limpios, tipados y normalizados
* Resolución determinística de entidades (`entity_id`)
* Deduplicación semántica
* Manejo de late data y schema drift
* Base confiable para análisis, features y señales

Tablas canónicas:

* `silver_entity_master`
* `silver_social_events`
* `silver_market_daily`

📄 Especificación: `docs/architecture/02_silver.md`

---

### 🟡 Gold (Business / Signals)

Gold es la capa de **productos de datos**.

* Métricas finales (market + social)
* Baselines y features versionadas
* Señales explicables con drivers y confidence
* Tablas optimizadas para UI, feeds y alertas

Ejemplos:

* `gold_market_entity_day`
* `gold_social_entity_day`
* `gold_baselines_entity_day`
* `gold_signal_events`
* `gold_entity_daily_summary`

📄 Especificación: `docs/architecture/03_gold.md`

---

## 🧩 Datasets soportados (v0)

### Social / Alt-data

* **X (Twitter) – Basic (API v2)**
  `x.posts` (recent search con cursor `start_time` + lookback + dedup)
* `reddit.posts`
* `youtube.comments`
* `news.articles_rss`
* `journals.articles_rss`
* `sec.filings`
* `arxiv.papers`

### Market

* **Alpaca**
  `market.daily_prices`

---

## 🛠️ Stack tecnológico

* **Lenguaje**: Python 3.11+
* **Orquestación**: Dagster (Python-first)
* **Storage**: S3-compatible (MinIO dev / S3 prod)
* **Formato**:

  * Bronze: JSONL.gz
  * Silver / Gold: Parquet + Iceberg (o Delta)
* **Estado / Metadata**: Postgres
* **Data Quality**: contracts + quality gates + quarantine
* **Observabilidad**: logs estructurados + métricas por run

---

## 📁 Estructura del repositorio (resumen)

```text
src/tradex_pipeline/
├─ sources/        # extractores por fuente
├─ bronze/         # runner + envelopes + manifests + dedup
├─ silver/         # parsers + transforms + quality
├─ gold/           # metrics + baselines + signals + serving
├─ contracts/      # definición formal de datasets
├─ state/          # cursores, watermarks, dedup (Postgres)
├─ orchestration/  # dagster jobs / schedules
├─ alerts/         # dispatch de alertas
└─ common/         # utilidades compartidas
```

---

## 🚀 Quickstart (local)

### 1️⃣ Requisitos

* Python 3.11+
* Docker + Docker Compose
* Poetry
* Make (opcional)

---

### 2️⃣ Clonar el repositorio

```bash
git clone git@github.com:tradex-ai/tradex-pipeline-etl.git
cd tradex-pipeline-etl
```

---

### 3️⃣ Variables de entorno

```bash
cp .env.example .env
```

Configura al menos:

* X API v2 (Basic)
* Alpaca Market Data
* Storage (MinIO/S3)
* Postgres

---

### 4️⃣ Levantar stack local

```bash
docker-compose up -d
```

Servicios:

* MinIO
* Postgres
* dependencias del pipeline

---

### 5️⃣ Instalar dependencias

```bash
poetry install
poetry shell
```

---

## ▶️ Ejecución de pipelines

> Los datasets se ejecutan con `dataset_key = source.dataset`.

### Bronze

```bash
python -m tradex_pipeline.cli run bronze x.posts
python -m tradex_pipeline.cli run bronze market.daily_prices
```

### Silver

```bash
python -m tradex_pipeline.cli run silver social_events
python -m tradex_pipeline.cli run silver market_daily
```

### Gold

```bash
python -m tradex_pipeline.cli run gold build_metrics
python -m tradex_pipeline.cli run gold detect_signals
python -m tradex_pipeline.cli run gold build_serving
```

---

## 🔁 Backfills

Ejemplo: backfill temporal de X posts

```bash
python -m tradex_pipeline.cli backfill \
  --layer bronze \
  --dataset x.posts \
  --start-date 2025-12-01 \
  --end-date 2025-12-15
```

Reglas:

* Bronze genera nuevos `run_id`
* Dedup evita duplicados
* Silver y Gold se recalculan desde Bronze

---

## 🧪 Data Quality

* Contracts por dataset (`contracts/`)
* Quality gates en Silver y Gold
* Registros inválidos → quarantine
* Fallos críticos bloquean publicación

---

## 📊 Observabilidad

Por cada `run_id` se mide:

* volumen de datos
* latencia por etapa
* errores por tipo
* lag temporal
* drift de esquema

Alertas automáticas ante:

* fallos consecutivos
* anomalías de volumen
* pérdida de frescura

📄 Detalle: `docs/architecture/06_observability.md`

---

## 🔐 Seguridad

* Secrets vía `.env` o secret manager
* Storage cifrado
* Acceso por roles a Bronze / Silver / Gold
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
* Agregar una nueva fuente = extractor + config + contract

---

## 📌 Próximos pasos

1. Revisar `/docs/architecture`
2. Completar `configs/base.yaml`
3. Ejecutar los primeros datasets Bronze
4. Publicar las primeras tablas Silver
5. Activar señales Gold

---

## 📬 Proyecto

**TradeX** es una plataforma enfocada en **señales de mercado basadas en datos alternativos**, combinando ingeniería de datos, modelos financieros/estadísticos, ML/DL y una capa agéntica de IA para alertas rápidas.

```
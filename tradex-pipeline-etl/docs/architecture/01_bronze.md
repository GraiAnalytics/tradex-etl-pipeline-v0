# 01 — Bronze (Raw / Ingest) — TradeX

Este documento define **de forma exacta, genérica y operativa** el funcionamiento de la capa **Bronze** del pipeline ETL de **TradeX**.

Bronze es un **sistema de ingest unificado**, diseñado para manejar **múltiples fuentes heterogéneas** (social, news, research, filings, market data), preservando los datos originales y garantizando:

- auditabilidad total
- reproducibilidad determinística
- idempotencia (re-runs seguros)
- backfills controlados
- escalabilidad horizontal
- independencia de las capas Silver y Gold

Las fuentes actuales (X Basic, Alpaca, Reddit, YouTube, RSS, SEC, arXiv, journals) son **instancias del modelo Bronze**, no casos especiales.

Este documento es **normativo**: la implementación debe adherirse a lo aquí definido.

---

## 0) Stack cerrado (Bronze)

| Componente | Decisión |
|-----------|---------|
| Storage | Object Storage S3-compatible (MinIO dev / S3 prod) |
| Formato de archivos | JSON Lines comprimido (`.jsonl.gz`) |
| Estado y metadata | Postgres |
| Orquestación | Dagster |
| Identificador de corrida | ULID (ordenable por tiempo) |
| Compresión | gzip |
| Timezone | UTC |
| Consumo downstream | solo runs con `_SUCCESS` |

---

## 1) Qué es Bronze (definición exacta)

**Bronze NO es una tabla ni una vista.**

Bronze es un **log de ingestas inmutable**, donde:

- cada ejecución genera un **run**
- cada run tiene un `run_id` único
- cada run se escribe de forma atómica
- cada run es auditable y reproducible

Bronze existe para **capturar lo que llegó desde la fuente**, no para interpretar ni corregir datos.

---

## 2) Principios de diseño de Bronze

Bronze sigue estrictamente estos principios:

1. **Inmutabilidad**
   - Una vez escrito un run, nunca se modifica.
2. **Separación de responsabilidades**
   - Bronze ingesta → Silver normaliza → Gold modela negocio.
3. **Fuente de verdad histórica**
   - Silver y Gold pueden reconstruirse desde Bronze sin llamar APIs externas.
4. **Idempotencia**
   - Re-ejecutar el mismo rango no duplica datos.
5. **Contrato único**
   - Todas las fuentes siguen el mismo modelo (envelope + manifest).

---

## 3) Modelo de dataset Bronze

Un *dataset Bronze* se identifica por:

```

dataset_key = "<source_system>.<dataset>"

```

Ejemplos:
- `x.posts`
- `reddit.posts`
- `youtube.comments`
- `news.articles_rss`
- `journals.articles_rss`
- `sec.filings`
- `arxiv.papers`
- `market.daily_prices`

Agregar un nuevo dataset Bronze requiere únicamente:
1. un extractor
2. un contrato
3. configuración

La arquitectura **no cambia**.

---

## 4) Datasets Bronze soportados (v0)

| dataset_key | Fuente | Dominio |
|------------|-------|---------|
| `x.posts` | X (Twitter) API v2 – Basic | Social |
| `reddit.posts` | Reddit API | Social |
| `youtube.comments` | YouTube API | Social |
| `news.articles_rss` | RSS News | News |
| `journals.articles_rss` | Journals RSS | Research |
| `sec.filings` | SEC EDGAR | Filings |
| `arxiv.papers` | arXiv API | Research |
| `market.daily_prices` | Alpaca Market Data | Market |

> Esta lista crecerá; el sistema Bronze **no requiere cambios** para nuevas fuentes.

---

## 5) Layout EXACTO en S3 / MinIO

Bronze se particiona por **ingestión**, no por fecha del evento.

```

s3://<bucket>/<prefix>/bronze/
source_system=<source_system>/
dataset=<dataset>/
ingest_date=YYYY-MM-DD/
run_id=<run_id>/
part-00000.jsonl.gz
part-00001.jsonl.gz
manifest.json
_SUCCESS

```

Ejemplo:
```

bronze/source_system=x/dataset=posts/ingest_date=2026-01-06/run_id=01JH.../

````

### Regla inmutable
Las capas downstream (**Silver, Gold**) **solo consumen runs que contengan `_SUCCESS`**.

---

## 6) Run ID y control temporal

- `run_id`: ULID generado al inicio del job
- `ingest_date`: fecha UTC del inicio del run
- `started_at`, `finished_at`: timestamps UTC (`ISO8601Z`)
- `ingest_time`: timestamp UTC por registro (momento de persistencia)

---

## 7) Bronze Envelope (schema estándar por registro)

Cada línea del archivo `.jsonl.gz` representa **un registro Bronze** con el siguiente envelope:

```json
{
  "schema_version": "bronze-envelope/1.0",

  "dataset_key": "x.posts",
  "source_system": "x",
  "dataset": "posts",

  "run_id": "01JH...",
  "ingest_time": "2026-01-06T13:05:22.123Z",

  "event_time": "2026-01-06T12:59:57Z",
  "source_record_id": "1876123456789012345",

  "extraction": {
    "mode": "incremental | backfill",
    "cursor": {
      "type": "start_time | date | page_token | none",
      "value": "..."
    },
    "params": {
      "...": "dataset-specific params"
    }
  },

  "raw_payload": {
    "...": "payload original de la fuente"
  },

  "raw_payload_hash": "sha256:...",
  "dedup_key": "<dataset_key>:<id-or-hash>"
}
````

### Reglas globales del envelope

* `raw_payload` **nunca se modifica**
* `raw_payload_hash = sha256(canonical_json(raw_payload))`
* `dedup_key`:

  * si existe ID nativo → `{dataset_key}:{source_record_id}`
  * si no existe → `{dataset_key}:{raw_payload_hash}`

---

## 8) Manifest por run (`manifest.json`)

Cada run genera un `manifest.json` con metadata completa de ejecución:

Incluye:

* identificación del run
* cursores start/end
* parámetros de extracción
* conteos
* archivos escritos
* métricas de errores y latencia

El manifest es la **fuente de verdad operativa** para auditoría y debugging.

---

## 9) Atomic Commit (obligatorio)

Bronze usa commit atómico por run:

1. escribir archivos en `_tmp/`
2. validar integridad y conteos
3. mover a path final
4. crear `_SUCCESS`
5. actualizar estado en Postgres

Si falla antes de `_SUCCESS`, el run **no existe para downstream**.

---

## 10) File sizing

* Tamaño objetivo comprimido: **128 MB**
* Rango aceptable: 64–256 MB
* El writer rota por tamaño o número de registros

Evitar *small files* es obligatorio.

---

## 11) Deduplicación e idempotencia

Bronze implementa deduplicación en dos niveles:

### Nivel 1 — In-memory (por run)

* evita duplicados dentro de la misma ejecución

### Nivel 2 — Persistente (Postgres)

Tabla: `bronze_record_index`

* PK: `(dataset_key, dedup_key)`
* evita duplicados entre:

  * re-runs
  * lookbacks
  * backfills

Esto garantiza idempotencia real.

---

## 12) Estado incremental (pipeline_state)

Bronze mantiene estado por dataset:

| Campo                     | Uso                  |
| ------------------------- | -------------------- |
| last_success_cursor_type  | tipo de cursor       |
| last_success_cursor_value | último valor exitoso |
| last_success_event_time   | opcional             |
| last_success_run_id       | auditoría            |

**Solo runs SUCCESS avanzan el estado.**

---

## 13) Dataset specs (ejemplos normativos)

### `x.posts` — X API v2 (Basic)

* Cursor: `start_time`
* Lookback: 120 minutos
* event_time: `created_at`
* Dedup: `tweet_id`

### `market.daily_prices` — Alpaca

* Cursor: `date`
* event_time: `dateT00:00:00Z`
* Dedup: `{symbol}:{date}:alpaca`

Otras fuentes siguen **exactamente el mismo modelo Bronze**.

---

## 14) Manejo de errores

| Error                | Acción                   |
| -------------------- | ------------------------ |
| 429                  | retry + backoff + jitter |
| timeout              | retry                    |
| 5xx                  | retry                    |
| error de escritura   | FAIL run                 |
| parse error aislado  | skip + count             |
| parse error > umbral | FAIL run                 |

Un run `FAILED` **no actualiza estado**.

---

## 15) Backfills

* Backfill = run normal (`extraction.mode = backfill`)
* No pisa runs previos
* Dedup evita duplicados
* Estado solo avanza con `SUCCESS`

---

## 16) Definition of Done — Bronze

Bronze está listo cuando:

* cualquier dataset genera runs con:

  * layout estándar
  * envelope válido
  * manifest válido
  * `_SUCCESS`
* re-runs no duplican datos
* backfills no rompen incremental
* Silver consume sin lógica especial por fuente

---

## 17) Principio rector

> **Bronze es genérico.
> Las fuentes son plugins.
> El contrato no cambia.**

Este principio es la base para que TradeX escale en fuentes, volumen y complejidad **sin deuda técnica**.
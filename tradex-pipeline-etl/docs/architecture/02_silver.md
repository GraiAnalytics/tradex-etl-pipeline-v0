# 02 — Silver (Clean / Canonical) — TradeX

Este documento define **de forma exacta, genérica y operativa** el funcionamiento de la capa **Silver** del pipeline ETL de **TradeX**.

Silver es la **capa canónica de datos** del sistema. Su responsabilidad es transformar datos **Bronze crudos y auditables** en datasets:

- limpios
- tipados
- normalizados
- consistentes entre fuentes
- resolviendo entidades
- confiables para análisis, features y señales

Silver **NO contiene lógica de negocio final ni señales**.  
Silver define **la verdad estructural** sobre la cual Gold construye productos de datos.

Este documento es **normativo**: la implementación debe adherirse a lo aquí definido.

---

## 0) Stack cerrado (Silver)

| Componente | Decisión |
|-----------|---------|
| Storage | Object Storage S3-compatible |
| Formato | Parquet |
| Table format | Iceberg (preferido) / Delta (alternativo) |
| Estado | Derivado de Bronze (`_SUCCESS`) |
| Orquestación | Dagster |
| Timezone | UTC |
| Particionamiento | por `event_date` |
| Consumo downstream | solo tablas publicadas |

---

## 1) Qué es Silver (definición exacta)

**Silver NO es raw.  
Silver NO es Gold.**

Silver es la **representación canónica y normalizada** de los datos de TradeX.

Silver existe para:

- eliminar inconsistencias de formato
- aplicar tipado fuerte
- unificar múltiples fuentes bajo un mismo modelo
- resolver entidades (`entity_id`)
- manejar late data
- preparar datos para agregación y feature engineering

Silver **no debe contener decisiones de negocio**, thresholds ni clasificaciones finales.

---

## 2) Principios de diseño de Silver

Silver se rige por estos principios estrictos:

1. **Determinismo**
   - A mismo input Bronze → mismo output Silver.
2. **Idempotencia**
   - Reprocesar no genera duplicados.
3. **Canonización**
   - Un concepto tiene **un solo esquema canónico**.
4. **Separación**
   - Silver no conoce UI ni alertas.
5. **Auditabilidad**
   - Cada registro Silver es rastreable a Bronze (`run_id`, `source_record_id`).

---

## 3) Inputs de Silver

Silver **solo consume Bronze** y **solo runs con `_SUCCESS`**.

### Fuente de verdad
- Archivos `part-*.jsonl.gz`
- `manifest.json`
- `_SUCCESS`

Silver **nunca**:
- llama APIs externas
- infiere estado fuera de Bronze
- modifica Bronze

---

## 4) Outputs de Silver

Silver publica **tablas canónicas** versionadas y optimizadas para lectura analítica.

### Tipos de tablas Silver

1. **Entity master**
   - catálogos de entidades
2. **Event tables**
   - eventos normalizados (social, news, filings)
3. **Time series**
   - series temporales limpias (market)

---

## 5) Datasets Silver definidos (v0)

| Dataset | Descripción |
|------|-----------|
| `silver_entity_master` | Catálogo canónico de entidades |
| `silver_social_events` | Eventos sociales normalizados |
| `silver_market_daily` | Series de mercado diarias |

> Nuevas tablas Silver deben **derivarse de Bronze** y seguir este documento.

---

## 6) Layout lógico de Silver

Silver se organiza por **tabla canónica**, no por fuente.

```

silver/
<table_name>/
event_date=YYYY-MM-DD/
part-00000.parquet

```

Ejemplo:
```

silver/silver_social_events/event_date=2026-01-06/part-00000.parquet

````

---

## 7) Esquemas canónicos (normativos)

### 7.1 `silver_entity_master`

```text
entity_id            STRING   (PK)
entity_type          STRING   (company | crypto | macro)
canonical_name       STRING
ticker               STRING
isin                 STRING
country              STRING
sector               STRING
industry             STRING
first_seen_at        TIMESTAMP (UTC)
last_seen_at         TIMESTAMP (UTC)
source_confidence    FLOAT
````

---

### 7.2 `silver_social_events`

```text
event_id             STRING   (PK)
entity_id            STRING   (FK)
platform             STRING   (x | reddit | youtube | news | journals)
event_time           TIMESTAMP (UTC)
event_date           DATE
text                 STRING
language              STRING
engagement_score     FLOAT
source_system        STRING
source_record_id     STRING
bronze_run_id        STRING
```

---

### 7.3 `silver_market_daily`

```text
entity_id            STRING   (FK)
date                 DATE
open_price           FLOAT
close_price          FLOAT
high_price           FLOAT
low_price            FLOAT
volume               FLOAT
returns_1d           FLOAT
source_system        STRING
bronze_run_id        STRING
```

---

## 8) Transformaciones Silver (exactas)

Silver aplica transformaciones **determinísticas**:

### 8.1 Parsing y tipado

* timestamps → UTC
* fechas → `DATE`
* floats normalizados
* strings limpiados (trim, unicode)

---

### 8.2 Normalización de texto

* lowercasing (opcional por campo)
* eliminación de control chars
* normalización unicode
* preservación de texto original semántico

---

### 8.3 Resolución de entidades

Silver **resuelve entidades** a un `entity_id` canónico usando:

* tickers (`AAPL`)
* símbolos (`$AAPL`)
* mapeos externos
* reglas determinísticas

**Nunca ML en Silver.**

---

### 8.4 Deduplicación semántica

Silver elimina duplicados cuando:

* mismo `entity_id`
* mismo `event_time` (o ventana corta)
* texto equivalente (hash semántico)

Silver **no depende** del dedup de Bronze.

---

## 9) Late data handling

Silver permite late data:

* Ventana configurable (ej: 7 días)
* Reprocesa particiones afectadas
* No rompe consistencia global

---

## 10) Data Quality (Silver)

Silver aplica **quality gates obligatorios**.

### Ejemplos de checks

| Check               | Acción |
| ------------------- | ------ |
| `entity_id` nulo    | FAIL   |
| `event_time` nulo   | FAIL   |
| `volume < 0`        | FAIL   |
| `language` inválido | WARN   |
| % nulos > umbral    | FAIL   |

Registros inválidos → **quarantine**.

---

## 11) Idempotencia y reprocessing

Silver es **totalmente reproducible**:

* mismas entradas Bronze → mismas salidas Silver
* reprocesar una partición:

  * borra
  * reescribe
  * publica

No existen *append-only hacks*.

---

## 12) Versionado de Silver

* Cambios de esquema → nueva versión de tabla
* Cambios backward-compatible → mismo esquema
* Versionado explícito en contracts

Silver **no muta silenciosamente**.

---

## 13) Orquestación Silver

Silver se ejecuta como jobs Dagster:

* dependientes de Bronze `_SUCCESS`
* por partición (`event_date`)
* con retries controlados

---

## 14) Definition of Done — Silver

Silver está listo cuando:

* cada tabla canónica:

  * tiene esquema estable
  * tiene checks de calidad
  * es reproducible
* no depende de la fuente original
* puede alimentar Gold sin lógica adicional

---

## 15) Principio rector

> **Silver es la verdad estructural.
> No interpreta.
> No decide.
> Solo canoniza.**

Esta capa es lo que permite que TradeX tenga señales confiables y explicables.
# 06 — Observability, SLAs & Operations — TradeX

Este documento define **de forma exacta, operativa y accionable** el sistema de **observabilidad, SLAs, alertas y operación** del pipeline ETL de **TradeX**.

La observabilidad en TradeX **no es decorativa**: es un requisito funcional para garantizar:

- confiabilidad de señales
- detección temprana de fallos
- control de costos
- operación segura en producción
- auditoría end-to-end

Este documento es **normativo**: cualquier componente del pipeline debe exponer las métricas aquí definidas.

---

## 1) Qué significa observabilidad en TradeX

Observabilidad en TradeX implica poder responder **en tiempo real** a:

1. ¿Qué datasets se están ingiriendo ahora?
2. ¿Cuándo fue el último dato válido por dataset?
3. ¿Hay lag respecto al tiempo real?
4. ¿Qué runs fallaron y por qué?
5. ¿Se están generando señales con datos incompletos?
6. ¿El volumen actual es anómalo?

---

## 2) Pilares de observabilidad

TradeX implementa los **tres pilares clásicos**, con foco en pipelines de datos:

### 2.1 Logs
- logs estructurados
- correlados por `run_id`
- nivelados (INFO / WARN / ERROR)

### 2.2 Métricas
- contadores
- gauges
- histogramas
- expuestas por dataset y capa

### 2.3 Trazas (opcional)
- duración de etapas
- dependencias entre capas
- útil para debugging profundo

---

## 3) Identidad operacional

Todo evento observable debe incluir:

| Campo | Uso |
|----|----|
| `run_id` | correlación |
| `dataset_key` | granularidad |
| `layer` | bronze / silver / gold |
| `environment` | dev / staging / prod |
| `job_name` | orquestación |
| `timestamp` | análisis temporal |

Sin estos campos, el evento es **inválido**.

---

## 4) Métricas obligatorias por capa

### 4.1 Métricas Bronze

Por `dataset_key` y `run_id`:

| Métrica | Tipo | Descripción |
|------|----|------------|
| `records_fetched` | counter | registros recibidos desde la fuente |
| `records_written` | counter | registros persistidos |
| `records_deduped` | counter | descartados por dedup |
| `records_failed` | counter | registros inválidos |
| `run_duration_seconds` | histogram | duración total del run |
| `api_429_count` | counter | rate limits |
| `api_5xx_count` | counter | errores de servidor |
| `cursor_lag_seconds` | gauge | lag del cursor vs now |

---

### 4.2 Métricas Silver

Por tabla y partición:

| Métrica | Tipo | Descripción |
|------|----|------------|
| `records_input` | counter | registros leídos desde Bronze |
| `records_output` | counter | registros publicados |
| `records_quarantined` | counter | enviados a quarantine |
| `null_ratio` | gauge | % de nulos por campo crítico |
| `late_data_count` | counter | eventos fuera de watermark |
| `partition_build_seconds` | histogram | tiempo por partición |

---

### 4.3 Métricas Gold

Por dataset y fecha:

| Métrica | Tipo | Descripción |
|------|----|------------|
| `entities_processed` | counter | entidades evaluadas |
| `signals_generated` | counter | señales creadas |
| `signals_high_severity` | counter | señales críticas |
| `feature_build_seconds` | histogram | tiempo de features |
| `signal_build_seconds` | histogram | tiempo de señales |

---

## 5) Métricas de estado y lag

Estas métricas son **críticas para producción**.

| Métrica | Descripción |
|------|------------|
| `bronze_cursor_lag_minutes` | atraso vs tiempo real |
| `silver_watermark_lag_days` | atraso de completitud |
| `gold_freshness_hours` | edad de señales |
| `runs_failed_consecutive` | fallos seguidos |

---

## 6) SLAs formales (v0)

### 6.1 Bronze

| Dataset | SLA |
|------|----|
| Social (X, Reddit, YT) | < 15 min |
| Market (daily) | < 2 h desde close |

---

### 6.2 Silver

| Tabla | SLA |
|----|----|
| `silver_social_events` | < 30 min desde Bronze |
| `silver_market_daily` | < 1 h |

---

### 6.3 Gold

| Producto | SLA |
|------|----|
| Métricas | < 1 h |
| Señales | < 90 min |
| Serving tables | < 2 h |

---

## 7) Alertas obligatorias

### 7.1 Alertas de fallo

| Condición | Severidad |
|--------|-----------|
| Run FAILED | HIGH |
| 3 runs fallidos consecutivos | CRITICAL |
| Error de escritura | CRITICAL |

---

### 7.2 Alertas de datos

| Condición | Severidad |
|--------|-----------|
| Caída de volumen > 40% | HIGH |
| Pico de volumen inesperado | MEDIUM |
| Null ratio > umbral | HIGH |
| Señales sin drivers | CRITICAL |

---

### 7.3 Alertas de frescura

| Condición | Severidad |
|--------|-----------|
| Bronze lag > SLA | HIGH |
| Silver watermark atrasado | MEDIUM |
| Gold freshness > SLA | HIGH |

---

## 8) Dashboards recomendados

TradeX debe exponer dashboards por:

1. **Estado general**
2. **Bronze ingest**
3. **Silver quality**
4. **Gold signals**
5. **Backfills**

Cada dashboard debe permitir:
- filtrar por dataset
- filtrar por fecha
- drill-down por `run_id`

---

## 9) Runbooks operativos

Cada alerta crítica debe tener un **runbook asociado**.

Ejemplos:
- `runbooks/bronze_x_posts_failed.md`
- `runbooks/silver_quality_drop.md`
- `runbooks/gold_signal_spike.md`

Un runbook debe incluir:
- síntomas
- causa probable
- pasos de mitigación
- validación post-fix

---

## 10) Auditoría end-to-end

Para cualquier señal Gold debe ser posible responder:

1. ¿Qué señal?
2. ¿Cuándo se generó?
3. ¿Qué drivers la causaron?
4. ¿Qué datos Silver la alimentaron?
5. ¿Qué runs Bronze están detrás?

Esto es **obligatorio** para TradeX.

---

## 11) Cost observability

TradeX monitorea costos indirectos:

- número de runs
- volumen ingerido
- volumen reprocesado
- tamaño de backfills

Alertas si:
- backfill excede presupuesto
- crecimiento anómalo de storage

---

## 12) Testing y observabilidad

Todo job debe exponer métricas incluso en tests:

- tests unitarios validan métricas mínimas
- tests de integración validan SLAs básicos
- fallar métricas críticas = test fail

---

## 13) Definition of Done — Observability

El sistema es observable cuando:

- cada run es rastreable
- cada fallo dispara alerta
- cada SLA es medible
- cada señal es auditable
- la operación no depende de “mirar logs a mano”

---

## 14) Principio rector

> **Si no se puede observar,  
> no se puede confiar.**

La observabilidad es lo que convierte el pipeline de TradeX en un **sistema operable en producción real**.
# 03 — Gold (Business / Features / Signals) — TradeX

Este documento define **de forma exacta, genérica y operativa** el funcionamiento de la capa **Gold** del pipeline ETL de **TradeX**.

Gold es la **capa de productos de datos** del sistema.  
Aquí los datos **ya no son solo correctos**, sino **útiles para la toma de decisiones**.

Gold transforma datos **Silver canónicos** en:

- métricas de negocio
- baselines y features versionadas
- señales explicables
- tablas optimizadas para serving (UI, alertas, ML)

Este documento es **normativo**: la implementación debe adherirse a lo aquí definido.

---

## 0) Stack cerrado (Gold)

| Componente | Decisión |
|-----------|---------|
| Storage | Object Storage S3-compatible |
| Formato | Parquet |
| Table format | Iceberg (preferido) / Delta |
| Orquestación | Dagster |
| Timezone | UTC |
| Particionamiento | por `date` |
| Consumo | UI / API / Alerts / ML |

---

## 1) Qué es Gold (definición exacta)

**Gold NO es raw.  
Gold NO es canónico.**

Gold es una **capa de interpretación controlada**, donde:

- se aplican reglas de negocio explícitas
- se agregan datos temporalmente
- se comparan contra baselines
- se generan señales accionables

Gold **sí puede contener decisiones**, pero **todas deben ser explicables y versionadas**.

---

## 2) Principios de diseño de Gold

Gold se rige por estos principios estrictos:

1. **Explicabilidad**
   - Toda señal debe tener drivers claros.
2. **Versionado explícito**
   - Features y señales tienen versión.
3. **Reproducibilidad**
   - Mismo input Silver → mismo output Gold.
4. **Separación de concerns**
   - Métricas ≠ Features ≠ Señales.
5. **Serving-first**
   - Gold existe para ser consumido.

---

## 3) Inputs de Gold

Gold **solo consume Silver**.

- tablas canónicas (`silver_*`)
- particiones publicadas
- sin dependencias a Bronze ni a APIs externas

Gold **nunca**:
- limpia datos crudos
- resuelve entidades
- corrige inconsistencias estructurales

---

## 4) Outputs de Gold (tipos)

Gold produce **data products** de cuatro tipos:

1. **Métricas**
2. **Baselines**
3. **Features**
4. **Señales**
5. **Serving tables**

Cada tipo tiene responsabilidades claras.

---

## 5) Datasets Gold definidos (v0)

| Dataset | Tipo |
|------|-----|
| `gold_market_entity_day` | Métricas |
| `gold_social_entity_day` | Métricas |
| `gold_baselines_entity_day` | Baselines |
| `gold_entity_day_features` | Features |
| `gold_signal_events` | Señales |
| `gold_entity_daily_summary` | Serving |

---

## 6) Layout lógico de Gold

Gold se organiza por **producto de datos** y por fecha:

```

gold/
<dataset_name>/
date=YYYY-MM-DD/
part-00000.parquet

```

Ejemplo:
```

gold/gold_signal_events/date=2026-01-06/part-00000.parquet

````

---

## 7) Métricas Gold (definición exacta)

Las métricas Gold son **agregaciones determinísticas** sobre Silver.

### Ejemplos de métricas

#### Market
- `price_change_1d`
- `price_change_7d`
- `volatility_30d`
- `volume_vs_baseline`

#### Social
- `mentions_1d`
- `mentions_7d`
- `engagement_score_1d`
- `sentiment_delta_7d` (si aplica)

### Reglas
- Ventanas temporales explícitas
- Fórmulas documentadas
- Sin heurísticas ocultas

---

## 8) Baselines Gold

Los baselines permiten **comparación relativa**, no valores absolutos.

### Tipos de baseline
- rolling mean (ej: 30d)
- rolling std
- EWMA
- percentiles históricos

### Ejemplo
```text
baseline_volume_30d = mean(volume over last 30 days)
volume_vs_baseline = (volume - baseline) / baseline
````

Los baselines:

* se recalculan con historia suficiente
* se versionan
* nunca se mezclan con señales

---

## 9) Features Gold

Las features son **inputs directos para modelos ML o scoring**.

### Principios

* Features ≠ Señales
* No hay labels en Gold
* Cada feature tiene:

  * nombre estable
  * definición formal
  * versión

### Ejemplos

* `social_activity_zscore_7d`
* `volume_spike_score`
* `price_momentum_30d`

---

## 10) Señales Gold (núcleo de TradeX)

Una **señal** es un evento interpretable que indica un **cambio relevante**.

### Qué es una señal

* no es un raw metric
* no es un threshold trivial
* es una **conclusión basada en múltiples inputs**

---

### Esquema normativo — `gold_signal_events`

```text
signal_id            STRING (PK)
entity_id            STRING
signal_type          STRING
signal_version       STRING
date                 DATE
confidence           FLOAT (0–1)
severity             STRING (low | medium | high)
drivers              ARRAY<STRUCT<
  name STRING,
  value FLOAT,
  baseline FLOAT,
  delta FLOAT
>>
explanation           STRING
created_at           TIMESTAMP (UTC)
```

---

### Ejemplos de señales

* **Unusual Volume**
* **Social Spike**
* **Price–Social Divergence**
* **Volatility Regime Change**

Cada señal:

* debe indicar **por qué ocurrió**
* debe poder auditarse hacia Silver
* no debe ser una “caja negra”

---

## 11) Scoring y confianza

Gold asigna **confidence scores** a señales usando:

* estabilidad histórica
* fuerza relativa vs baseline
* consenso entre drivers

**Nunca**:

* heurísticas mágicas
* scores no reproducibles

---

## 12) Serving Tables

Gold genera tablas **optimizadas para consumo**:

### Ejemplo — `gold_entity_daily_summary`

Incluye:

* métricas clave
* señales activas
* contexto temporal
* texto explicativo

Estas tablas:

* evitan joins complejos en UI
* permiten APIs simples
* soportan alertas near-real-time

---

## 13) Data Quality (Gold)

Gold aplica quality gates estrictos:

| Check                     | Acción |
| ------------------------- | ------ |
| signal sin drivers        | FAIL   |
| confidence fuera de rango | FAIL   |
| entity_id nulo            | FAIL   |
| métricas NaN              | FAIL   |
| % señales erráticas       | WARN   |

---

## 14) Idempotencia y reprocessing

Gold es **completamente reproducible**:

* re-ejecutar una fecha:

  * borra
  * recalcula
  * publica

No existen *side effects*.

---

## 15) Versionado (obligatorio)

Todo en Gold se versiona:

* `metric_version`
* `baseline_version`
* `feature_version`
* `signal_version`

Cambios de lógica → **nueva versión**, nunca overwrite silencioso.

---

## 16) Orquestación Gold

Gold se ejecuta vía Dagster:

* dependencias explícitas a Silver
* jobs separados:

  * métricas
  * baselines
  * features
  * señales
  * serving
* retries controlados

---

## 17) Definition of Done — Gold

Gold está listo cuando:

* las métricas son estables y documentadas
* los baselines son consistentes
* las señales son explicables
* las tablas sirven directamente a UI y alertas
* no se requieren transformaciones adicionales downstream

---

## 18) Principio rector

> **Gold no adivina.
> Gold explica.
> Gold decide con evidencia.**

Esta capa es lo que convierte datos en **valor real** para TradeX.
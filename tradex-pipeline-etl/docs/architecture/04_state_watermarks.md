# 04 — State, Cursors & Watermarks — TradeX

Este documento define **de forma exacta, genérica y operativa** cómo TradeX maneja el **estado del pipeline**, los **cursores de ingesta**, los **watermarks temporales** y el **late data** a lo largo de las capas **Bronze, Silver y Gold**.

El objetivo es garantizar:

- ingest incremental correcta
- ausencia de huecos y duplicados
- reprocessing seguro
- backfills controlados
- reproducibilidad total

Este documento es **normativo**: la implementación debe seguirlo tal cual.

---

## 1) Conceptos clave (definiciones)

### 1.1 Estado (State)
Información persistente que permite al pipeline **continuar donde quedó**.

### 1.2 Cursor
Valor concreto utilizado para pedir datos a una fuente o para avanzar procesamiento.

Ejemplos:
- `start_time` (X)
- `date` (market)
- `page_token` (RSS, APIs paginadas)

### 1.3 Watermark
Marca temporal que indica **hasta dónde el sistema considera los datos “completos”**.

### 1.4 Late data
Eventos cuyo `event_time` es **anterior al watermark** pero llegan tarde.

---

## 2) Principios de diseño

1. **El estado es explícito y versionado**
2. **Solo runs SUCCESS avanzan el estado**
3. **Cursores ≠ watermarks**
4. **El sistema favorece duplicar y deduplicar antes que perder datos**
5. **Reprocessing es un camino de primera clase**

---

## 3) State Store (arquitectura)

TradeX mantiene estado en **Postgres**.

### Tablas principales

| Tabla | Propósito |
|-----|----------|
| `pipeline_state` | Estado incremental por dataset |
| `bronze_runs` | Auditoría de runs Bronze |
| `bronze_record_index` | Deduplicación persistente |
| `silver_partitions` | Particiones Silver publicadas |
| `gold_partitions` | Particiones Gold publicadas |

---

## 4) `pipeline_state` (definición exacta)

Una fila por `dataset_key`.

```text
dataset_key                  STRING (PK)
last_success_cursor_type     STRING
last_success_cursor_value    STRING
last_success_event_time      TIMESTAMP (UTC)
last_success_run_id          STRING
updated_at                   TIMESTAMP (UTC)
````

### Reglas

* Se actualiza **solo al finalizar un run SUCCESS**
* Nunca retrocede automáticamente
* Puede ser sobrescrito solo vía backfill controlado

---

## 5) Cursores por capa

### 5.1 Bronze

Bronze mantiene cursores **por dataset** y **por fuente**.

| Tipo de cursor | Ejemplos               |
| -------------- | ---------------------- |
| Temporal       | `start_time`, `date`   |
| Paginación     | `page_token`, `offset` |
| Ninguno        | datasets full snapshot |

Bronze guarda:

* cursor start (desde state)
* cursor end (definido al finalizar run)

---

### 5.2 Silver

Silver **no mantiene cursores externos**.

Silver avanza por:

* particiones (`event_date`)
* disponibilidad de Bronze `_SUCCESS`

Silver usa **watermarks temporales** (ver sección 6).

---

### 5.3 Gold

Gold no maneja cursores de fuente.

Gold avanza por:

* fechas (`date`)
* dependencias Silver completas

---

## 6) Watermarks (definición exacta)

### 6.1 Bronze watermark

Bronze **no define watermark global**.

Bronze solo garantiza:

* qué se pidió
* qué se escribió
* con qué cursor

La completitud temporal **no se asume** en Bronze.

---

### 6.2 Silver watermark

Silver mantiene un **watermark temporal por tabla**:

```
silver_watermark = max(event_time) - allowed_lateness
```

Ejemplo:

* `allowed_lateness = 7 días`
* watermark = `2026-01-06T00:00:00Z`

Silver considera:

* datos con `event_time < watermark` → estables
* datos >= watermark → potencialmente incompletos

---

### 6.3 Gold watermark

Gold usa watermarks derivados de Silver.

Gold solo procesa fechas **≤ watermark Silver**.

Esto evita:

* señales con datos incompletos
* re-triggers innecesarios

---

## 7) Late data handling

### 7.1 Bronze

* Bronze **acepta late data siempre**
* Dedup evita doble conteo
* No existe rechazo por tiempo

---

### 7.2 Silver

* Silver permite late data dentro de `allowed_lateness`
* Reprocesa particiones afectadas
* Actualiza watermark cuando corresponde

---

### 7.3 Gold

* Gold solo se recalcula cuando:

  * cambia Silver bajo el watermark
  * o se ejecuta backfill explícito

---

## 8) Ventanas de reprocesamiento

Silver y Gold definen ventanas explícitas:

| Capa   | Ventana típica |
| ------ | -------------- |
| Silver | 7 días         |
| Gold   | 7–30 días      |

Estas ventanas:

* limitan el costo
* controlan recomputación
* permiten late data

---

## 9) Backfills (interacción con estado)

### Tipos de backfill

1. **Temporal**

   * rango de fechas
2. **Dataset**

   * dataset completo
3. **Lógico**

   * cambio de lógica

### Reglas

* Backfill **no pisa** runs previos
* Backfill puede sobrescribir `pipeline_state` solo si es explícito
* Dedup protege consistencia

---

## 10) Casos típicos (ejemplos)

### 10.1 X Basic (out-of-order)

* Se usa `start_time`
* Lookback amplio
* Dedup persistente
* Silver resuelve orden final

---

### 10.2 Market daily (ordenado)

* Cursor por fecha
* No requiere lookback
* Watermark natural diario

---

## 11) Errores y recuperación

| Situación           | Acción                   |
| ------------------- | ------------------------ |
| Run FAILED          | no avanza cursor         |
| Run SUCCESS parcial | no permitido             |
| Pérdida de estado   | reconstruir desde Bronze |
| Bug en Silver       | reprocesar particiones   |
| Bug en Gold         | reprocesar fechas        |

---

## 12) Observabilidad del estado

TradeX expone métricas de estado:

* lag del cursor
* lag vs wall-clock
* diferencia watermark vs now
* runs fallidos consecutivos

Estas métricas alimentan alertas.

---

## 13) Definition of Done — State & Watermarks

El sistema de estado está correcto cuando:

* no hay huecos temporales
* no hay duplicados
* late data es absorbido correctamente
* reprocessing es seguro y reproducible
* Gold no produce señales con datos incompletos

---

## 14) Principio rector

> **El estado nunca es implícito.
> Los cursores avanzan solo con éxito.
> Los watermarks protegen la verdad temporal.**

Este diseño es lo que permite que TradeX escale sin perder control.
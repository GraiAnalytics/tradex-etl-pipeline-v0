# 05 — Backfills & Reprocessing — TradeX

Este documento define **de forma exacta, controlada y operativa** cómo TradeX ejecuta **backfills y reprocesamientos** a lo largo de las capas **Bronze, Silver y Gold**.

El objetivo del sistema de backfills es permitir:

- reprocesar historia sin perder auditabilidad
- corregir bugs lógicos o de datos
- absorber late data masivo
- recalcular métricas y señales
- mantener reproducibilidad total

Este documento es **normativo**: cualquier backfill debe seguir estas reglas.

---

## 1) Qué es un backfill (definición exacta)

Un **backfill** es una ejecución explícita del pipeline sobre datos históricos ya existentes, que:

- **no pisa datos previos**
- **genera nuevos runs / particiones**
- **respeta deduplicación**
- **es completamente auditable**

Un backfill **no es**:
- un overwrite silencioso
- una corrección manual
- una mutación directa de Bronze/Silver/Gold

---

## 2) Principios de diseño de backfills

1. **Nada se borra sin intención explícita**
2. **Todo backfill es un run formal**
3. **Bronze es append-only**
4. **Silver y Gold son recalculables**
5. **El estado nunca avanza implícitamente**
6. **El costo del backfill es controlado**

---

## 3) Tipos de backfill soportados

TradeX soporta **cuatro tipos formales de backfill**.

---

### 3.1 Backfill temporal

Reprocesa un **rango de fechas**.

Ejemplo:
- “Reprocesar X posts del 1 al 15 de diciembre”

Usos típicos:
- late data
- caídas de API
- lag prolongado

---

### 3.2 Backfill por dataset

Reprocesa **un dataset completo**.

Ejemplo:
- `silver_social_events` completo

Usos típicos:
- bug de parsing
- cambio de normalización
- nueva regla de deduplicación

---

### 3.3 Backfill lógico

Reprocesa datos debido a un **cambio de lógica**.

Ejemplos:
- nueva definición de baseline
- cambio en scoring de señales
- nueva resolución de entidades

Usos típicos:
- evolución del modelo de negocio
- mejoras en señales

---

### 3.4 Backfill forzado (excepcional)

Reprocesamiento que **sobrescribe estado**.

Usos:
- corrección crítica
- data corruption
- error operativo severo

> ⚠️ Requiere aprobación explícita y logging reforzado.

---

## 4) Backfills por capa

### 4.1 Bronze

Bronze **nunca se modifica ni se borra**.

Backfill Bronze significa:
- ejecutar un run con `extraction.mode = backfill`
- generar **nuevos run_id**
- usar cursores explícitos

Dedup garantiza que:
- no se dupliquen registros
- se pueda re-ejecutar sin riesgo

---

### 4.2 Silver

Silver se backfillea por:
- particiones (`event_date`)
- tablas completas (casos raros)

Regla:
- particiones afectadas se **borran y recalculan**
- otras particiones permanecen intactas

Silver **no depende del estado externo**, solo de Bronze.

---

### 4.3 Gold

Gold se backfillea por:
- fechas (`date`)
- versiones de lógica

Regla:
- Gold **siempre se recalcula**
- nunca se edita manualmente

---

## 5) Flujo operativo de un backfill

Ejemplo: backfill temporal end-to-end.

```

BACKFILL REQUEST
↓
Bronze (run backfill, new run_id)
↓
Silver (rebuild affected partitions)
↓
Gold (recompute metrics, baselines, signals)

````

Cada etapa:
- es auditable
- es reversible
- es observable

---

## 6) Interacción con `pipeline_state`

### Reglas estrictas

- Backfill **NO avanza estado por defecto**
- Estado solo avanza con `SUCCESS` incremental
- Backfill puede:
  - leer estado
  - ignorar estado
  - sobrescribir estado **solo si es explícito**

### Flags requeridos

Todo backfill debe declarar:

```text
mode = backfill
override_state = true | false
````

---

## 7) Deduplicación durante backfills

Dedup funciona igual que en runs normales:

* Bronze: dedup persistente
* Silver: dedup semántico
* Gold: agregación determinística

Esto garantiza:

* no duplicar señales
* no inflar métricas
* consistencia histórica

---

## 8) Versionado y backfills lógicos

Cuando un backfill se debe a un **cambio de lógica**:

* se incrementa versión:

  * `baseline_version`
  * `feature_version`
  * `signal_version`
* Gold publica nuevas particiones
* Particiones antiguas pueden:

  * mantenerse (auditoría)
  * marcarse como deprecated

Nunca se “corrige” una versión pasada silenciosamente.

---

## 9) Orquestación de backfills

Backfills se ejecutan vía Dagster con:

* jobs dedicados
* límites de concurrencia
* prioridades bajas (por defecto)
* observabilidad reforzada

Ejemplo:

```text
dagster job: backfill_bronze_x_posts
dagster job: backfill_silver_social_events
dagster job: backfill_gold_signals
```

---

## 10) Cost control

Backfills pueden ser costosos.

TradeX aplica:

* ventanas de reprocesamiento limitadas
* batch sizes controlados
* cuotas de concurrencia
* dry-run opcional (planificación)

---

## 11) Observabilidad de backfills

Cada backfill registra:

* rango afectado
* datasets impactados
* volumen reprocesado
* duración total
* errores por etapa

Backfills generan alertas si:

* fallan
* exceden SLA
* producen anomalías de volumen

---

## 12) Errores comunes y mitigaciones

| Error                          | Mitigación           |
| ------------------------------ | -------------------- |
| Backfill muy grande            | dividir por ventanas |
| Reprocesar sin dedup           | prohibido            |
| Avanzar estado accidentalmente | flags obligatorios   |
| Cambiar lógica sin versionar   | prohibido            |
| Backfill en peak hours         | usar prioridad baja  |

---

## 13) Definition of Done — Backfills

El sistema de backfills es correcto cuando:

* se puede reprocesar cualquier rango
* no se pierden datos
* no se duplican registros
* la auditoría es completa
* Gold refleja la nueva verdad versionada

---

## 14) Principio rector

> **Nada se borra.
> Todo se puede recalcular.
> El pasado es auditable.**

Este enfoque es lo que permite que TradeX evolucione sin miedo a romper su historia.
# Flujo del motor de simulación

> **Regla de oro:** cada dato nace en un solo lugar y los demás lo leen de ahí.
> Si vas a guardar algo, primero pregúntate si ya existe en otro archivo.

## Recorrido de una simulación

Se dispara cada vez que el usuario da clic en "Simular" (`python main.py`).

```
escenario (JSON)
      │
      ▼
main.simular_escenario
      │
      ├─ 1. Preparación (por escenario)
      │      scenario_builder      → red del escenario (.net.xml)
      │      escenario_demanda     → rutas (.rou.xml)
      │      data_generators       → configuración (.sumocfg)
      │
      ├─ 2. simulation_engine.ejecutar_simulacion  (TraCI + SUMO)
      │      escribe: tripinfo.xml, queue.xml, resumen_ejecucion.json, trayectorias.json
      │      devuelve en memoria: {archivo_resultados (tripinfo.xml), semaforos}
      │
      ├─ 3. main.armar_indicadores
      │      indicadores.calcular_indicadores  ← lee tripinfo, queue, resumen_ejecucion
      │      + flujos (si el escenario los define)
      │      + semáforos (vienen del motor, en memoria)
      │
      ├─ 4. gestion_reportes.guardar_escenario → indicadores.json (Resumen de la simulacion del escenario mas  la info del esceneario y sus indicadores)
      │
      ├─ 5. gestion_reportes.generar_reporte   → reporte.pdf  (lee SOLO indicadores.json)
      │
      └─ 6. main.enviar_indicadores            → POST /resultado-sumo (backend)
```

La red base del proyecto (`obtener_red_base`) se importa **una sola vez** por proyecto y se reutiliza.

## Qué hace cada módulo

| Módulo | Responsabilidad | No debe hacer |
|---|---|---|
| `main.py` | Orquesta los pasos y junta los datos | Calcular métricas |
| `simulation_engine.py` | Correr SUMO y medir lo que solo existe con TraCI vivo (retraso por semáforo, trayectorias) | Interpretar resultados ni generar reportes |
| `indicadores.py` | Convertir los archivos crudos en KPIs | Correr SUMO ni dibujar PDFs |
| `gestion_reportes.py` | Guardar `indicadores.json` y pedir el PDF | Calcular KPIs |
| `reporte.py` | Dibujar el PDF a partir de indicadores | Leer archivos crudos de SUMO |
| `comparar_escenarios.py` | Calcular cambios porcentuales contra el base | Dibujar nada |

## Archivos que se crean

**Por proyecto (una vez):** el `.osm`, `red_base.net.xml` y  `geojson`.

**Por escenario:**

| Archivo | Lo escribe | Para qué sirve |
|---|---|---|
| red del escenario (`.net.xml`), rutas (`.rou.xml`), `.sumocfg` | preparación | entrada de SUMO |
| `tripinfo.xml` | SUMO | un registro por viaje; base de los KPIs |
| `queue.xml` | SUMO | longitud máxima de fila (puede pesar cientos de MB) |
| `resumen_ejecucion.json` | `simulation_engine` | salud de la corrida: terminó completa, teletransportes, pendientes |
| `trayectorias.json` | `simulation_engine` | "grabación" para la animación del frontend |
| `indicadores.json` | `guardar_escenario` | **fuente de verdad** del escenario |
| `reporte.pdf` | `generar_reporte` | entregable |

Los comparativos van en `<proyecto>/reportes/comparacion_<ids>.pdf`.

## Dónde nace cada dato

| Dato | Origen único | Quién lo copia |
|---|---|---|
| Salud de la corrida (`termino_completo`, `vehiculos_teletransportados`, `vehiculos_insertados`) | `resumen_ejecucion.json` | `calcular_indicadores` |
| KPIs globales (espera, velocidad, fila, atendidos) | `tripinfo.xml` y `queue.xml` | `calcular_indicadores` |
| Espera para entrar a la red (`retraso_entrada_promedio`, `espera_total_promedio`) | `departDelay` de `tripinfo.xml` | `calcular_indicadores` |
| Retraso por semáforo (con nombre de calle) | retorno de `simulation_engine` | `armar_indicadores` |
| Configuración en texto para el PDF | `escenario` dentro de `indicadores.json` | se genera al armar el PDF |

## Qué contiene `indicadores.json`

```
semilla, generado
escenario     → el escenario tal como se simuló (id, nombre, duración, flujos, modificaciones)
indicadores   → KPIs + flujos + semáforos
```

El POST al backend manda solo `indicadores` (más `escenario_id`), no este archivo completo.

## Cómo agregar un indicador nuevo

1. **Si sale de `tripinfo.xml` o `queue.xml`:** calcúlalo en `calcular_indicadores` y agrégalo al dict que regresa.
2. **Si solo se puede medir con TraCI en vivo:** mídelo en `simulation_engine` y devuélvelo en el dict de retorno (no crees otro archivo si cabe en `indicadores.json`).
3. **Para que salga en el PDF:** si es una fila de la tabla, agrégalo a `INDICADORES` en `comparar_escenarios.py`. Si es una sección propia, agrégala en `reporte.py`.
4. **No cambies** los nombres de las claves que lee el frontend: `tiempo_promedio_espera`, `velocidad_promedio`, `longitud_max_fila`, `vehiculos_atendidos`.

## Decisiones tomadas

- **Trayectorias en JSON y no en tiempo real.** El flujo es por lotes: se simula una vez y se reproduce las veces que haga falta (pausar, adelantar, comparar escenarios lado a lado). La posición de los vehículos solo existe mientras TraCI está conectado, por eso la graba el motor.
- **El retraso por semáforo no tiene archivo propio.** Viaja por memoria hasta `indicadores.json`.
- **`simulation_engine` no devuelve el resumen de la corrida.** Ya está en disco y `calcular_indicadores` lo lee de ahí.
- **La espera total** (dentro de la red + para entrar) es la métrica principal del PDF cuando todos los escenarios la traen.

## Cosas a vigilar

- **`ZONA_APROXIMACION_M` está en dos lugares:** `simulation_engine.py` (`zona_aproximacion_m`, por omisión 100) y `reporte.py` (para la nota metodológica). Si cambias una, cambia la otra.
- **Los nombres de calle** dependen de que la red traiga `name` en los `<edge>` y de que tu versión de SUMO tenga `traci.edge.getStreetName`. Si no, el reporte muestra el id del semáforo.
- **Escenarios simulados antes de estos cambios** no traen `semaforos` ni `espera_total_promedio`. Hay que volver a simularlos. Si se comparan con uno nuevo, el PDF vuelve a usar `tiempo_promedio_espera` como métrica principal.
- **La espera total está subestimada** cuando la simulación se corta por tope de tiempo: los vehículos que nunca entraron no aparecen en `tripinfo.xml`. Para eso existe el aviso de `termino_completo`.
- **El filtro de semáforos** (`MIN_VEH_SEMAFORO = 10` en `reporte.py`) evita que un semáforo con pocos vehículos salga como "crítico".
- **Una sola corrida por escenario:** diferencias pequeñas entre escenarios pueden ser variación aleatoria. La semilla queda registrada en `indicadores.json`.

## Pendientes opcionales

- Acortar el id del cluster en el PDF (hoy ocupa tres renglones).
- Usar `comp["mejor_por_indicador"]` en `_recomendacion`, en lugar de recalcularlo.
- Guardar la longitud de fila por carril y no solo la máxima global, para identificar dónde se forma.
- Varias corridas por escenario con distintas semillas, para dar un intervalo en lugar de un solo número.
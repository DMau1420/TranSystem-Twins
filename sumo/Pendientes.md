# Pendientes: capa SUMO (lista global y priorizada)

Estado: todo está **sin corregir** salvo lo marcado `[x]`. Los ids (P0-1, P1-3...) sirven para decir "vamos con el P0-2".

Contexto: el servidor se está refactorizando (flujos, semilla, trayectorias), así que los puntos de servidor van agrupados en **P0-5**.

---

## Ya cerrado o aclarado

- [x] `red_base.net.xml` tiene todos los semáforos en `type="static"`. Base y escenarios usan el mismo tipo de control, así que `fijar_todos` / `semaforos_fijos` ya no hacen falta.
- [x] `velocidad_promedio` sí está en km/h (`indicadores.py` multiplica por 3.6).
- [x] `server.py` es solo de pruebas visuales; el servidor real es `server_verdadero.py`.
- [x] El `POST /resultado-sumo` solo existe en la CLI de `main.py`. El contrato real con el frontend son las acciones del WebSocket.
- [x] `utils.py` está bien.
- [x] Elegir el base **no requiere cambios en `reporte.py`**: el base es el primer nombre de `resultados`.

---

## P0: resultados engañosos o cosas que rompen lo prometido en la propuesta (días 1-3)

- [ ] **P0-1. `velocidad_max` nunca se aplica.**
  `planear_cambios` (escenario_calles.py) crea `velocidades = {}` y nunca lo llena. El frontend sí manda `velocidad_max` (km/h, igual que el GeoJSON) y el PDF lo describe como si se hubiera aplicado.
  *Arreglo:* llenar `velocidades[tramo] = (via, kmh)` en `planear_cambios`. `aplicar_velocidades` ya convierte a m/s.

- [ ] **P0-2. Los rechazos no llegan a nadie.**
  `reporte_cambios.json` y `reporte_demanda.json` quedan en disco. El PDF describe lo *pedido*, no lo *aplicado*.
  *Arreglo:* al guardar el escenario, meter los rechazos en `indicadores.json` (clave `"rechazados"`), mostrarlos en el PDF ("no aplicado: motivo") y mandarlos al frontend.

- [ ] **P0-3. Si todo se rechaza, se simula la red base sin avisar.**
  El escenario B saldría igual que A y nadie se entera.
  *Arreglo:* si el escenario traía modificaciones y no se aplicó ninguna, avisar fuerte (o abortar con error claro, a decidir).

- [ ] **P0-4. Tiempo máximo en dos lugares.**
  `crear_sumo_config` tiene `end=7200` fijo y `simulation_engine` calcula `duracion + drenaje`. Coinciden solo porque hoy `duracion=3600`.
  *Arreglo:* calcularlo una vez en `main` (`duracion + drenaje`) y pasarlo a ambos. Validar también `fin_s <= duracion_segundos`.

- [ ] **P0-5. Refactor del servidor (`server_verdadero.py`).** Lo que debe quedar:
  - [ ] Escenario por request: `simular` recibe el escenario completo con su `id` propio. Hoy es un global con `id: 12` y las modificaciones se acumulan entre corridas. Sin esto no hay comparación ni base elegible.
  - [ ] Usar `obtener_red_base` en lugar de `importar_zona`. Hoy cada reinicio vuelve a descargar de Overpass y **reescribe** `red_base.net.xml`; los ids de tramo y de semáforo pueden cambiar.
  - [ ] `get_red` debe leer el GeoJSON de disco si ya existe (hoy responde 409 hasta simular).
  - [ ] `await asyncio.to_thread(simular_escenario, ...)`: hoy la simulación congela el bucle y `websockets` puede cerrar la conexión por falta de ping.
  - [ ] Entrada de `flujos`, `inicio_s`, `fin_s`, `porcentaje_pesados` y **semilla** desde el request.
  - [ ] Nuevas acciones: `get_trayectorias`, `comparar` (con `id_base`), `get_reporte_pdf`, `get_resultado` por id (leer `indicadores.json` de disco, no solo memoria).
  - [ ] Decidir si desde el servidor se genera el PDF. Hoy no se genera.
  - [ ] `patch_semaforo`: validar que `indice` exista (hoy responde `'indice'`).

- [ ] **P0-6. Correr sin GUI.**
  `main` usa `herramientas["sumo_gui"]`: abre ventana. En Docker o servidor se cuelga. `sumo_tools` ya carga `herramientas["sumo"]`. Además `cargar_herramientas_sumo` hace `sys.exit` si falta `SUMO_HOME`.

- [ ] **P0-7. `"--output.street-names true"` va como un solo argumento** en `scenario_builder._reconstruir_red` (en `data_generators` sí está bien).
  Solo afecta a escenarios *con modificaciones*. *Prueba:* un escenario con +1 carril y revisar si los semáforos salen con nombre de calle.

- [ ] **P0-8. Nombres de escenario sin `escape` en `reporte.py`.**
  Un nombre con `&` o `<` rompe el PDF. Los nombres los escribe el usuario.

- [ ] **P0-9. La recomendación automática del PDF no es confiable.**
  `_recomendacion` ignora corridas incompletas y teletransportes, no exige una mejora mínima (1 % con una corrida se presenta como "mejor"), y solo mira la espera.

---

## P1: validez de los números (días 3-4)

- [ ] **P1-1. Una sola corrida por escenario.** Correr 3-5 semillas en los escenarios clave y reportar promedio e intervalo.
- [ ] **P1-2. La semilla de la demanda aleatoria está fija (42).** `main` solo pasa la semilla a SUMO, no a `randomTrips`; con varias semillas la demanda aleatoria sería idéntica. (Los flujos son determinísticos.)
- [ ] **P1-3. La demanda aleatoria ignora `inicio_s`, `fin_s` y `duracion_segundos`** (`tiempo_insercion=3600` fijo).
- [ ] **P1-4. Nivel de servicio basado en `timeLoss` de toda la ruta.** El HCM usa retraso por control en la intersección. Declararlo o calcularlo con el retraso del semáforo.
- [ ] **P1-5. Retraso por semáforo solo cuenta los últimos 100 m.** Subestima colas largas (tu fila máxima fue de 163 m). Leer `zona_aproximacion_m` desde `resumen_ejecucion.json` y copiarlo en `calcular_indicadores`, para quitar la duplicación con `reporte.py`.
- [ ] **P1-6. Política para teletransportes.** Tu corrida de prueba tuvo 5. Decidir si se marca "no confiable" o solo se avisa.
- [ ] **P1-7. Verificar que los ids de semáforo (`cluster_...`) coincidan entre red base y red reconstruida.** Si no, la tabla de puntos críticos sale N/D en todas las alternativas.
- [ ] **P1-8. Editar un tramo puede modificar también el sentido contrario** (`pertenece_a_via` acepta `-id`), y el delta se calcula con un solo tramo de referencia. Verificar y decidir si es intencional.
- [ ] **P1-9. Limpiar la carpeta del escenario al iniciar una corrida.** Quedan archivos viejos (por ejemplo un `reporte_cambios.json` de una corrida anterior).
- [ ] **P1-10. `queue.xml` puede pesar cientos de MB.** Borrar o comprimir tras calcular la fila máxima.
- [ ] **P1-11. Declarar supuestos del modelo:** tiempos de semáforo generados (`--tls.cycle.time 90`, `--tls.guess-signals`), no de campo; ruta por distancia mínima; inserción uniforme.
- [ ] **P1-12. La ruta de un flujo con camiones es la apta para camiones, y la comparten los autos.** Documentarlo o separar rutas.

---

## P2: comparación y base elegible (día 4-5)

- [ ] **P2-1.** `generar_reporte(..., id_base=None)`: reordenar `ids` para que el base quede primero; convertir ids a `int`; quitar repetidos.
- [ ] **P2-2.** `comparar_escenarios`: llaves por **id** (nombres aparte). **No** lanzar error por menos de 2 escenarios (la ficha individual también la usa).
- [ ] **P2-3.** Campo `mejoro_vs_base` (el signo del porcentaje no dice si mejoró) y lista de `advertencias` de comparabilidad (corrida incompleta, teletransportes, demanda distinta).
- [ ] **P2-4.** Empates en `mejor_por_indicador`.
- [ ] **P2-5.** Comparar también `nivel_de_servicio`, `retraso_entrada_promedio`, semáforos y flujos.
- [ ] **P2-6.** `comparar_para_frontend(proyecto_id, ids, id_base)` que regrese el JSON sin dibujar PDF (la propuesta pide dashboard de comparación).
- [ ] **P2-7.** Duración por escenario (hoy solo se toma la del primero).

---

## P3: PDF (día 5)

- [ ] **P3-1.** Sección de cambios no aplicados (depende de P0-2).
- [ ] **P3-2.** Sección de flujos: esperados vs. completados y espera por flujo.
- [ ] **P3-3.** Gráficas: "N/D" se pinta como 0, etiquetas cortadas a 14 caracteres (dos escenarios parecidos se ven iguales), no escala con 5+ escenarios.
- [ ] **P3-4.** La nota "una sola corrida" desaparece cuando las semillas difieren (está dentro de `if semilla is not None`).
- [ ] **P3-5.** Casos límite: `StopIteration` en `_recomendacion` si falta la métrica principal; `Table([pares])` sin gráficas; `_ruta_escribible` deja un PDF vacío si el build falla.
- [ ] **P3-6.** Acortar el id del cluster (ocupa tres renglones).
- [ ] **P3-7.** Verificar la primera línea de `reporte.py`: en lo que pegaste el docstring abre con `""` (probablemente error de copiado).
- [ ] **P3-8.** Si falta `resumen_ejecucion.json` (`termino_completo = None`), no se avisa nada.
- [ ] **P3-9 (opcional).** Mapa del área en el PDF; la propuesta lo menciona en el producto final.

---

## P4: robustez y limpieza (cuando sobre tiempo)

- [ ] **P4-1.** `escenario_semaforos`: `KeyError` si falta `tls_id`; error si la duración no es numérica. El resto del código rechaza con motivo, esto no.
- [ ] **P4-2.** `describir_configuracion`: truena si `vehiculos_por_hora` llega como texto o `carriles_extra` como decimal.
- [ ] **P4-3.** Manejo de `None` de `generar_rutas_aleatorias` (hoy termina en `TypeError` en `crear_sumo_config`) y de `descargar_red`.
- [ ] **P4-4.** Centralizar `TIPOS_VEHICULO` (duplicado y distinto en `data_generators` y `escenario_demanda`; a los camiones de los flujos les faltan `guiShape` y `color`).
- [ ] **P4-5.** `main.py`: `proyecto` siempre es `PROYECTO_PRUEBA`; `netxml_base_url` es `str` en una rama y `Path` en otra. `PROYECTO` duplicado en `main` y servidor.
- [ ] **P4-6.** Camiones aleatorios asignados a rutas que `randomTrips` generó para autos.
- [ ] **P4-7.** `guardar_escenario` usa `default=str` y oculta objetos raros sin avisar.
- [ ] **P4-8.** Código muerto y typos: `cargar_escenario()` (llama a `/points/prueba`), "TranSytemTwins" en el User-Agent, `seed=42` documentado en el `.sumocfg` pero la corrida usa otra.
- [ ] **P4-9.** `tiempo_drenaje` fijo en 3600 (`main` no lo pasa).

---

## P5: contrato con backend y frontend (en paralelo, avisar pronto)

- [ ] **P5-1.** Documento del contrato con las acciones del WebSocket (`get_red`, `patch_infraestructura`, `patch_semaforo`, `simular`, `get_resultado`, y las nuevas), con JSON de ejemplo, tipos y qué campos pueden venir `null` (`velocidad_promedio`, `longitud_max_fila`, `termino_completo`).
- [ ] **P5-2.** No cambiar las 4 claves que lee el frontend: `tiempo_promedio_espera`, `velocidad_promedio`, `longitud_max_fila`, `vehiculos_atendidos`.
- [ ] **P5-3.** `edge_id` del GeoJSON es de **tramo** (`8640976#10`), no de vía. Definir cuándo se manda tramo (`tramos`) y cuándo vía completa (`edge_id` sin `#`).
- [ ] **P5-4.** El frontend manda `carriles` absoluto; el builder lo convierte a relativo. Confirmar que ese es el formato final (o pasar a `carriles_extra`).
- [ ] **P5-5.** Decidir con el equipo cómo se definen los **flujos** desde el frontend (origen/destino sobre el mapa). Sin eso, `escenario_demanda` solo se usa desde `main.py`.
- [ ] **P5-6.** Qué se entrega al frontend: `trayectorias.json` (`t_max`, `paso`, `bbox`, `veh = [t0, es_camion, [[lon, lat, v]...]]`), `semaforos`, `flujos`, `rechazados`, avisos de calidad (`termino_completo`, teletransportes).
- [ ] **P5-7.** Cómo se entregan los archivos (PDF, trayectorias, GeoJSON): por WebSocket, por HTTP o leídos de disco.

---

## P6: documentación y pruebas (final de la semana)

- [ ] **P6-1.** Actualizar `GUIA_SCENARIO_BUILDER.md`: menciona `semaforos_fijos`, `fijar_todos`, `verificar_secuencias.py`, `probar_builder.py`, `probar_flujo.py` que no están en lo revisado, y habla de semáforos "actuados" (ya no aplica). Confirmar en el repo qué versión es la buena.
- [ ] **P6-2.** Quitar la nota "pasa a tiempo fijo" que `escenario_semaforos` agrega al reporte.
- [ ] **P6-3.** Fichas por archivo en `docs/`.
- [ ] **P6-4.** Manual técnico: supuestos del modelo (ver P1-11 y `GUIA` sección 5).
- [ ] **P6-5.** Correr `probar_builder.py` y `test/test_escenario.py` después de cada cambio al builder. Esperado según la guía: 4 / 7+3 / 5+3 / 1 borrado + 4 movidos.
- [ ] **P6-6.** Pendientes de la guía: reducir dos vías que comparten semáforo, probar `carriles_extra >= 2`, dos vías conectadas a la vez.
- [ ] **P6-7 (futuro).** Perfiles de demanda por hora, llegadas aleatorias, carga de aforos desde CSV (la propuesta lo menciona como fuente de datos).

---

## Plan sugerido para la semana

| Día | Qué |
|---|---|
| Lun | P0-1 (velocidad), P0-7 (street-names), P0-4 (tiempo máximo), P0-6 (sin GUI), P0-8 (escape) |
| Mar | P0-2 y P0-3 (rechazos de punta a punta), P0-9 |
| Mié | P0-5 (refactor del servidor: escenario por request, `obtener_red_base`, `to_thread`, flujos, semilla) |
| Jue | P0-5 (trayectorias, comparar, PDF) y P1-1/P1-2 (semillas) |
| Vie | P2 (base elegible, comparación en JSON) y P1-7/P1-8 (verificaciones) |
| Sáb | P3 (PDF) y P5-1 (documento del contrato para backend y frontend) |
| Dom | P6 (guía, fichas, pruebas) |

**Avisar a backend y frontend desde el lunes:** P5-3, P5-4, P5-5 y P5-6, porque dependen de tus decisiones y ellos tardan en ajustar.

---

## Lo que aún no he visto

- `test/test_escenario.py`
- Los scripts `probar_*.py` y `verificar_secuencias.py` que menciona la guía
- La versión actual del servidor refactorizado
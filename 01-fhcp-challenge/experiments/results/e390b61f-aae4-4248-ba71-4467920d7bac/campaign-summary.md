# Resultados de la campaña FHCP M6 v3

Campaña `e390b61f-aae4-4248-ba71-4467920d7bac`. Código `22994034acb6eb4232fb72489758b6092cb0c626`. Equipo i5-12450H, afinidad CPU 2, CPython 3.14.10 y NumPy 2.5.4; perfil completo en manifest.json.

La ejecución planificada está completa: 1,044 procesos, sin errores de ejecución ni timeouts externos registrados. No se encontró ningún ciclo hamiltoniano certificado dentro del presupuesto. Es un resultado negativo de búsqueda, no una prueba de inexistencia de ciclos.

Duración de pared, incluidas las pausas: **7 h 01 min 36 s**. Suma de duraciones de procesos: **6 h 49 min 33 s**. Estos alcances no son intercambiables ni deben sumarse. La campaña terminó el 13/11/2026 a las 05:43:19 (America/Monterrey), antes de la auditoría posterior.

## Cobertura

| Fase | Procesos | Agotamiento de evaluaciones | Límite temporal cooperativo | Éxitos |
|---|---:|---:|---:|---:|
| Comprobación inicial | 12 | 12 | 0 | 0 |
| Ajuste | 120 | 67 | 53 | 0 |
| Evaluación | 720 | 270 | 450 | 0 |
| Escala | 180 | 0 | 180 | 0 |
| Verificación de reproducibilidad | 12 | 12 | 0 | 0 |

Evaluación: cuatro grafos, seis familias y 30 repeticiones por celda (720 intentos). Escala: graph1001, analizado por separado (180 intentos). Hasta 10,000 evaluaciones o 30 segundos de solver por intento. Comprobación y ajuste no forman parte del denominador de evaluación.

## Selección congelada tras el ajuste

| Familia | Configuración seleccionada |
|---|---|
| GA | ga-c2 |
| SA | sa-c1 |
| AS | as-c2 |
| ABC | abc-c2 |
| DE | de-c2 |
| PSO | pso-c1 |

Las seis selecciones tuvieron cero éxitos en ajuste; se aplicó la regla preregistrada sobre errores, costo normalizado y ordinal. Los parámetros y puntuaciones efectivos están en freeze.json y selection.csv. No se eligieron configuraciones usando evaluación.

## Resultados por celda

| Fase | Instancia | Algoritmo | Éxitos / intentos | Agotamientos | Timeouts cooperativos | Mediana solver (s) | Media evaluaciones completadas |
|---|---|---|---:|---:|---:|---:|---:|
| evaluation | graph175 | ABC | 0 / 30 | 30 | 0 | 26.436 | 10000.0 |
| evaluation | graph175 | AS | 0 / 30 | 0 | 30 | 30.000 | 27.0 |
| evaluation | graph175 | DE | 0 / 30 | 0 | 30 | 30.002 | 3405.1 |
| evaluation | graph175 | GA | 0 / 30 | 0 | 30 | 30.001 | 8630.1 |
| evaluation | graph175 | PSO | 0 / 30 | 0 | 30 | 30.002 | 3426.8 |
| evaluation | graph175 | SA | 0 / 30 | 0 | 30 | 30.001 | 9813.2 |
| evaluation | graph479 | ABC | 0 / 30 | 0 | 30 | 30.003 | 4307.4 |
| evaluation | graph479 | AS | 0 / 30 | 0 | 30 | 30.000 | 3.0 |
| evaluation | graph479 | DE | 0 / 30 | 0 | 30 | 30.010 | 1151.5 |
| evaluation | graph479 | GA | 0 / 30 | 0 | 30 | 30.001 | 3252.5 |
| evaluation | graph479 | PSO | 0 / 30 | 0 | 30 | 30.005 | 1155.7 |
| evaluation | graph479 | SA | 0 / 30 | 0 | 30 | 30.002 | 3694.7 |
| evaluation | graph48 | ABC | 0 / 30 | 30 | 0 | 8.857 | 10000.0 |
| evaluation | graph48 | AS | 0 / 30 | 0 | 30 | 30.000 | 241.4 |
| evaluation | graph48 | DE | 0 / 30 | 30 | 0 | 26.820 | 10000.0 |
| evaluation | graph48 | GA | 0 / 30 | 30 | 0 | 11.845 | 10000.0 |
| evaluation | graph48 | PSO | 0 / 30 | 30 | 0 | 26.684 | 10000.0 |
| evaluation | graph48 | SA | 0 / 30 | 30 | 0 | 10.375 | 10000.0 |
| evaluation | graph74 | ABC | 0 / 30 | 30 | 0 | 12.263 | 10000.0 |
| evaluation | graph74 | AS | 0 / 30 | 0 | 30 | 30.000 | 132.2 |
| evaluation | graph74 | DE | 0 / 30 | 0 | 30 | 30.001 | 7898.0 |
| evaluation | graph74 | GA | 0 / 30 | 30 | 0 | 16.288 | 10000.0 |
| evaluation | graph74 | PSO | 0 / 30 | 0 | 30 | 30.000 | 7965.5 |
| evaluation | graph74 | SA | 0 / 30 | 30 | 0 | 14.222 | 10000.0 |
| scale | graph1001 | ABC | 0 / 30 | 0 | 30 | 30.010 | 1274.4 |
| scale | graph1001 | AS | 0 / 30 | 0 | 30 | 30.000 | 0.0 |
| scale | graph1001 | DE | 0 / 30 | 0 | 30 | 30.040 | 302.3 |
| scale | graph1001 | GA | 0 / 30 | 0 | 30 | 30.005 | 963.6 |
| scale | graph1001 | PSO | 0 / 30 | 0 | 30 | 30.040 | 303.6 |
| scale | graph1001 | SA | 0 / 30 | 0 | 30 | 30.006 | 1088.0 |

Los tiempos con plazo alcanzado describen consumo del presupuesto; no son tiempos hasta solución. AS no terminó ningún candidato completo en los 30 intentos de graph1001. Esos intentos permanecen en el denominador y no se les atribuye un costo de ruta inexistente.

## Auditoría y limitaciones

- Se verificaron 10,575 hashes de artefactos e historiales, la congelación, los 1,044 registros y sus análisis. El recálculo independiente de aristas y cierre coincide con los costos de los 1,014 candidatos disponibles; 30 intentos no produjeron candidato.
- Los seis pares predefinidos de verificación reproducen ruta, costo, estado y contadores. Los tiempos no se exigen iguales.
- Se conservaron dos incidencias globales de swap en ajuste y dos pérdidas de alimentación AC en evaluación. Los intentos afectados no se sustituyeron ni eliminaron; estas incidencias limitan la comparación de tiempos. Los detalles están en los manifiestos y en los archivos incident-review-*.json.
- Solo se estudiaron las nueve instancias seleccionadas; los resultados no representan los 1,001 grafos. No hay una familia ganadora por tasa de éxito: todas obtuvieron 0 % en evaluación y escala.
- Precisión, recall y F1 no se aplican como métricas de esta búsqueda. La comparación con publicaciones y el cierre global de M6 corresponden a #71.
- Completar los procesos no integra la entrega de #70 ni cierra el milestone. La PR entrega los resultados del #70 para revisión e integración. Los cinco respaldos están publicados en Drive con acceso institucional. El estado de publicación se registra en artifact-access.json.

## Ubicación de la evidencia

El manifest.json de esta carpeta enlaza cada fase con su lote y análisis. post-campaign-audit.json contiene la auditoría posterior; verification.json contiene los seis pares. Cada analyses/<UUID>/ incluye tablas CSV/JSON, procedencia por intento y figuras PNG/SVG. El índice creado por benchmark_archive identifica los archivos tar.gz y sus hashes. Conservar esta carpeta junto con su índice, congelación y archivos comprimidos para recuperación.

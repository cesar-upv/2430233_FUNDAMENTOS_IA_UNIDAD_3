# Comparación FHCP y verificación de M6

## Identificación y alcance

- Responsable de la entrega: Junior Arturo Vázquez Leonel · @Arturo2430, por delegación de Diego Eduardo Zapata Aguilar · @ZapataFrame.
- Issue: [#71](https://github.com/ZapataFrame/FHCP-Challenge/issues/71). Fecha de consulta: 2026-11-13.
- Base aceptada: `b83b19ef628712e9e10b9d9d9f5eaedacaa5bcee`, integración de [PR #77](https://github.com/ZapataFrame/FHCP-Challenge/pull/77).
- Cierre revisado el 2026-11-17: comparación y evidencia verificadas; #71 se cierra al integrar la PR #78 y M6 después de comprobar las cinco entregas en main. No se modifica la campaña, sus parámetros ni sus denominadores.

La campaña `e390b61f-aae4-4248-ba71-4467920d7bac`, ejecutada con código limpio `22994034acb6eb4232fb72489758b6092cb0c626`, completó 1,044 procesos. La evaluación principal y escala reúnen **0 éxitos / 900 intentos**. Es un resultado de búsqueda bajo presupuesto, no una prueba de no hamiltonicidad. El experimento posterior de graph2 y el ZIP de otro equipo no forman parte del protocolo aceptado ni de estas estadísticas. Las mejoras de los algoritmos se integraron posteriormente mediante PR #80; su
evaluación distribuida se cerró en #94 / PR #96 con 14 grafos distintos
certificados en 7,383 intentos. Esos resultados usan otras variantes, hardware,
semillas y presupuestos y se conservan en [su informe separado](../experiments/distributed-evaluation.md),
sin sumarlos a los denominadores de M6 ni atribuir causalidad a una mejora aislada.

## Fuentes primarias y condiciones publicadas

El [inventario de fuentes](evidence/m6/published-results.json) conserva autores, versión, localizador, hardware, parámetros, presupuesto, repeticiones y criterio de éxito; `null` significa no publicado en el pasaje consultado. Se reutilizan las claves de [la bibliografía compartida](references.bib), añadiendo `seeja2018HybridHam`. Se registran datos puntuales, sin reproducir documentos completos.

| Fuente | Dato publicado y ubicación | Alcance del contraste |
| --- | --- | --- |
| [Portal FHCP](https://sites.flinders.edu.au/flinders-hamiltonian-cycle-project/fhcp-challenge-set/), `flindersFhcpChallenge` | «Challenge Results»: 985/1001 por Cohen y Coudert. «Competition rules»: concurso de un año. | Cobertura acumulada; no 30 repeticiones homogéneas ni tiempo CPU. Hardware, semillas y cupo uniforme no publicados. |
| [Coudert y Cohen, 2017](https://interstices.info/le-defi-des-1001-graphes/), `cohenCoudert2017Challenge` | «L’oracle», filas 1 y 2: 0.76 s y 0.01 s. Oráculo MILP con SageMath/CPLEX, versiones no precisadas. | IDs compartidos con comprobación, no evaluación final. Hardware, repeticiones y límite individual no especificados. |
| [Seeja, 2018, HybridHAM](https://doi.org/10.1155/2018/9328103), `seeja2018HybridHam` | §4: Core i5, 4 GB, MATLAB 13RA. §4.3 declara 6 ciclos en 250 instancias y 75 caminos; su tabla 4 contiene más etiquetas HC (discrepancia interna). Tabla 4: graph1 HP, 0.0625 s; graph2 HC, 0.0469 s. | Camino HP no cuenta como ciclo HC. Modelo exacto de CPU, semillas, repeticiones y cupo experimental común no publicados. |
| [Haythorpe, 2018](https://bica.the-ica.org/Volumes/83/Reprints/BICA2017-32-Main-Reprint.pdf), `haythorpe2018Fhcp` | §2, p. 100: selección por dificultad para Concorde/LKH/SLH. §3, pp. 102–103: resultados del concurso. | No ofrece una matriz temporal reproducible de esos tres solvers. Los tours oficiales no son mediciones de rendimiento. |

Los enlaces se consultaron el 13 de noviembre y se contrastaron nuevamente el
17 de noviembre; HybridHAM se comprobó mediante el contenido indexado de la
página editorial. El texto de su §4.3 declara seis ciclos, mientras la tabla 4
marca como HC más de seis instancias (entre ellas graph2, graph6, graph72,
graph79, graph84, graph90 y graph96). Se conserva la afirmación textual con
esa discrepancia explícita, sin inferir una cifra corregida ni una tasa global.
Los tiempos por ID se atribuyen a sus filas, distinguiendo HP de HC. La versión editorial de Haythorpe es de 2018; arXiv v1 es de 2019 y no constituye otro experimento.

## Contraste explícito

| Dimensión | Nuestra campaña | Referencias y límite |
| --- | --- | --- |
| Cobertura | 9 grafos distintos entre fases; 4 de evaluación y graph1001 de escala, separados de ajuste/comprobación. | 1001 en el concurso; 250 en HybridHAM. No comparar sus porcentajes como si procedieran de la misma muestra. |
| Éxito | 0/720 en evaluación y 0/180 en escala; 30 semillas por grafo/familia. | Conteos publicados de instancias resueltas, sin distribución equivalente de semillas. No estiman nuestra probabilidad de éxito. |
| Tiempo | Hasta 10,000 evaluaciones o 30 s de solver; mediana, cuartiles y desviación disponibles por celda. | Tiempos puntuales de métodos y condiciones distintos. No calcular aceleraciones ni convertir entre CPUs. |
| Recursos | i5-12450H, afinidad CPU lógico 2, un trabajador, hilos nativos solicitados a 1, ~32 GB RAM, Linux y entorno fijado. | Datos parciales o ausentes según fuente; no atribuir diferencias al hardware. |

El [contraste por ID](evidence/m6/published-contrast.csv) contiene 36 filas con referencias individuales para graph1/graph2, incluidas las repeticiones de verificación de graph1. Cada fila declara `equivalent_conditions=False`: nuestros casos compartidos pertenecen a comprobación (20 evaluaciones o 5 s) o verificación (100 evaluaciones), y no equivalen a la evaluación final. El resultado HP de HybridHAM se distingue de HC. No se asignan tiempos externos a graph48/175/74/479/1001 a partir de los conteos globales.

## Resultados entre las seis familias

La [tabla derivada por celda](evidence/m6/campaign-cells.csv) reúne 72 combinaciones de fase, grafo y configuración: tamaño, grado medio, densidad, éxitos, candidatos, tiempos, cuartiles, variabilidad, evaluaciones y RSS. Cada fila enlaza el análisis y el archivo de intentos originales, que identifican semillas, RunRecord, hashes, entorno y commit. `expected_primary` distingue los primarios de `records_all_roles`; las seis repeticiones adicionales de verificación no inflan el denominador de evaluación.

| Familia | Éxitos / 150 evaluación + escala | Plazos temporales / 150 | Agotamientos de evaluaciones / 150 | Media de evaluaciones completadas en graph1001 | RSS máximo observado (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| GA | 0/150 | 90 | 60 | 963.57 | 59.73 |
| SA | 0/150 | 90 | 60 | 1088.03 | 53.99 |
| AS (hormigas) | 0/150 | 150 | 0 | 0.00 | 400.41 |
| ABC | 0/150 | 60 | 90 | 1274.40 | 58.54 |
| DE | 0/150 | 120 | 30 | 302.33 | 66.78 |
| PSO | 0/150 | 120 | 30 | 303.57 | 61.75 |

El RSS es del proceso, no memoria exclusiva del algoritmo. Sus máximos no son estimaciones ni suma de intentos. Los 900 primarios no registraron errores de ejecución ni timeouts externos. Los límites cooperativos se incluyen como intentos sin éxito; 30 AS de escala no completaron candidato y no reciben costo ficticio.

No hay ganador por éxito: todas las tasas son cero y su desviación binaria muestral es cero, lo que no demuestra probabilidad real nula. Los boxplots originales y los cuartiles/desviaciones del CSV muestran la variabilidad temporal; la concentración cerca de 30 s describe censura por presupuesto, no tiempos hasta solución. Los seis pares de verificación coinciden en ruta, costo, estado y contadores; no se exige igualdad temporal.

En graph48 ABC/GA/SA/DE/PSO completaron 10,000 evaluaciones en todos los intentos, mientras AS llegó al plazo temporal. En graph175 solo ABC agotó evaluaciones en sus 30 intentos. En graph479 y graph1001 todas las familias alcanzaron el plazo. Por tanto, igual presupuesto máximo no implica igual número efectivo de candidatos explorados. La construcción de AS es un cuello de botella observado: en graph1001 no terminó rutas completas. Esto no identifica por sí solo qué operación interna consume el tiempo; no se realizó perfilado.

La selección documenta graph48/175 como `motif_16`, graph74/479 como `bells`, graph58 como `near_cycle`, graph268 como `big_degree` y graph1001 como `blocks_1001`, según el [manifiesto de instancias](../decisions/fhcp-instances.json). Esa clasificación es documental; no se infiere por el número de archivo ni demuestra causalidad del rendimiento. Dos instancias por algunas estructuras y una de escala no separan efectos de tamaño, estructura, parámetros e implementación. La selección intencional tampoco representa estadísticamente los 1001 grafos.

Se conservaron dos incidencias de swap en ajuste y dos de alimentación AC en evaluación. No se eliminaron ni sustituyeron sus intentos. Estas incidencias y la actividad del escritorio limitan la interpretación temporal. Los candidatos con costo positivo son rutas incompletas respecto a las aristas del ciclo, aunque sean permutaciones válidas. Precisión, recall y F1 son N/A: no se predice una clase negativa FHCP.

## Recuperación y regeneración comprobadas

La [comprobación de reproducción](evidence/m6/reproduction-check.json) registra checkout, plataforma, intérprete, comandos, salidas y resultados. Se usó un clon limpio del commit aceptado `b83b19e`, el entorno fijado de la laptop y copias de los cinco respaldos locales originales. El [inventario y los enlaces de Drive](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/artifact-access.json) conservan ubicación y SHA-256; se requiere cuenta institucional para acceder a los archivos.

Desde ese checkout, con las cinco copias en las rutas del índice y el entorno instalado según README:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m src.cli.benchmark_archive restore experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/archive-index-732914c2-7124-4bf1-bd13-b7ec6ce60a9e.json
```

Ejecutar el analizador sobre el `manifest_path` de cada una de las cinco fases del [manifiesto de campaña](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/manifest.json):

```bash
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/3db63fd9-6545-4199-a1ea-cf74bdd50444/manifest.json
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/ef9646e3-1985-47b6-8f58-6744b2f70810/manifest.json
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/67191556-cc8d-4612-9517-e9b4cd0a2340/manifest.json
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/22560abf-18ec-4dab-87a9-8e1141f7ed05/manifest.json
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/311e6dd4-2d47-4775-833d-c2969771094c/manifest.json
```

Cada análisis audita el inventario, las entradas, la cadena de manifiestos y los RunRecord. Se restauraron cinco lotes; las siete tablas/archivos de datos de cada fase coinciden byte por byte y se generaron de nuevo las figuras PNG/SVG. Se recalcularon los 1,014 candidatos disponibles de 1,044 registros; los otros 30 no tenían candidato. La recertificación de éxitos tiene conjunto vacío porque no hubo éxitos: no se presenta como evidencia de éxito. Los seis pares predefinidos volvieron a coincidir. El clon permaneció limpio. No se repitió búsqueda estocástica ni se exigieron tiempos idénticos.

Las tablas de este issue se regeneran sin buscar soluciones ni modificar los análisis originales:

```bash
.venv/bin/python scripts/build_benchmark_comparison.py
```

El generador comprueba los hashes de configuración, metadatos y salidas originales. No requiere ejecutar solvers ni descargar fuentes externas. Los datos publicados del inventario son una transcripción manual identificada por localizador, no mediciones propias.

## Auditoría de criterios de M6

El [registro de GitHub](evidence/m6/dependency-check.json) conserva la revisión de las dependencias y sus commits integrados. La evidencia se distribuye así:

| Criterio del milestone | Evidencia aceptada o presentada |
| --- | --- |
| Instancias, semillas, configuraciones y presupuestos fijados | #67 / [PR #72](https://github.com/ZapataFrame/FHCP-Challenge/pull/72); protocolo v3, `benchmark-v3.json`, `freeze.json` de #70 / PR #77. |
| Repeticiones completas y trazables | #68 / [PR #73](https://github.com/ZapataFrame/FHCP-Challenge/pull/73), #70 / PR #77; 1,044 registros y reconciliación sin pendientes. |
| Manifiestos y crudos conservados | Índice SHA-256, cinco respaldos, historial y auditoría de #70; recuperación desde clon registrada en este issue. |
| Éxitos validados | Validador independiente integrado; auditoría de candidatos; cero éxitos de campaña, sin afirmar una recertificación positiva inexistente. |
| Fallos y plazos en denominadores | #69 / [PR #74](https://github.com/ZapataFrame/FHCP-Challenge/pull/74); tablas de #70 y 900 primarios con 630 plazos y 270 agotamientos. |
| Tablas y gráficos regenerables | Herramienta #69; comprobación de las cinco fases y tablas de contraste de #71. |
| Referencias y limitaciones | Este documento, inventario de fuentes, bibliografía y CSV con condiciones no equivalentes. |
| Entregas aceptadas en main | #67–#70 cerrados y PR #72/#73/#74/#77 integradas. #71 requiere revisión e integración; abrir su PR no cierra M6. |

Después de integrar la entrega aceptada de #71, comprobar su commit en `main`, el cierre de los cinco issues y la matriz anterior antes de proponer el cierre del milestone. Esta entrega no cierra administrativamente M6.

## Revisión final de integración

El 17 de noviembre se resolvieron los conflictos con main conservando las
entregas posteriores y se regeneraron las 72 celdas y 36 contrastes: los dos
CSV son idénticos a los del 13 de noviembre. Las 50 pruebas de configuración,
análisis y campaña volvieron a pasar. La recuperación completa se repitió en
un clon limpio del commit histórico, con su evidencia separada en
[reproduction-final-check.json](evidence/m6/reproduction-final-check.json).
No se lanzaron búsquedas ni se alteraron los respaldos o resultados originales.

La [auditoría final](evidence/m6/finalization-check.json) confirma que las
dependencias #67–#70 y sus PR están integradas. La matriz científica está
verificada; resta la integración de #78, cierre automático de #71 y comprobación
administrativa final del milestone. Ese cierre no exige éxitos positivos ni
convierte los agotamientos en prueba de no hamiltonicidad.

## Insumos y pendientes de M7

M7 recibe la configuración congelada, manifiestos, tablas/figuras originales, CSV de contraste, fuentes y bibliografía, prueba de recuperación y limitaciones. Quedan para M7 integrar la plantilla LaTeX, redactar el informe, seleccionar tablas/figuras sin alterar sus denominadores y compilar/verificar el PDF. Mejorar inicialización, operadores o presupuesto no es requisito retroactivo para aceptar los resultados medidos de M6. M7 también recibe la evaluación posterior de #94, presentada por separado con su alcance parcial y limitaciones.

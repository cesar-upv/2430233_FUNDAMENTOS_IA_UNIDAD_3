# Roadmap

La preparación del repositorio está completada. M1 reúne las seis entregas documentales de los issues #1–#6; su cierre se hace efectivo al integrar la [PR #13](https://github.com/ZapataFrame/FHCP-Challenge/pull/13) y se registra en el [milestone M1](https://github.com/ZapataFrame/FHCP-Challenge/milestone/1). M3 tiene integrados grafo, lectores, validador y carga verificada (#26–#29); la integración completa del #30 se presenta para revisión. La campaña M6 v3 está medida e integrada mediante PR #77; el respaldo está en Drive y el contraste/auditoría #71 se entrega en la PR #78, con los criterios científicos de M6 verificados para cierre tras su integración. No hay fechas de entrega acordadas.

## Etapas

| Hito | Tareas principales | Estado |
| --- | --- | --- |
| M0 · Preparación del repositorio | README, integrantes, estructura, instrucciones y enunciado. | Completado |
| [M1 · Investigación](https://github.com/ZapataFrame/FHCP-Challenge/milestone/1) | Investigar fundamentos, metaheurísticas, representación, fitness y métricas; entregar documentos con fuentes. | Completado al integrar la [PR #13](https://github.com/ZapataFrame/FHCP-Challenge/pull/13) |
| [M2 · Definición del problema y dataset](https://github.com/ZapataFrame/FHCP-Challenge/milestone/2) | Acordar stack, contratos, representación y fitness; seleccionar instancias y preparar el entorno. | Entregas #15–#19 integradas; issues cerrados |
| [M3 · Carga de grafos y validación](https://github.com/ZapataFrame/FHCP-Challenge/milestone/3) | Leer instancias FHCP y validar ciclos con pruebas positivas y negativas. | #26–#30 integrados |
| [M4 · Algoritmo genético base](https://github.com/ZapataFrame/FHCP-Challenge/milestone/4) | Implementar GA y una ejecución reproducible mediante CLI. | Completado al integrar la [PR #48](https://github.com/ZapataFrame/FHCP-Challenge/pull/48) |
| [M5 · Metaheurísticas adicionales](https://github.com/ZapataFrame/FHCP-Challenge/milestone/5) | Implementar SA, ACO, Bee Colony, DE y PSO bajo el contrato común. | Completado al integrar la entrega del [#56](https://github.com/ZapataFrame/FHCP-Challenge/issues/56) |
| [M6 · Benchmarking reproducible](https://github.com/ZapataFrame/FHCP-Challenge/milestone/6) | Ejecutar comparativas, conservar resultados y generar tablas y gráficos frente a referencias FHCP. | Completado al integrar PR #78 y verificar el cierre de #67–#71; campaña #70 integrada (1,044 procesos), contraste, auditoría y reproducción comprobados |
| [M7 · Informe y entrega](https://github.com/ZapataFrame/FHCP-Challenge/milestone/7) | Integrar la plantilla LaTeX, redactar el informe y verificar el PDF y las instrucciones de reproducción. | Pendiente |

## Investigación

Los seis temas asignados pertenecen a M1. Cada issue contiene el entregable, sus fuentes y los criterios de aceptación.

Formato de entrega: [guía de investigación](docs/research/README.md).

| Tarea | Responsable | Issue | Entrega y PR |
| --- | --- | --- | --- |
| Teoría de grafos y ciclos hamiltonianos | César Euresti · @cesar-upv | [#1](https://github.com/ZapataFrame/FHCP-Challenge/issues/1) | [Documento](docs/research/graph-theory.md) · [PR #10](https://github.com/ZapataFrame/FHCP-Challenge/pull/10) |
| Algoritmos: GA, SA, ACO, Bee Colony, DE y PSO | Junior Arturo Vázquez Leonel · @Arturo2430 | [#2](https://github.com/ZapataFrame/FHCP-Challenge/issues/2) | [Documento](docs/research/metaheuristics.md) · [PR #12](https://github.com/ZapataFrame/FHCP-Challenge/pull/12) |
| Representación del espacio de búsqueda | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#3](https://github.com/ZapataFrame/FHCP-Challenge/issues/3) | [Documento](docs/research/search-space.md) · [PR #11](https://github.com/ZapataFrame/FHCP-Challenge/pull/11) |
| Formatos y criterios del FHCP Challenge | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#4](https://github.com/ZapataFrame/FHCP-Challenge/issues/4) | [Documento](docs/research/fhcp-challenge.md) · [PR #9](https://github.com/ZapataFrame/FHCP-Challenge/pull/9) |
| Módulo evolutivo, heurísticas y fitness | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#5](https://github.com/ZapataFrame/FHCP-Challenge/issues/5) | [Documento](docs/research/evolution-and-fitness.md) · [PR #14](https://github.com/ZapataFrame/FHCP-Challenge/pull/14) |
| Métricas de evaluación en IA | Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON | [#6](https://github.com/ZapataFrame/FHCP-Challenge/issues/6) | [Documento](docs/research/evaluation-metrics.md) · [PR #13](https://github.com/ZapataFrame/FHCP-Challenge/pull/13) |

M6 se desglosa en los issues #67–#71, detallados en [benchmarking reproducible](#benchmarking-reproducible). M7 se desglosará al concretar su alcance. Los criterios de cierre de cada etapa están en su milestone.

El [entregable del issue #4](docs/research/fhcp-challenge.md) incluye fuentes, capturas, inspección documental del archivo oficial y propuestas para M2/M6. La [PR #9](https://github.com/ZapataFrame/FHCP-Challenge/pull/9) registra la entrega y sus correcciones de revisión; el estado de integración y cierre se consulta en la PR y el issue #4. El cierre de M1 requiere las seis entregas y los criterios de sus issues. No se han completado M2 ni M3 por inspeccionar archivos durante la investigación.

El [entregable del issue #3](docs/research/search-space.md) compara representaciones del grafo y de candidatos, propone índices y cierre, y analiza operadores y validación independiente. Incorpora la teoría del issue #1, integrado mediante la [PR #10](https://github.com/ZapataFrame/FHCP-Challenge/pull/10). La entrega del #3 está integrada mediante la [PR #11](https://github.com/ZapataFrame/FHCP-Challenge/pull/11), por lo que satisface esa dependencia del #5; las convenciones descritas son propuestas para M2, sin contratos aprobados ni implementación.

El [documento del issue #2](docs/research/metaheuristics.md) introduce las seis metaheurísticas con descripciones, componentes, funcionamiento, características y ejemplos didácticos antes de sus adaptaciones al proyecto. Identifica ABC frente a The Bees Algorithm y propone adaptaciones a permutaciones, incluidas claves reales para DE y PSO. Prioriza libros académicos y un capítulo de manual, con bibliografía, capturas de los pasajes citados y [procedencia de las imágenes](docs/research/evidence/metaheuristics-sources.json). La [PR #12](https://github.com/ZapataFrame/FHCP-Challenge/pull/12) registra la entrega y sus verificaciones; la entrega está integrada en `main` y el issue #2 está cerrado. No se presentan implementaciones ni resultados experimentales.

El [entregable del issue #5](docs/research/evolution-and-fitness.md) conecta codificación, decodificación, evaluación y búsqueda; compara conteo de conexiones faltantes y sus transformaciones, evaluación binaria, ponderación y continuidad como desempate. Incluye ejemplos conceptuales con cierre, validación independiente, fuentes y evidencias. Las dependencias #3 y #2 están satisfechas mediante las [PR #11](https://github.com/ZapataFrame/FHCP-Challenge/pull/11) y [PR #12](https://github.com/ZapataFrame/FHCP-Challenge/pull/12), ya integradas; el documento y el manifiesto de #2 consultados en `0642c4f` coinciden con la versión aceptada. La [PR #14](https://github.com/ZapataFrame/FHCP-Challenge/pull/14) registra la entrega y sus verificaciones; el estado de integración y cierre se consulta en la PR y el issue #5. La selección definitiva del fitness corresponde a M2.

El [entregable del issue #6](docs/research/evaluation-metrics.md) define costo, iteraciones, éxito, tiempo, precisión, recall y F1, con fórmulas, limitaciones y ejemplos conceptuales. Propone evidencia mínima y distingue fallos, timeouts, fitness y validación sin fijar el protocolo de M6. Incorpora #4 y la versión aceptada de #5, integrados mediante las [PR #9](https://github.com/ZapataFrame/FHCP-Challenge/pull/9) y [PR #14](https://github.com/ZapataFrame/FHCP-Challenge/pull/14). La [PR #13](https://github.com/ZapataFrame/FHCP-Challenge/pull/13) registra la entrega, su revisión y las verificaciones de cierre de M1. Las entregas #1–#5 ya están integradas; integrar #13 completa las seis entregas requeridas. El estado de cierre se consulta en el issue #6 y el milestone M1; no se presentan mediciones ni se completan M2–M7.

## Definición del problema y dataset

El [milestone M2](https://github.com/ZapataFrame/FHCP-Challenge/milestone/2) convierte la investigación de M1 en decisiones revisadas para implementar el proyecto.

| Tarea | Responsable | Issue | Depende de |
| --- | --- | --- | --- |
| Acordar stack y preparar el entorno mínimo | Junior Arturo Vázquez Leonel · @Arturo2430 | [#15](https://github.com/ZapataFrame/FHCP-Challenge/issues/15) | — |
| Seleccionar instancias FHCP y registrar procedencia | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#16](https://github.com/ZapataFrame/FHCP-Challenge/issues/16) | — |
| Definir los contratos de grafo y ruta | César Euresti · @cesar-upv | [#17](https://github.com/ZapataFrame/FHCP-Challenge/issues/17) | — |
| Seleccionar el costo o fitness de búsqueda | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#18](https://github.com/ZapataFrame/FHCP-Challenge/issues/18) | #17 |
| Definir el contrato del solver y su resultado | Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON | [#19](https://github.com/ZapataFrame/FHCP-Challenge/issues/19) | #15, #18 |

Las cinco entregas #15–#19 están integradas en `main` y sus issues están cerrados.

El contrato de grafo y ruta del [#17](https://github.com/ZapataFrame/FHCP-Challenge/issues/17) está integrado mediante la [PR #22](https://github.com/ZapataFrame/FHCP-Challenge/pull/22). El [costo de búsqueda del #18](docs/decisions/fitness.md) está integrado mediante la [PR #23](https://github.com/ZapataFrame/FHCP-Challenge/pull/23), commit `d3bb853`; el issue #18 está cerrado.

El [contrato de solver y resultado del #19](docs/decisions/solver-and-result-contracts.md) se integró mediante la [PR #25](https://github.com/ZapataFrame/FHCP-Challenge/pull/25), commit `f35688c`. Define entradas, aleatoriedad, presupuestos, estados, contadores y evidencia por intento. Sus ejemplos son conceptuales.

**Cierre de M2:** cinco entregas revisadas e integradas, decisiones trazables en `docs/decisions/`, selección FHCP con procedencia verificable y entorno mínimo con comandos comprobados. La carga y la validación ejecutables corresponden a M3; el protocolo de comparación, a M6.

El [entorno mínimo del #15](docs/decisions/stack-and-tooling.md) usa CPython 3.14.10, NumPy, venv, pip y pytest, con versiones fijadas y [comandos de instalación](README.md#entorno-de-desarrollo). Se comprobó en dos entornos nuevos de Linux x86_64. ELIAS DE JESUS ZUÑIGA DE LEON [reportó tres pruebas aprobadas, ausencia de conflictos y pines exactos en Windows](https://github.com/ZapataFrame/FHCP-Challenge/pull/24#issuecomment-6744109184) sobre `e0976ac`; la salida publicada fue aceptada como evidencia. La [PR #24](https://github.com/ZapataFrame/FHCP-Challenge/pull/24) está integrada en `main` mediante `4ef50bb` y el issue #15 está cerrado. No se han implementado solvers.

## Carga de grafos y validación

El [milestone M3](https://github.com/ZapataFrame/FHCP-Challenge/milestone/3) implementa el [contrato de grafo y ruta](docs/decisions/graph-and-route-contracts.md) con el [stack de M2](docs/decisions/stack-and-tooling.md) y la [selección FHCP](docs/decisions/dataset-selection.md).

| Tarea | Responsable | Issue | Depende de |
| --- | --- | --- | --- |
| Grafo CSR y operaciones de ruta | César Euresti · @cesar-upv | [#26](https://github.com/ZapataFrame/FHCP-Challenge/issues/26) | — |
| Lectores HCP y TOUR | Junior Arturo Vázquez Leonel · @Arturo2430 | [#27](https://github.com/ZapataFrame/FHCP-Challenge/issues/27) | #26 |
| Validador independiente | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#28](https://github.com/ZapataFrame/FHCP-Challenge/issues/28) | #26 |
| Carga verificada con el manifiesto | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#29](https://github.com/ZapataFrame/FHCP-Challenge/issues/29) | #27 |
| Integración y pruebas sobre FHCP | Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON | [#30](https://github.com/ZapataFrame/FHCP-Challenge/issues/30) | #28, #29 |

El núcleo del [#26](https://github.com/ZapataFrame/FHCP-Challenge/issues/26) se integró mediante la [PR #32](https://github.com/ZapataFrame/FHCP-Challenge/pull/32), con CSR inmutable, mapeo reversible y operaciones de ruta, conforme a la [adaptación del contrato a Python](docs/decisions/graph-and-route-contracts.md#adaptación-a-python-del-núcleo-26). Sus pruebas usan grafos sintéticos; los comandos están en [README](README.md#núcleo-de-grafos-y-rutas) y su evidencia se registra en la PR.

Las entregas #26–#29 están integradas y sus issues están cerrados. Las dependencias de cierre del #30 están satisfechas; M3 permanece abierto hasta revisar e integrar esa última entrega.

Los lectores del [#27](https://github.com/ZapataFrame/FHCP-Challenge/issues/27) se integraron mediante la [PR #34](https://github.com/ZapataFrame/FHCP-Challenge/pull/34). Implementan el perfil HCP/TOUR y errores con código, línea y detalle conforme a la [adaptación Python de los lectores](docs/decisions/graph-and-route-contracts.md#adaptación-a-python-de-los-lectores-27). Sus comandos están en [README](README.md#lectores-hcp-y-tour). La carga verificada y las pruebas de integración de la selección corresponden a #29 y #30.

El validador del [#28](https://github.com/ZapataFrame/FHCP-Challenge/issues/28) se integró mediante la [PR #33](https://github.com/ZapataFrame/FHCP-Challenge/pull/33), commit `56a4c0e`. Incluye certificación independiente y pruebas sintéticas de legalidad, aristas, cierre y conservación de entradas, con comandos en [README](README.md#validador-independiente-de-ciclos).

La carga verificada del [#29](https://github.com/ZapataFrame/FHCP-Challenge/issues/29) se integró mediante la [PR #35](https://github.com/ZapataFrame/FHCP-Challenge/pull/35), commit `92a3186`. Resuelve el miembro por ID, verifica sus bytes y metadatos, y carga certificados por separado. Incluye una prueba con `graph1` y rechazos en copias temporales; los comandos están en [README](README.md#carga-fhcp-con-procedencia-verificada).

La entrega del [#30](https://github.com/ZapataFrame/FHCP-Challenge/issues/30), presentada en la [PR #36](https://github.com/ZapataFrame/FHCP-Challenge/pull/36), añade [pruebas de integración](tests/test_fhcp_integration.py) y [pasos de reproducción y evidencia](README.md#integración-fhcp-de-extremo-a-extremo). Se comprobaron en Windows los 18 archivos seleccionados, los nueve certificados por lectura, conversión y validación independiente, y casos negativos controlados. Pasaron 38 pruebas nuevas y las 383 de la suite completa con el entorno aprobado del #15; esta entrega no se ejecutó en Linux. El issue #30 y M3 siguen abiertos durante la revisión; no se añaden solvers ni benchmarking.

**Cierre de M3:** cinco entregas revisadas e integradas, carga de instancias reales con procedencia comprobada, certificación independiente de los nueve tours seleccionados y pruebas positivas y negativas de formato, cobertura, unicidad, aristas y cierre. Registrar en README los pasos ejecutados para repetir las pruebas. La CLI de solver y el GA corresponden a M4; la comparación experimental, a M6.

## Algoritmo genético base

Los operadores del [#38](https://github.com/ZapataFrame/FHCP-Challenge/issues/38), a cargo de César Euresti · @cesar-upv, se entregan mediante la [PR #45](https://github.com/ZapataFrame/FHCP-Challenge/pull/45): inicialización por permutación, cruce OX e intercambio de posiciones distintas, con RNG inyectado o decisiones explícitas. El [contrato](docs/decisions/ga-permutation-operators.md) fija sus límites y los [comandos de pruebas](README.md#operadores-de-permutación-del-ga) permiten comprobarlos sin dataset. Esta entrega no incluye bucle evolutivo ni completa M4.

El costo de búsqueda del [#37](https://github.com/ZapataFrame/FHCP-Challenge/issues/37) se integró mediante la [PR #44](https://github.com/ZapataFrame/FHCP-Challenge/pull/44) en `src/evaluation/` conforme al #18, con recálculo completo, rechazos con contexto y pruebas independientes del solver. La API y comandos están en [README](README.md#costo-de-búsqueda). Esta entrega es una dependencia del GA #40 junto con los operadores #38 y el control de ejecución #39; no completa M4.

El [#39](https://github.com/ZapataFrame/FHCP-Challenge/issues/39) entrega la
[API de ejecución secuencial](docs/decisions/solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39).
Define cómo el GA admite trabajo, conserva el mejor candidato, contabiliza el
presupuesto y registra la certificación. El [#40](https://github.com/ZapataFrame/FHCP-Challenge/issues/40)
consumirá esta API junto con el costo y los operadores de permutación.

El GA del [#40](https://github.com/ZapataFrame/FHCP-Challenge/issues/40), a cargo de Junior Arturo Vázquez Leonel · @Arturo2430, se integró mediante la [PR #46](https://github.com/ZapataFrame/FHCP-Challenge/pull/46) en `b58d5f5`. La [decisión de la variante](docs/decisions/ga-baseline.md) define los torneos, el cruce OX, la mutación, el elitismo y el presupuesto. Los [comandos del README](README.md#ga-generacional-base) reproducen las pruebas sintéticas.

La [CLI individual del #41](https://github.com/ZapataFrame/FHCP-Challenge/issues/41), a cargo de Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON, está integrada mediante la [PR #47](https://github.com/ZapataFrame/FHCP-Challenge/pull/47). Incluye ejecución FHCP, salida JSON y guardado por intento. La [receta verificada en Windows](README.md#cli-individual-del-ga) reproduce el ejemplo real y el fallo controlado.

El [#42](https://github.com/ZapataFrame/FHCP-Challenge/issues/42), a cargo de Diego Eduardo Zapata Aguilar · @ZapataFrame, se entrega mediante la [PR #48](https://github.com/ZapataFrame/FHCP-Challenge/pull/48), con [pruebas y pasos de reproducción](README.md#reproducción-e-integración-del-ga). Repite la CLI sobre `graph1`, contrasta candidato, costo y contadores, y conserva cada intento. La prueba sintética del GA comprueba por separado un éxito certificado. Las dependencias #37–#41 están integradas y sus issues cerrados. La integración de la PR #48 completa los criterios de cierre de M4.

## Metaheurísticas adicionales

El [milestone M5](https://github.com/ZapataFrame/FHCP-Challenge/milestone/5)
implementa las cinco familias restantes sobre el GA, la carga y la validación
integrados en M4. Se usan las [adaptaciones investigadas en M1](docs/research/metaheuristics.md),
el [costo común](docs/decisions/fitness.md) y el
[contrato de ejecución](docs/decisions/solver-and-result-contracts.md).
Cada solver registra y somete a revisión su variante, parámetros y consecuencias
en la decisión indicada por su issue.

| Tarea | Responsable | Issue | Depende de |
| --- | --- | --- | --- |
| Implementar el decodificador de claves reales | César Euresti · @cesar-upv | [#49](https://github.com/ZapataFrame/FHCP-Challenge/issues/49) | — |
| Implementar recocido simulado con intercambio | César Euresti · @cesar-upv | [#50](https://github.com/ZapataFrame/FHCP-Challenge/issues/50) | — |
| Implementar Ant System con penalización de pares ausentes | Junior Arturo Vázquez Leonel · @Arturo2430 | [#51](https://github.com/ZapataFrame/FHCP-Challenge/issues/51) | — |
| Implementar Artificial Bee Colony discreto | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#52](https://github.com/ZapataFrame/FHCP-Challenge/issues/52) | — |
| Implementar DE/rand/1/bin sobre claves reales | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#53](https://github.com/ZapataFrame/FHCP-Challenge/issues/53) | #49 |
| Implementar PSO global sobre claves reales | Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON | [#54](https://github.com/ZapataFrame/FHCP-Challenge/issues/54) | #49 |
| Integrar las metaheurísticas adicionales en la CLI y RunRecord | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#55](https://github.com/ZapataFrame/FHCP-Challenge/issues/55) | #50, #51, #52, #53, #54 |
| Verificar la integración reproducible y los criterios de cierre de M5 | Diego Eduardo Zapata Aguilar · @ZapataFrame | [#56](https://github.com/ZapataFrame/FHCP-Challenge/issues/56) | #55 |

El decodificador, SA, Ant System y ABC pueden iniciarse en paralelo. DE y PSO
requieren el decodificador aceptado. La integración de la CLI espera a los cinco
solvers y la verificación de cierre espera a esa integración. Los bloqueos están
registrados como dependencias nativas en GitHub. Cada issue contiene el alcance,
entregable, fuentes y criterios de aceptación.

Las variantes previstas son SA con intercambio y enfriamiento geométrico,
Ant System con penalización de pares ausentes, ABC discreto, DE/rand/1/bin y PSO
global con claves reales. ABC conserva las fases de empleadas, observadoras y
exploración del [informe de Karaboga](https://abc.erciyes.edu.tr/pub/tr06_2005.pdf).
El decodificador ordena por clave e índice, conforme a la construcción del #2 y
la [separación entre claves y decodificación de Gonçalves y Resende](https://optimization-online.org/wp-content/uploads/2009/10/2423.pdf).
Las vecindades, penalizaciones y adaptaciones a FHCP son elecciones del proyecto
que deben documentarse y comprobarse durante la implementación.

**Criterios de cierre de M5**

Integrar las ocho entregas revisadas. Cada familia debe respetar semilla,
presupuestos, contadores, fases parciales y certificación independiente. La CLI
debe registrar su variante y parámetros efectivos y conservar los comandos
existentes del GA. La verificación final debe reproducir las cinco familias sobre
una instancia seleccionada, comprobar éxitos sintéticos certificados y agotamientos
coherentes, y registrar commit, entorno y salidas. El hito permanece abierto hasta
aceptar e integrar esa verificación. El protocolo de comparativas y los resultados
experimentales corresponden a M6.

El ABC discreto del [#52](https://github.com/ZapataFrame/FHCP-Challenge/issues/52) está integrado mediante la PR #60 con su [decisión](docs/decisions/abc-baseline.md), pruebas sintéticas y [comandos](README.md#artificial-bee-colony-discreto). Incluye empleadas, observadoras con pesos congelados y hasta una exploradora por ciclo, sobre el control de ejecución común. El issue está cerrado. Su integración en la CLI está en #55 y la verificación de cierre, en #56.

El [#49](https://github.com/ZapataFrame/FHCP-Challenge/issues/49), a cargo de
César Euresti · @cesar-upv, entrega el decodificador común de claves reales
para DE/PSO mediante la [PR #58](https://github.com/ZapataFrame/FHCP-Challenge/pull/58),
con [decisión de representación](docs/decisions/real-key-decoder.md)
y [pruebas sintéticas reproducibles](README.md#decodificador-de-claves-reales).
La evidencia experimental corresponde a M6.

El [#50](https://github.com/ZapataFrame/FHCP-Challenge/issues/50), a cargo de
César Euresti · @cesar-upv, entrega SA con intercambio mediante la
[PR #59](https://github.com/ZapataFrame/FHCP-Challenge/pull/59), con
[decisión de variante](docs/decisions/sa-baseline.md) y
[pruebas sintéticas](README.md#recocido-simulado-con-intercambio).
La integración de las familias en la CLI corresponde al #55 y la verificación
de cierre de M5 al #56.

El [#53](https://github.com/ZapataFrame/FHCP-Challenge/issues/53), a cargo de
Diego Eduardo Zapata Aguilar · @ZapataFrame, entregó mediante la PR #61 DE/rand/1/bin
sobre claves reales, [decisión de variante](docs/decisions/de-baseline.md) y
[comandos de pruebas](README.md#evolución-diferencial-sobre-claves-reales).
La dependencia #49 está integrada. La entrega usa población congelada, reemplazo
por mejora estricta y certificación independiente. El issue está cerrado.
La CLI y la verificación de M5 corresponden a #55–#56.

El [#54](https://github.com/ZapataFrame/FHCP-Challenge/issues/54), a cargo de
Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON, entregó el PSO global
sobre claves reales, con [decisión de variante](docs/decisions/pso-baseline.md)
y [pruebas reproducibles en Windows](README.md#pso-global-sobre-claves-reales).
El issue está cerrado y su entrega está integrada.

El Ant System del [#51](https://github.com/ZapataFrame/FHCP-Challenge/issues/51), a cargo de Junior Arturo Vázquez Leonel · @Arturo2430, está integrado mediante la PR #63 con [decisión de variante](docs/decisions/ant-system-baseline.md), feromonas triangulares compactas y [pruebas sintéticas reproducibles](README.md#ant-system-con-penalización-de-pares-ausentes). Incluye penalización de pares ausentes, depósitos cíclicos acotados y presupuesto comprobado dentro de construcción y actualización. El issue está cerrado. CLI/RunRecord y cierre de M5 corresponden a #55–#56, y la evidencia experimental, a M6.


La integración del [#55](https://github.com/ZapataFrame/FHCP-Challenge/issues/55) está aceptada e integrada mediante la [PR #64](https://github.com/ZapataFrame/FHCP-Challenge/pull/64) con selección de familia, parámetros por variante, metadatos RunRecord y [comandos comprobados](README.md#cli-de-metaheurísticas-adicionales). Las cinco dependencias están integradas. El issue #55 está cerrado.

La entrega del [#56](https://github.com/ZapataFrame/FHCP-Challenge/issues/56),
a cargo de Diego Eduardo Zapata Aguilar · @ZapataFrame, reúne las
[pruebas y pasos de cierre de M5](README.md#verificación-de-integración-de-m5).
Las dos ejecuciones por familia coinciden en candidato, costo y contadores,
con conservación de registros y auditoría independiente. Cada familia también
supera un caso sintético certificado. Las dependencias #49–#55 están integradas
y sus issues cerrados. La integración de esta entrega completa los criterios
de M5; la comparación experimental pertenece a M6.

## Benchmarking reproducible

El [milestone M6](https://github.com/ZapataFrame/FHCP-Challenge/milestone/6)
parte de la integración del #56, aceptada mediante la
[PR #66](https://github.com/ZapataFrame/FHCP-Challenge/pull/66). Sus pruebas de humo
no son una campaña experimental. El [protocolo](docs/decisions/benchmark-protocol.md)
y el [catálogo versionado](experiments/configs/benchmark-v1.json) del #67 están integrados mediante la PR #72. El ejecutor #68 está integrado mediante la PR #73;
la campaña v3 de #70 conserva ajuste y configuraciones congeladas, integrada
mediante PR #77 con respaldo en Drive. #71 presenta contraste y auditoría para revisión.

| Tarea | Responsable | Issue | Depende para cierre de |
| --- | --- | --- | --- |
| Definir protocolo, configuraciones y contratos de evidencia | César Euresti · @cesar-upv | [#67](https://github.com/ZapataFrame/FHCP-Challenge/issues/67) | #56 (integrado) |
| Implementar ejecución reproducible por lotes y humo | Eder Omar Zúñiga Zavala · @KirbyStone69 | [#68](https://github.com/ZapataFrame/FHCP-Challenge/issues/68) | #67 |
| Generar métricas, tablas y gráficos reproducibles | Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON | [#69](https://github.com/ZapataFrame/FHCP-Challenge/issues/69) | #67, #68 |
| Ejecutar ajuste, congelar configuraciones y auditar campaña | Junior Arturo Vázquez Leonel · @Arturo2430 | [#70](https://github.com/ZapataFrame/FHCP-Challenge/issues/70) | #67, #68, #69 |
| Comparar con referencias FHCP y verificar cierre | Junior Arturo Vázquez Leonel · @Arturo2430 (delegación de Diego Eduardo Zapata Aguilar · @ZapataFrame) | [#71](https://github.com/ZapataFrame/FHCP-Challenge/issues/71) | #67, #68, #69, #70 |

Se pueden preparar herramientas con fixtures, pero su integración depende del
protocolo aceptado. #70 no inicia evaluación antes de completar ajuste y congelación.
El [comando de verificación del plan](README.md#protocolo-del-benchmark-m6) comprueba
compatibilidad con las APIs actuales; no implementa las herramientas de #68/#69.
#67–#70 están cerrados con sus PR integradas; #71 permanece abierto durante revisión.

**Criterios de cierre de M6:** integrar las cinco entregas aceptadas y verificar
instancias, semillas, configuraciones y presupuestos congelados; manifiestos y
crudos de todas las repeticiones conservados; éxitos recertificados; errores y
timeouts en denominadores explícitos; tablas y gráficos regenerables; contraste
con referencias primarias con sus limitaciones. #71 reúne la evidencia de cada
criterio y confirma las dependencias integradas. Abrir una PR o aprobar el protocolo
no completa el hito. El informe LaTeX pertenece a M7.

La entrega #68 conserva un [humo completo de 12 ensayos](experiments/results/972e2ae0-f2f3-4375-91b7-ef10e9641b10/manifest.json)
con preflight real, seis familias y dos grafos. Todos agotaron normalmente
20 evaluaciones; no es una campaña de evaluación. La PR #73 está integrada.

La entrega #69 añade auditoría, tablas CSV/JSON y figuras SVG/PNG regenerables
desde el humo aceptado. La campaña #70 está medida e integrada; el contraste y auditoría
#71 se presentan para revisión.

La preparación histórica v2 de #70 registra una
[revisión previa del entorno](docs/decisions/benchmark-protocol-v2.md)
y un coordinador reanudable. Esa preparación no incluía ajuste completo ni
ganadoras; la evidencia medida v3 se describe más abajo. La PR #74 integra #69.

**Traspaso histórico de #70:** preparación integrada mediante PR #75. Por indicación del
usuario, el cómputo prolongado se delegó a otro integrante. Se conservan 12/12
ensayos de humo v2 y 2/120 de ajuste; en ese estrato quedaron pendientes
evaluación, escala, congelación y verificación. El [traspaso](docs/experiments/m6-handoff.md) describe la evidencia
y cómo continuar sin mezclar equipos ni sustituir primarios. Ese pendiente de #70 quedó cubierto posteriormente por la campaña v3; #71 y M6 siguen abiertos.

**Preparación v3 de #70:** el responsable eligió la laptop i5-12450H
y aceptó la revisión v3 en este chat, autorizando su commit local.
La [revisión v3](docs/decisions/benchmark-protocol-v3.md) y su configuración
registran el equipo y conservan todas las decisiones de búsqueda de v1/v2.
La [receta de terminal](README.md#campaña-en-esta-laptop-m6-v3) permite comprobar
recursos sin búsqueda y, después de aceptar la revisión y registrar un commit
limpio, crear una campaña nueva. Los intentos v2 permanecen separados.

**Campaña v3 medida de #70:** la [entrega y recuperación](docs/experiments/m6-results.md)
conserva 1,044 procesos completos en el commit limpio `2299403`: 12 iniciales,
120 de ajuste, 720 de evaluación, 180 de escala y 12 de verificación. Los 900
primarios de evaluación/escala tuvieron cero éxitos certificados; los seis pares
de reproducibilidad coincidieron. Se conservaron las incidencias y se comprobó
la recuperación de los cinco respaldos locales. La duración de pared fue
7 h 01 min 36 s, incluidas pausas.

La PR incluye evidencia consultable y los enlaces a los cinco `.tar.gz`
publicados en Drive, con acceso institucional y hashes de recuperación. La
entrega del #70 está integrada mediante PR #77 y el issue está cerrado.
#71 se cierra al integrar PR #78; el cierre administrativo de M6 exige comprobar las cinco entregas aceptadas.

**Contraste y auditoría #71:** la [entrega](docs/research/benchmark-comparison.md)
registra fuentes primarias, 72 celdas propias, contraste por ID con condiciones
no equivalentes, y recuperación/regeneración comprobada de las cinco fases desde
el commit aceptado de main. Su matriz enlaza cada criterio de M6 y confirma
#67–#70 / PR #72/#73/#74/#77 integradas. La recuperación se repitió y el contraste volvió a comprobarse el 17 de
noviembre; al integrar PR #78 y verificar el cierre de #67–#71 se completa M6.
M7 recibe tablas, figuras, bibliografía, trazabilidad y limitaciones para integrar
la plantilla LaTeX, redactar y verificar el informe PDF.

## Mejoras exploratorias posteriores a la campaña

Por solicitud del responsable, una rama independiente incorpora
[inicialización voraz y guía por aristas](docs/decisions/graph-guided-search.md)
como políticas opcionales: inicialización en GA/SA/ABC/DE/PSO, inversión guiada en
GA/SA/ABC y construcción por vecinos en AS. El protocolo y los resultados M6
permanecen separados. La verificación cubre invariantes, semillas, presupuestos y
certificación; la evaluación con múltiples semillas requiere una campaña nueva.
No acredita una mejora estadística ni completa por sí sola un milestone.

La siguiente revisión exploratoria añade [costo incremental en SA/ABC,
recalentamiento de SA y feromonas por arista en AS](docs/decisions/search-enhancements.md).
Son políticas opcionales con contadores, verificaciones y versiones separadas;
las pruebas de integración no sustituyen una campaña comparativa nueva.

El seguimiento de estas mejoras corresponde al [issue #79](https://github.com/ZapataFrame/FHCP-Challenge/issues/79),
separado de #71/PR #78. El primer lote exploratorio de tres grafos y diez semillas
por familia terminó 180/180 intentos en 27 min 25 s, sin errores: graph2 produjo
21 ciclos certificados (ABC 10/10, AS 7/10, GA 2/10 y DE 2/10); graph48 y graph74
no produjeron éxitos bajo ese presupuesto. La [actualización de evidencia](https://github.com/ZapataFrame/FHCP-Challenge/pull/78#issuecomment-6861889596)
identifica el lote local, las verificaciones y sus limitaciones. Los crudos nuevos
siguen locales, separados de los respaldos originales; el
[protocolo exploratorio](docs/decisions/search-exploration-40min.md) conserva el plan.
Esta evidencia no aísla el efecto de cada cambio ni sustituye la comparación M6.

## Evaluación experimental FHCP

El ejecutador integrado mediante la [PR #82](https://github.com/ZapataFrame/FHCP-Challenge/pull/82)
es [reanudable](docs/decisions/distributed-campaigns.md)
para los 1001 grafos, sin nuevos cambios en algoritmos. La preparación no inició
búsquedas; las sesiones posteriores se consolidaron al cierre del #94.
El [plan 10×60](experiments/configs/distributed-fhcp-10x60.json) incluye todos los
grafos de la ejecución anterior, seis familias, 10 semillas (1001–1010) y 60 s de solver
por intento, sin límite de evaluaciones. Sus 60,060 intentos se reparten entre
las cinco cuentas del equipo (220 para Arturo, 196 para Zapata y 195 para cada integrante restante); el techo agregado
de búsqueda es 1001 h, sin sobrecarga. Estos conteos corresponden a la cola completa de candidatos; la meta original era alcanzar
60 grafos distintos certificados por sesiones, sin exigir agotar los 1001.
El alcance de entrega se cerró posteriormente con el corte parcial descrito abajo. Los pendientes se conservan como tales; no se sustituye ni borra M6.

El catálogo completo conserva hashes y parser; la selección histórica de nueve
grafos permanece intacta. Se implementan recuperación sin repetir primarios,
auditoría, agregación sin duplicados y ZIP con SHA-256. Los
[issues por integrante y destinos de Drive](docs/experiments/distributed-campaign-issues/README.md)
incluyen listas de grafos, instalación y comandos para sesiones de 60 minutos,
reanudación y entrega final del ZIP, checksum y tablas. La carpeta
`FHCP-evaluation` tiene los cinco destinos y acceso de edición del equipo;
los respaldos M6 permanecen separados en `M6-original-prueba-inicial`.
La preparación 10×60 se sigue en el
[issue #88](https://github.com/ZapataFrame/FHCP-Challenge/issues/88), sobre el
ejecutador integrado de #81/PR #82 y los algoritmos de #79/PR #80.
Los cinco issues fijan la revisión de código, el plan compartido y los destinos
de entrega, con comandos reproducibles para Linux y Windows.
La [entrega conjunta de #94](docs/experiments/distributed-evaluation.md) recupera
las cinco entregas de #83–#87, integradas mediante las PR #90–#93 y #95:
7,383 intentos, 300 éxitos certificados por intento, 14 grafos distintos
resueltos y 12 incidencias conservadas. Se conciliaron 60 combinaciones en
121 grafos; cuatro quedaron parciales y 876 sin iniciar. ZIPs, hashes,
perfiles y tablas sustentan la agregación reproducible; no se lanzaron
nuevas búsquedas para consolidar.

Arturo solicitó cerrar esta entrega y documentar que se esperaban
aproximadamente 20 grafos resueltos. El resultado fue 14: no se alcanzó
esa referencia aproximada ni la meta original de 60. La
[decisión de cierre](docs/decisions/distributed-evaluation-cutoff.md) acepta
este alcance parcial, conserva 52,677 combinaciones pendientes fuera de la
entrega y no altera el plan. Los resultados y tablas están en
`experiments/results/team-evaluation-20261117/`; cerrar #94 no completa por
sí solo M6 ni el informe final.

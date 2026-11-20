# Costo de búsqueda para candidatos hamiltonianos

## Estado y alcance

**Estado:** propuesta completa para revisión del responsable y del equipo; vigente únicamente después de su aceptación e integración en `main`.

- Responsable del issue: Eder Omar Zúñiga Zavala · @KirbyStone69.
- Seguimiento: [issue #18](https://github.com/ZapataFrame/FHCP-Challenge/issues/18), M2.
- Dependencia satisfecha: [issue #17](https://github.com/ZapataFrame/FHCP-Challenge/issues/17), integrado mediante la [PR #22](https://github.com/ZapataFrame/FHCP-Challenge/pull/22), commit `3aea2538631116e3e347e4993873fe1885582ff2`.
- Contrato de referencia: [grafo y ruta](graph-and-route-contracts.md), versión integrada el 7 de noviembre de 2026.
- Preparación del borrador: Codex, a solicitud del responsable. La revisión y el acuerdo del equipo están pendientes.
- Entregable: propuesta de evaluación de cada candidato; no implementa algoritmos, reglas de estancamiento ni un protocolo experimental.

## Contexto

El objetivo es encontrar un ciclo hamiltoniano en un grafo no dirigido y no ponderado. Se requiere una valoración que permita comparar candidatos antes de encontrar un ciclo válido. El fitness no mide distancia recorrida ni rendimiento de una generación o población.

La [investigación del #5](../research/evolution-and-fitness.md), especialmente sus secciones 4–8, compara señales, ejemplos y limitaciones. La [representación del #3](../research/search-space.md) y las [adaptaciones del #2](../research/metaheuristics.md) aportan supuestos para discutir esta decisión. Las [métricas del #6](../research/evaluation-metrics.md) corresponden a ejecuciones, no a la calidad de un candidato.

Este borrador reutiliza esos razonamientos y fuentes. No presenta una fórmula nueva ni resultados experimentales; no afirma que la alternativa preferida sea la mejor en FHCP.

## Compatibilidad con el contrato aceptado de grafo y ruta

Se adopta el #17 como contrato, en lugar de las convenciones provisionales de M1:

- Grafo simple, no dirigido, sin pesos e inmutable; almacenamiento CSR con vecinos ordenados. Se consulta únicamente mediante sus operaciones públicas.
- Índices internos I = {0, ..., n-1}; etiquetas externas ordenadas y mapeo reversible. El costo no utiliza diferencias numéricas entre etiquetas.
- Ruta legal: exactamente n índices enteros, distintos y dentro de I, con cierre implícito. Se comprueba con `check_route_legality(n, route)`.
- Cada par se consulta mediante `graph.has_edge(u, v)`, que busca en la fila más corta. No se presupone consulta constante.
- `canonical_route` se reserva para registro y deduplicación. Evaluar no modifica, reordena, repara ni canonicaliza la ruta.

El grafo admite n >= 1, pero el costo de búsqueda hamiltoniana se define solo para **n >= 3**. Para n = 1 o n = 2 se devuelve `graph_too_small`, sin valor numérico. Esto no rechaza su carga ni cambia la legalidad de sus rutas: restringe el dominio de esta evaluación conforme al objetivo de ciclo simple. En particular, sumar sin esa condición daría cero en `[0,1]` con una única arista, al contar ida y vuelta sobre ella; no sería un ciclo simple válido.

El conjunto de aristas en índices internos se denota por E_I. Una entrada externa se convierte con `route_to_internal` antes de evaluar; `unknown_label` e `invalid_label_type` pertenecen a esa conversión. Los certificados oficiales se reservan para comprobación y no intervienen en el costo ni sirven como ruta objetivo de la búsqueda.

## Alternativas consideradas

| Alternativa | Ventaja | Limitación y postura provisional |
| --- | --- | --- |
| Conteo de conexiones faltantes | Entero, interpretable; cero equivale al objetivo dentro del dominio legal. | Produce empates y no mide esfuerzo de reparación. Se propone como costo común inicial. |
| Conteo normalizado o transformado en aptitud | Permite adaptar escala y sentido a cada método. | Conserva el orden en una instancia, pero puede cambiar selección proporcional o aceptación. Es una adaptación, no una señal adicional. |
| Evaluación binaria | Distingue cumplimiento e incumplimiento. | Empata todos los candidatos no factibles. No se propone como guía principal. |
| Penalización ponderada | Permite priorizar ciertos incumplimientos. | Requiere justificar pesos artificiales positivos y puede preferir más faltantes de menor peso. No se propone sin una hipótesis y comparación. |
| Desempate por continuidad | Distingue algunos candidatos con igual conteo. | Una racha larga no garantiza reparación fácil; añade sesgo y complejidad. Se reserva como alternativa futura. |

La comparación procede del #5. Evaluar movimientos vecinos para estimar facilidad de reparación también añadiría una búsqueda local y consumo de presupuesto; no se incorpora al costo común sin una comparación que justifique ese trabajo. La información de diversidad de población o generaciones sin mejora pertenece al algoritmo, no al valor de una ruta.

## Elección propuesta: conteo entero de conexiones faltantes

**Se elige para esta propuesta minimizar el conteo entero de conexiones faltantes por ruta legal, sujeto a revisión del equipo:**

$$
C(p)=\sum_{i=0}^{n-1}\mathbf{1}\left[\{p_i,p_{(i+1)\bmod n}\}\notin E_I\right].
$$

- **Dominio:** pares (G, p) donde G cumple el #17, n >= 3 y p es una ruta legal de I. La notación C(p) supone el grafo fijo.
- **Rango:** enteros de 0 a n, inclusive; no todos tienen que ser alcanzables en cada grafo.
- **Sentido:** minimizar; un costo menor es preferible.
- **Objetivo:** C(p) = 0, seguido de certificación independiente.
- **Unidad:** número de pares consecutivos ausentes, incluido el cierre.

Sobre el dominio, la permutación garantiza cobertura y unicidad; los n pares presentes garantizan adyacencia y retorno. Por eso el cero caracteriza un ciclo válido matemáticamente. En software, el valor calculado no sustituye al validador.

La elección se justifica por su correspondencia directa con las restricciones y por evitar pesos o prioridades sin sustento experimental. Su sencillez facilita comprobar resultados y coordinar los seis métodos; no acredita superioridad de búsqueda.

### Evaluación y rechazos

La operación conceptual `evaluate_cost(graph, route)` devuelve **un entero** si la entrada pertenece al dominio; en otro caso, un rechazo con código y contexto, **sin costo**. No se usa un valor centinela, infinito ni una conversión implícita. El tipo concreto de retorno y su integración en el resultado del solver corresponden al stack y al #19.

Orden de comprobación:

1. `graph.vertex_count() < 3`: `graph_too_small`.
2. `check_route_legality(n, route)`: propagar el primer rechazo con el mismo código, posición e índices del #17: `invalid_length`, `invalid_vertex_type`, `unknown_vertex` o `repeated_vertex`.
3. Solo después de aceptar el dominio, contar los n pares con `has_edge`, incluido el cierre. Un par ausente suma uno; no produce un rechazo de evaluación.

```text
evaluate_cost(graph, route):
    n = graph.vertex_count()
    if n < 3: reject("graph_too_small")
    check_route_legality(n, route)   # propagar rechazo y contexto si falla
    cost = 0
    for i in 0 .. n-1:
        if not graph.has_edge(route[i], route[(i+1) mod n]):
            cost = cost + 1
    return cost
```

Es pseudocódigo normativo de la propuesta, no una implementación. `reject` termina la evaluación. Booleanos, reales (incluso `1.0`) y cadenas se rechazan como índices, igual que en #17. La cobertura se deduce de longitud, pertenencia y unicidad; no se agrega un código para omisiones.

Los prefijos constructivos y las listas con cierre explícito reciben `invalid_length`. Si un algoritmo repara un candidato, debe entregar la ruta reparada legal y contabilizar ese trabajo. El evaluador no oculta defectos del productor mediante reparación. Un `invalid_vertex_index` de `has_edge` después de comprobar legalidad indicaría una discrepancia de implementación, no una conexión faltante.

## Ejemplos conceptuales

Se reutiliza el grafo didáctico compartido por #5 y #17, ajeno al dataset; sus etiquetas externas son `[10,20,30,40,50]`:

I = {0,1,2,3,4}; E_I = {{0,1},{1,2},{2,3},{3,4},{0,4},{0,2},{1,3}}.

| Candidato | Resultado del costo propuesto | Motivo |
| --- | --- | --- |
| [0,1,2,3,4] | 0 | Existen los cuatro pares internos y el cierre 4–0. |
| [0,1,3,2,4] | 1 | Falta 2–4; el cierre sí existe. |
| [1,0,2,3,4] | 1 | Existen los pares internos; falta el cierre 4–1. |
| [1,3,0,4,2] | 2 | Faltan 3–0 y 4–2; el cierre 2–1 existe. |
| [0,1,3,1,2] | `repeated_vertex`, posición 3; sin costo | Repite 1 y omite 4, aunque todos sus pares cíclicos existen. |
| [0,1,3,4] | `invalid_length`; sin costo | Longitud incorrecta y falta 2. |
| [0,1,2,3,5] | `unknown_vertex`, posición 4; sin costo | Índice 5 ajeno al dominio. |
| [0,1,2,3,4,0] | `invalid_length`; sin costo | Cierre explícito rechazado por el contrato. |
| [0,1,2,3,1.0] | `invalid_vertex_type`, posición 4; sin costo | No se convierte un real a índice. |
| [0,1,2,3,true] | `invalid_vertex_type`, posición 4; sin costo | Un booleano no es un índice entero. |
| [0,1,2,3,"4"] | `invalid_vertex_type`, posición 4; sin costo | No se convierte una cadena a índice. |

La ruta externa `[30,40,50,10,20]` se convierte a `[2,3,4,0,1]` y obtiene costo 0. `[10,20,30,40,60]` falla en la conversión con `unknown_label`, antes de evaluar.

Otros casos fijan los extremos del dominio:

| Grafo | Ruta | Evaluación | Certificación independiente |
| --- | --- | --- | --- |
| Un vértice sin aristas | `[0]` | `graph_too_small`, sin costo | `graph_too_small` |
| Dos vértices unidos | `[0,1]` | `graph_too_small`, sin costo | `graph_too_small` |
| Triángulo completo | `[0,2,1]` | 0 | Válida |
| Tres vértices sin aristas | `[0,1,2]` | 3 | `missing_edge`, posición 0 |
| Camino 0–1–2–3–4 | `[0,1,2,3,4]` | 1 | `missing_closing_edge`, posición 4 |

Son cálculos conceptuales, no ejecuciones de un solver ni resultados experimentales.

## Certificación independiente

Se usa `validate_cycle(graph, route)` del #17, conservando su orden y sus códigos. Puede compartir `check_route_legality` y el acceso al grafo, pero debe recorrer por su cuenta las aristas y el cierre, sin consultar el costo almacenado ni una marca del operador. Por ejemplo, `[0,1,3,2,4]` obtiene costo 1 y rechazo `missing_edge`; `[1,0,2,3,4]` obtiene también 1 y rechazo `missing_closing_edge`. La evaluación agrega incumplimientos; el validador informa el primero según su contrato.

Un costo positivo indica un candidato no factible. Un costo cero solicita certificación: si el validador discrepa, se trata como error que requiere diagnóstico. El contrato de resultados y presupuestos se coordinará con #19; esta decisión no define su esquema.

Agotar tiempo, evaluaciones o generaciones sin certificado no prueba que el grafo sea no hamiltoniano. Un candidato con costo 1 tampoco está necesariamente a un solo movimiento de una solución.

## Adaptaciones necesarias por algoritmo

| Método | Uso de la evaluación y coordinación pendiente |
| --- | --- |
| GA | Torneos o reemplazos pueden preferir costos menores. Una ruleta requiere pesos que favorezcan costos bajos, no usar directamente C como aptitud a maximizar. |
| SA | Comparar diferencias de costo; temperatura compatible con su escala. Cero en temperatura requiere una política explícita. |
| ACO | Evaluar rutas completas incluyendo el retorno. Atractivo local, bloqueo y depósito son reglas adicionales; reforzar pares ausentes debe justificarse. |
| ABC | Comparar costos para mejora y, si se usa selección proporcional, convertirlos en pesos positivos. |
| DE y PSO | Evaluar la ruta decodificada; controlar empates y valores no finitos antes de decodificar. Las operaciones continuas no se aplican directamente a etiquetas. |

Se conserva C como costo común registrado. Cuando la variante necesita pesos positivos de selección, se propone el adaptador F(p) = 1/(1+C(p)), con rango [1/(n+1), 1] y sentido de maximización. El éxito se comprueba con el costo entero y el validador, nunca mediante tolerancias sobre F. Con costos 1 y 2, los pesos son 1/2 y 1/3 y, al normalizarlos para esas dos rutas, las probabilidades son 3/5 y 2/5.

Para SA se usa la diferencia del costo entero, no la diferencia del adaptador de selección. En un empeoramiento y T > 0, la regla propuesta por #2 usa exp(-ΔC/T). Cambiar a C/n exige dividir también T entre n para conservar esa probabilidad; por eso la normalización no se introduce silenciosamente. Para ACO, un depósito Q/(1+C) puede utilizar la misma transformación, pero Q, las aristas que reciben depósito y la política constructiva pertenecen a la variante.

La comparación del costo declara empate cuando C es igual, sin desempate secundario por continuidad, etiquetas o posición del cierre. Cada algoritmo debe declarar cómo maneja ese empate en selección, aceptación y memoria. Las reglas de movimientos, reinicios y terminación siguen fuera del alcance de esta decisión.

## Consecuencias y límites

- Se dispone de un criterio común por ruta, con un significado y objetivo verificables.
- Rotación e inversión del recorrido conservan el costo en el grafo no dirigido. El renombrado consistente de vértices tampoco lo cambia.
- Existen mesetas: rutas diferentes pueden compartir costo. El conteo no estima la cantidad mínima de movimientos ni el tiempo necesario para reparar una ruta.
- Escapar del estancamiento requiere mecanismos de búsqueda; no se garantiza por esta función.
- Con el CSR aceptado, el tiempo completo es O(n + Σᵢ log(1 + min(d(pᵢ), d(pᵢ₊₁)))), con subíndices cíclicos. Si Δ es el grado máximo, una cota es O(n(1 + log(1 + Δ))). El término O(n) incluye comprobar dominio y recorrer posiciones incluso en grafos sin aristas. No se afirma O(n) general con el acceso actual. La memoria auxiliar para legalidad es O(n); el contador usa O(1) adicional.
- En DE/PSO, ordenar claves añade O(n log n) antes de esta evaluación. Una futura actualización incremental de un intercambio puede reducir el número de consultas, pero no convierte `has_edge` en O(1) ni evita comprobar su equivalencia con el costo completo.
- Decodificación, copia, construcción, reparación y validación también cuestan recursos. Una evaluación incremental futura debe contrastarse con el recálculo completo, especialmente cerca del cierre.
- Las comparaciones experimentales y cualquier revisión de esta elección corresponden a entregas posteriores; no se fijan semillas, repeticiones o presupuestos en este borrador.

## Criterios de aceptación de la implementación futura

M3–M5 deberán comprobar que la implementación respeta este contrato: ejemplos y códigos anteriores; prioridad de rechazos; ausencia de consultas de arista antes de validar el dominio; costo cero equivalente a certificación dentro del dominio; invariancia ante rotación, inversión y renombrado consistente; no modificación de entradas; y concordancia del cálculo completo con cualquier optimización incremental.

Los certificados de las nueve instancias seleccionadas en [#16](dataset-selection.md) pueden servir como comprobación de costo cero, siempre separados de las entradas de los solvers. Su aceptación comprueba factibilidad y coherencia de evaluación; no mide capacidad de búsqueda.

## Estado de entrega y consecuencias para #19

La dependencia #17 está satisfecha. Esta propuesta aporta a #19: costo entero con sentido de minimización, objetivo cero sujeto a validación, evaluación rechazada sin valor numérico y separación entre mejor candidato y ciclo certificado. No establece el esquema del resultado ni los presupuestos de ejecución, y #19 no es un bloqueo adicional para #18.

La propuesta se presenta para revisión del responsable y del equipo mediante una PR vinculada. El issue #18 permanece abierto hasta aceptar e integrar la entrega. Las comprobaciones de preparación se registran en esa PR; no se presentan como pruebas ejecutables del proyecto ni como resultados de benchmarking.

## Base documental

- [Contrato aceptado #17: operaciones, legalidad, tipos y certificación](graph-and-route-contracts.md), integrado mediante PR #22.
- [Investigación #5: alternativas, ejemplos, escala y límites](../research/evolution-and-fitness.md).
- [Investigación #3: dominio, índices, representación y validación](../research/search-space.md).
- [Investigación #2: uso de la evaluación por las seis metaheurísticas](../research/metaheuristics.md).
- [Investigación #6: separación entre costo y métricas de ejecución](../research/evaluation-metrics.md).

Las fuentes académicas y sus evidencias se conservan en esos entregables y en la [bibliografía compartida](../research/references.bib). La justificación de esta propuesta es una elección de diseño para discusión, no un resultado atribuido a esas publicaciones.

## Adaptación a Python del evaluador (#37)

`evaluate_cost(graph, route)`, importable desde `src.evaluation`, devuelve un `int` de Python entre 0 y n para una ruta legal en un grafo con n >= 3. Recalcula las n conexiones mediante `has_edge`, incluido el cierre implícito, sin caché, reparación ni llamadas a `validate_cycle`. No modifica las entradas ni registra presupuestos o contadores; esos controles corresponden al solver.

Una entrada fuera del dominio levanta `CostEvaluationError(ValueError)`, también exportado desde `src.evaluation`. La excepción expone `code`, `position` y `vertices`, sin valor de costo: `graph_too_small` tiene posición `None` y vértices `()`; los rechazos de legalidad conservan exactamente el contexto de `check_route_legality`. Se eligió una excepción para mantener el retorno numérico de las evaluaciones completadas y evitar que un rechazo se compare como aptitud. El consumidor debe conservar este diagnóstico y aplicar los estados del #19, sin convertirlo en infinito ni continuar como si hubiera evaluado una ruta legal.

Se aceptan los mismos tipos de ruta e índices que en el núcleo #26, incluidos enteros NumPy. Los contenedores sin posiciones producen `TypeError` cuando n >= 3; el rechazo de grafo pequeño siempre tiene prioridad. Un error de `has_edge` se propaga como discrepancia de implementación, no como conexión ausente. Las pruebas y sus comandos están en [README](../../README.md#costo-de-búsqueda).

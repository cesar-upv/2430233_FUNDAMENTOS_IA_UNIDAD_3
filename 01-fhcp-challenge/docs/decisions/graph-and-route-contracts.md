# Contratos de grafo y ruta

**Estado:** propuesta en revisión para el [issue #17](https://github.com/ZapataFrame/FHCP-Challenge/issues/17) (M2); vigente al integrarse en `main`.
**Responsable:** César Euresti · @cesar-upv.

## Contexto y decisión

Este documento resuelve las preguntas sobre grafo, índices, cierre y simetrías que dejó abiertas la [investigación de representación](../research/search-space.md#7-síntesis-para-m2-y-preguntas-abiertas), a partir de la [teoría de grafos](../research/graph-theory.md) y de los [formatos FHCP](../research/fhcp-challenge.md#3-formatos-publicados-e-identificadores). El stack sigue pendiente en [#15](https://github.com/ZapataFrame/FHCP-Challenge/issues/15), así que aquí se fija la semántica en notación neutral: M3 adapta nombres y tipos al lenguaje elegido, sin cambiar comportamiento, dominios ni códigos de error. No se implementan parser ni validador, ni se definen fitness (#18) o interfaz del solver (#19).

Se decide:

1. **Grafo:** finito, simple, no dirigido y sin pesos; inmutable durante la búsqueda y almacenado como listas de vecinos ordenadas en CSR.
2. **Índices:** enteros `0..n-1`, separados de las etiquetas externas por un mapeo reversible con etiquetas en orden ascendente.
3. **Ruta:** exactamente `n` índices con cierre implícito; la forma con el origen repetido al final se rechaza.
4. **Entradas:** perfil cerrado del FHCP; todo lo demás se rechaza con un código y sin grafo parcial.
5. **Certificación:** un validador que solo recibe grafo y ruta, independiente del fitness y del solver.

## Perfil medido del dataset

Se inspeccionaron los 1001 grafos y los 1001 tours de `data/raw/`. Son datos observados, no resultados de un solver. Un rasgo observado no se convierte automáticamente en requisito: la última columna indica cuáles se exigen.

| Rasgo | Observado en los 1001 pares | Tratamiento en el contrato |
| --- | --- | --- |
| Tamaño | `n` de 66 a 9528 (mediana 2916); `m` de 99 a 315 283 (mediana 5311). | Enteros de 32 bits bastan para esta colección (`2m` máximo: 630 566). |
| Encabezado HCP | `NAME`, `COMMENT`, `TYPE : HCP`, `DIMENSION`, `EDGE_DATA_FORMAT : EDGE_LIST`. | Exigido, salvo `NAME` y `COMMENT`, que son opcionales. |
| Encabezado TOUR | `NAME`, `COMMENT` (vacío en todos), `TYPE : TOUR`, `DIMENSION`; un solo tour con `n` posiciones, un valor por línea. | Exigido, salvo `NAME` y `COMMENT`. |
| Terminación | `-1` y `EOF`; finales de línea CRLF y salto final. | `-1` y `EOF` exigidos; se admiten CRLF y LF. |
| Etiquetas | Exactamente `1..n`; todas aparecen en alguna arista. | El universo `1..n` es exigido; que todas aparezcan, no. |
| Aristas | Una por línea, con `u < v`; sin bucles ni duplicados en ningún sentido. | Sin bucles ni duplicados exigido; el orden de los extremos, no. |
| Estructura | Conexos, grado mínimo 2, grado máximo 1908 (`graph690`), densidad máxima ≈ 0.50. | No exigido: los grafos no hamiltonianos de prueba también deben cargarse. |

TSPLIB no alcanza para fijar este perfil. Permite `ADJ_LIST` y colecciones de tours, y hace opcional `EOF` ([manual, §§1.1.7, 1.1.11, 1.2.4 y 1.2.7](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tsp95.pdf)). También exige un `-1` adicional al terminar la sección de tours, que ningún archivo FHCP contiene; por eso el perfil admitido es el del FHCP y no el de TSPLIB completo.

## Contrato del grafo

**Supuestos.** $G=(V,E)$ es finito, simple y no dirigido, con $n=|V|\ge1$ y $m=|E|$. Una arista es un par no ordenado de vértices distintos, sin peso. El grafo no se completa ni se repara. No se exige conexidad, grado mínimo ni hamiltonicidad: un grafo con vértices aislados o sin aristas es válido, y el validador se encarga de rechazar sus rutas.

**Estructura.** El grafo es inmutable tras construirse y se comparte entre los candidatos, sin copiarlo por individuo. Contiene:

| Campo | Contenido | Invariante |
| --- | --- | --- |
| `external_labels` | `n` etiquetas enteras. | Estrictamente ascendentes. |
| `offsets` | `n+1` posiciones. | `offsets[0] = 0`, `offsets[n] = 2m` y no decreciente. |
| `adjacency` | `2m` índices; la fila `u` es `adjacency[offsets[u] .. offsets[u+1])`. | Cada fila es estrictamente ascendente, no contiene a `u`, y `v` está en la fila `u` si y solo si `u` está en la fila `v`. |
| `source` | Identificador de instancia y SHA-256, más `NAME` y `COMMENT` como texto descriptivo; vacío si el grafo se construye en memoria. | No interviene en la adyacencia. |

Los campos son internos: solvers y validador usan únicamente estas operaciones. Las cotas son analíticas.

| Operación | Contrato | Costo |
| --- | --- | --- |
| `vertex_count()` / `edge_count()` | `n` y `m`. | $O(1)$ |
| `degree(u)` | Número de vecinos de `u`. | $O(1)$ |
| `neighbors(u)` | Vista de solo lectura, en orden ascendente. | $O(1)$ más $O(d(u))$ al recorrerla |
| `has_edge(u, v)` | Simétrica; `false` si `u = v`. Busca en la fila más corta de las dos. | $O(\log(1+\min(d(u),d(v))))$ |
| `edges()` | Cada arista una vez, como `(u, v)` con `u < v`, en orden lexicográfico. | $O(n+m)$ |
| `external_label(i)` | Etiqueta de `i`. | $O(1)$ |
| `index_of(label)` | Índice de `label`, o error `unknown_label`. | $O(\log n)$ |

Un índice fuera de `0..n-1` en estas operaciones es un error de programación: se señala como `invalid_vertex_index` y nunca devuelve `false` ni una lista vacía. Si el stack necesita una variante sin esa comprobación por rendimiento, debe ser privada de `src/graphs` y justificarse con una medición.

### Ejemplo

Es el grafo del [§4.1 de la investigación](../research/search-space.md#41-ejemplo-de-codificación-y-decodificación), conceptual y ajeno al FHCP, con etiquetas no consecutivas para que falle cualquier atajo `etiqueta = índice + 1`:

```text
external_labels = [10, 20, 30, 40, 50]
external_edges  = (10,20) (20,30) (30,40) (40,50) (10,50) (10,30) (20,40)

offsets   = [0, 3, 6, 9, 12, 14]
adjacency = [1,2,4,  0,2,3,  0,1,3,  1,2,4,  0,3]

has_edge(0, 4) = true       has_edge(4, 0) = true
has_edge(2, 4) = false      has_edge(2, 2) = false
neighbors(4)   = [0, 3]     degree(4)      = 2
index_of(30)   = 2          index_of(60)   → unknown_label
```

## Índices y mapeo reversible

Un **índice** es un entero de `0..n-1` y es lo único que manejan rutas, solvers y validador. Una **etiqueta** es el identificador de la instancia original y solo aparece al cargar o exportar.

- El índice `i` corresponde a la `i`-ésima etiqueta en orden ascendente. Se cumple `index_of(external_label(i)) = i`, y no depende del orden de las aristas en el archivo ni de la iteración de una tabla hash.
- Una instancia HCP no enumera sus vértices, así que el lector toma como universo `1..DIMENSION`. Eso incluye a los vértices sin aristas, que no se omiten ni se renumeran. La regla sigue lo observado en los 1001 grafos; el manual de TSPLIB no la fija expresamente para HCP.
- El mapeo se usa siempre mediante `external_label` e `index_of`, aunque en el FHCP equivalga a `i + 1`. Como se deriva de `DIMENSION`, no se guarda aparte en `data/processed/`.
- `route_to_external(graph, route)` y `route_to_internal(graph, labels)` convierten posición por posición, sin ordenar, deduplicar ni cerrar. `route_to_internal` falla con `unknown_label` o `invalid_label_type`. Los errores de longitud o repetición se dejan al validador, que los informa con su código.

## Contrato de la ruta

Una **ruta** es una secuencia de exactamente `n` índices `(p_0, ..., p_{n-1})`. El cierre es implícito: el último par es `(p_{n-1}, p_0)`, y por eso una ruta de `n` posiciones comprueba `n` aristas. Es el formato común de intercambio; los estados internos, como claves reales o secuencias de intercambios, son libres si se convierten a él antes de evaluar o validar.

| Nivel | Condición | Quién lo garantiza |
| --- | --- | --- |
| Candidato | Cualquier secuencia sin comprobar, incluidos prefijos o datos corruptos. | Nadie. |
| Ruta legal | Longitud `n`, índices enteros de `0..n-1` y sin repetidos. | Operadores y decodificadores, comprobado con `check_route_legality`. |
| Ciclo certificado | Ruta legal cuyas `n` aristas, incluido el cierre, existen en el grafo, con $n\ge3$. | Solo `validate_cycle`. |

Una lista de `n+1` posiciones con el origen repetido no se normaliza y se rechaza. Un prefijo no es una ruta. Un adaptador futuro podría aceptar otra convención, siempre declarada y anterior al validador.

**Simetrías.** Rotar o invertir una ruta representa el mismo ciclo, y las dos formas son válidas o inválidas por igual. `canonical_route(route)` se define solo para rutas legales: rota hasta dejar el índice `0` al inicio. Para `n = 1` o `n = 2` devuelve esa secuencia rotada, sin comparar segundos elementos: `[0] → [0]`, `[0,1] → [0,1]` y `[1,0] → [0,1]`. Para `n >= 3` conserva el sentido cuyo segundo elemento sea menor. Por ejemplo, `[3,4,0,1,2]` y `[0,4,3,2,1]` producen `[0,1,2,3,4]`. Se usa únicamente para registrar y detectar duplicados; **no durante la búsqueda**, porque alterar posiciones podría interferir con el estado de un operador o una partícula. Los certificados se comprueban por factibilidad, nunca por igualdad con el tour oficial.

### Ejemplo de conversión

```text
labels  = [30, 40, 50, 10, 20]        tour externo, cierre 20–30
route   = route_to_internal(...)      → [2, 3, 4, 0, 1]
validate_cycle(graph, route)          → válido
canonical_route(route)                → [0, 1, 2, 3, 4]
route_to_external(graph, route)       → [30, 40, 50, 10, 20]

route_to_internal(graph, [10,20,30,40,60])  → unknown_label
```

## Entradas admitidas e inválidas

Los lectores aceptan un perfil cerrado, procesan la entrada en orden y se detienen en el primer error. Devuelven `{code, line, detail}` y ningún grafo o tour parcial. No hay reparación silenciosa: bucles y duplicados no se descartan, y las aristas ausentes no se completan. Las líneas del encabezado se revisan una a una; al terminar este, se comprueba en el orden de la tabla: palabras clave ausentes, sección, tipo, formato y dimensión.

**Perfil común.** Texto ASCII con líneas terminadas en CRLF o LF; el salto final es opcional. Cada línea de encabezado tiene la forma `KEYWORD : value`, con espacios opcionales alrededor de `:`; las palabras clave distinguen mayúsculas, no pueden repetirse y pueden ir en cualquier orden antes de la sección de datos. `NAME` y `COMMENT` son opcionales y pueden estar vacíos. Las etiquetas son enteros decimales positivos, sin signo ni ceros a la izquierda. La sección termina con `-1`, seguido de `EOF`, y después solo puede haber líneas en blanco.

**Instancia (`read_hcp`).** Palabras clave: `NAME`, `COMMENT`, `TYPE : HCP`, `DIMENSION`, `EDGE_DATA_FORMAT : EDGE_LIST`, seguidas de `EDGE_DATA_SECTION`. Cada línea de datos contiene dos etiquetas, separadas por espacios o tabuladores, en cualquier orden. `DIMENSION` es un entero de al menos 1. Una sección sin aristas es válida.

**Certificado (`read_tour`).** Palabras clave: `NAME`, `COMMENT`, `TYPE : TOUR`, `DIMENSION`, seguidas de `TOUR_SECTION`. Cada línea de datos contiene una etiqueta. Recibe el grafo correspondiente y exige que `DIMENSION` coincida con su `n`. Devuelve las etiquetas tal cual. El consumidor aplica explícitamente `read_tour → route_to_internal → validate_cycle`; nunca pasa etiquetas externas directamente al validador. `route_to_internal` rechaza las etiquetas fuera del universo con `unknown_label`; tras convertirlas, la longitud y las repeticiones las juzga el validador.

Sobre un triángulo con etiquetas externas `[1,2,3]`, el lector devuelve el tour `[1,2,3]`, la conversión produce `[0,1,2]` y el validador lo acepta. Si el lector devuelve `[1,2,4]`, la conversión falla con `unknown_label` y no se llama al validador. Este flujo no certifica una ruta solo por haberla leído o convertido.

Ejemplos sobre el triángulo sintético de la [investigación de formatos](../research/fhcp-challenge.md#3-formatos-publicados-e-identificadores), con `DIMENSION : 3`:

| Entrada inválida | Código |
| --- | --- |
| Bytes no ASCII, por ejemplo `NAME : gráfica`. | `invalid_encoding` |
| Línea de encabezado sin `:` o línea en blanco antes de la sección. | `malformed_header` |
| Palabra clave ajena al perfil, por ejemplo `CAPACITY : 5`. | `unknown_keyword` |
| `NAME` dos veces. | `repeated_keyword` |
| Falta `TYPE`, `DIMENSION` o `EDGE_DATA_FORMAT`. | `missing_keyword` |
| El archivo termina sin `EDGE_DATA_SECTION` o `TOUR_SECTION`. | `missing_section` |
| `TYPE : TSP`, o `TYPE : TOUR` en `read_hcp`. | `unsupported_type` |
| `EDGE_DATA_FORMAT : ADJ_LIST`. | `unsupported_edge_format` |
| `DIMENSION : 0`, `-3` o `3.0`. | `invalid_dimension` |
| `1 2 3`, `1 x`, `01 2` o una línea en blanco dentro de la sección. | `malformed_edge_line` |
| `1 4`: etiqueta fuera de `1..3`. | `unknown_label` |
| `2 2`: bucle. | `self_loop` |
| `1 2` y después `1 2` o `2 1`: la misma arista no dirigida. | `duplicate_edge` |
| El archivo termina sin `-1`. | `missing_terminator` |
| El archivo termina tras `-1` sin `EOF`. | `missing_eof` |
| Contenido tras `EOF`, o cualquier otra línea entre `-1` y `EOF`, como un segundo `-1`. | `trailing_content` |
| `read_tour`: `DIMENSION : 4` para un grafo con `n = 3`. | `dimension_mismatch` |
| `read_tour`: `1 2` en una línea o `x`. | `malformed_tour_line` |

Construir un grafo en memoria exige etiquetas enteras estrictamente ascendentes y no vacías (`invalid_labels` en otro caso), sin la restricción `1..DIMENSION` del lector HCP, y aplica `unknown_label`, `self_loop` y `duplicate_edge` para las aristas.

**Instancias del manifiesto.** Para las instancias de [`fhcp-instances.json`](fhcp-instances.json), el SHA-256 del archivo se comprueba antes de leerlo (`source_hash_mismatch`), y `dimension` y `edge_count` se comparan después (`manifest_mismatch`). Una instancia se identifica por su ID del manifiesto y su hash, no por `NAME`. La correspondencia con su certificado la da también el manifiesto. Los certificados de `data/raw/FHCPCS_sols/` se leen solo para comprobar, nunca como entrada del solver.

## Validador independiente

`validate_cycle(graph, route)` recibe únicamente el grafo y la ruta. No consulta fitness, estado del solver ni certificados; no confía en ninguna marca previa, no normaliza y no modifica la ruta. Un rechazo es un resultado normal, no una excepción: devuelve `{valid, reason, position, vertices}`. En el pseudocódigo, `reject` termina la validación completa con ese resultado.

```text
check_route_legality(n, route):
    if length(route) != n: reject("invalid_length")
    seen = array(n, false)
    for position, vertex in route:
        if not is_integer(vertex): reject("invalid_vertex_type", position)
        if vertex < 0 or vertex >= n: reject("unknown_vertex", position, vertex)
        if seen[vertex]: reject("repeated_vertex", position, vertex)
        seen[vertex] = true
    accept()

validate_cycle(graph, route):
    n = graph.vertex_count()
    if n < 3: reject("graph_too_small")
    check_route_legality(n, route)
    for i in 0 .. n-2:
        if not graph.has_edge(route[i], route[i+1]):
            reject("missing_edge", i, (route[i], route[i+1]))
    if not graph.has_edge(route[n-1], route[0]):
        reject("missing_closing_edge", n-1, (route[n-1], route[0]))
    accept()
```

| Comprobación | Cómo se cubre | Código de rechazo |
| --- | --- | --- |
| Tamaño mínimo | $n\ge3$; bajo la [definición de ciclo simple](../research/graph-theory.md#2-definiciones-y-notación) no hay ciclo con menos vértices. | `graph_too_small` |
| Longitud | Exactamente `n`; descarta prefijos y el origen repetido. | `invalid_length` |
| Tipo | Solo enteros, sin conversión implícita: booleanos, reales (incluso `1.0`) y cadenas se rechazan. | `invalid_vertex_type` |
| Dominio | Cada índice en `0..n-1`. | `unknown_vertex` |
| Unicidad | Marcas por índice. | `repeated_vertex` |
| Cobertura | Se deduce: `n` valores distintos dentro de un dominio de `n` deben cubrirlo entero. Por eso falta un vértice solo si antes falla la longitud o la unicidad, y no necesita código propio. | — |
| Aristas internas | Los `n-1` pares consecutivos. | `missing_edge` |
| Cierre | El par `(p_{n-1}, p_0)`, informado aparte para distinguir un camino hamiltoniano de un ciclo. | `missing_closing_edge` |

El orden es determinista: se informa el primer fallo según la secuencia anterior y, dentro de cada recorrido, la primera posición. La memoria auxiliar es $O(n)$ y el tiempo, $O(n)$ más `n` llamadas a `has_edge`. Agotar un presupuesto o rechazar una ruta no dice nada sobre la existencia de un ciclo en el grafo.

### Casos que M3 debe cubrir

Sobre el grafo del ejemplo:

| Ruta | Resultado | Razón |
| --- | --- | --- |
| `[0,1,2,3,4]` | Válida | Están las cuatro aristas internas y el cierre `4–0`. |
| `[0,4,3,2,1]` | Válida | Es el mismo ciclo en sentido inverso. |
| `[2,3,4,0,1]` | Válida | Es el mismo ciclo rotado. |
| `[0,1,3,1,2]` | `repeated_vertex`, posición 3 | Todos sus pares existen, pero repite 1 y omite 4. |
| `[0,1,3,4]` | `invalid_length` | Falta 2. |
| `[0,1,2,3,4,0]` | `invalid_length` | Cierre explícito. |
| `[0,1,2,3,5]` | `unknown_vertex`, posición 4 | 5 está fuera del dominio. |
| `[0,1,2,3,1.0]` | `invalid_vertex_type`, posición 4 | Un real no es un índice. |
| `[0,1,3,2,4]` | `missing_edge`, posición 3 | Es una permutación con cierre válido, pero falta `2–4`. |
| `[1,0,2,3,4]` | `missing_closing_edge`, posición 4 | Es un camino hamiltoniano sin arista `4–1`. |

Otros grafos:

| Grafo | Ruta | Resultado |
| --- | --- | --- |
| Camino `0–1–2–3–4`, no hamiltoniano ([§4.2 de la teoría](../research/graph-theory.md#42-un-grafo-sin-ciclo-hamiltoniano-y-una-prueba-de-inexistencia)). | `[0,1,2,3,4]` | `missing_closing_edge` |
| Dos vértices y una arista. | `[0,1]` | `graph_too_small` |
| Triángulo. | `[0,2,1]` | Válida: es el caso mínimo, con tres aristas distintas. |

Además, M3 debe comprobar:

- **Lectores:** cada fila de la tabla de entradas inválidas, ambos finales de línea, y que un vértice aislado se conserve.
- **Grafo:** que `has_edge` y `edges()` coincidan con los pares del archivo y que reordenar o invertir las aristas produzca el mismo grafo.
- **Mapeo:** un grafo con etiquetas no consecutivas, para detectar el atajo `i + 1`; comprobar también el flujo completo de tour del triángulo anterior y el rechazo de `[1,2,4]` en la conversión.
- **Canonicalización:** comprobar `[0] → [0]`, `[0,1] → [0,1]` y `[1,0] → [0,1]`. Son rutas legales, pero `validate_cycle` debe rechazarlas con `graph_too_small`; canonicalizar no certifica ciclos.
- **Dataset:** los 18 archivos seleccionados en [`dataset-selection.md`](dataset-selection.md), comparados con el manifiesto, con los nueve certificados oficiales aceptados por el validador.

## Alternativas descartadas

| Decisión | Alternativa | Motivo |
| --- | --- | --- |
| Estructura | Lista de aristas | Adecuada como formato de entrada; $O(m)$ por consulta. |
| Estructura | Conjuntos hash de vecinos | Su costo es $O(1)$ solo esperado, con sobrecarga, y exigen ordenar aparte para ser deterministas. |
| Estructura | Matriz de bits o de bytes | Consulta $O(1)$, pero `neighbors` cuesta $O(n)$, justo lo que necesita una construcción tipo ACO, y su memoria crece con $n^2$ (ver abajo). |
| Índices | Usar las etiquetas `1..n` como índices | Evita el mapeo, pero mezcla ambos dominios y los errores por uno pasan inadvertidos. |
| Orden de etiquetas | Orden de aparición en el archivo | Haría depender los índices del orden de las aristas. |
| Ruta | Vector de sucesores, código ordinal o claves | Sirven como estado interno, pero exigen decodificar, y los sucesores admiten subciclos disjuntos. |
| Cierre | Explícito con `n+1` posiciones | Tiene repetición redundante y permite aceptar dos convenciones por accidente. |
| Simetrías | Normalizar durante la búsqueda | Podría interferir con el estado de los operadores. |
| Duplicados | Eliminarlos o admitir multigrafos | Ocultaría un archivo corrupto; ningún grafo del conjunto los necesita. |
| Formato | TSPLIB completo | Añade rutas de código sin uso, como `ADJ_LIST` o varios tours, sin ningún archivo que las requiera. |
| `n < 3` | Rechazarlo al cargar | Dejaría sin efecto `graph_too_small`; tener pocos vértices es una propiedad del ciclo, no un archivo inválido. |

Costos calculados, no medidos, con índices de 32 bits y filas de bits en palabras de 64. Excluyen la sobrecarga del lenguaje. La columna de comparaciones es la cota de búsqueda binaria en la fila de mayor grado.

| Instancia | `n` | `m` | Grado máx. | CSR (bytes) | Matriz de bits (bytes) | Comparaciones máx. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `graph268` (seleccionada) | 1644 | 2767 | 192 | 28 716 | 341 952 | 8 |
| `graph479` (seleccionada) | 2772 | 4536 | 5 | 47 380 | 975 744 | 3 |
| `graph1001` (seleccionada, mayor `n`) | 9528 | 13 968 | 3 | 149 860 | 11 357 376 | 2 |
| `graph188` (mayor `m`) | 1123 | 315 283 | 1122 | 2 526 760 | 161 712 | 11 |

CSR es más compacto en 979 de los 1001 grafos, y su peor caso (2.5 MB) es menor que el de la matriz de bits (11.4 MB). La matriz ocupa menos en los 22 restantes, entre los que están los densos como `graph188`, donde CSR requiere 15.6 veces su memoria. Esta elección favorece a la selección de #16, que es dispersa, y no se ha comprobado con tiempos reales. Si un perfilado posterior muestra que `has_edge` limita la búsqueda, se puede añadir un índice interno sin alterar este contrato.

## Consecuencias

- **#15 (stack):** debe ofrecer enteros de al menos 32 bits y una forma de exponer el grafo como solo lectura. Los nombres pueden seguir el estilo del lenguaje, pero los códigos de rechazo se conservan literalmente, porque formarán parte de la evidencia. Si los tipos estáticos impiden un índice no entero, `invalid_vertex_type` se comprueba solo en la frontera con datos externos.
- **#18 (fitness):** su dominio es la ruta legal; debe usar `has_edge` y contar el cierre. Una ruta con fitness óptimo no se declara ciclo sin `validate_cycle`.
- **#19 (solver y resultado):** el solver recibe el grafo sin certificados y devuelve rutas en índices internos, que se convierten a etiquetas solo al exportar. Los prefijos y construcciones bloqueadas no son rutas. Los códigos de rechazo y `canonical_route` están disponibles para sus resultados; este documento no fija esos estados.
- **M3:** implementa grafo y lectores en `src/graphs`, y validador en `src/evaluation`, con los casos anteriores. Los algoritmos usan el grafo, pero no leen certificados ni dependen de la CLI.
- **M5:** las operaciones que recorren vecinos resultan baratas; las consultas de arista cuestan como máximo la búsqueda binaria indicada. Las metaheurísticas con estado continuo deben declarar su conversión a ruta.
- **Costos aceptados:** el mapeo añade una indirección que en el FHCP parece trivial; `has_edge` no es $O(1)$; y el perfil rechaza archivos válidos en TSPLIB, como los que omiten `EOF`.
- **Cambios futuros:** ampliar el perfil de entrada o cambiar la convención de ruta requiere revisar esta decisión, no una tolerancia añadida en el código.

## Comprobaciones

- **Perfil del dataset:** se leyeron los 1001 pares de `data/raw/FHCPCS/` y `data/raw/FHCPCS_sols/` con una inspección puntual, que no forma parte del repositorio. Los 1001 certificados oficiales cubren sus vértices y usan aristas existentes, incluido el cierre.
- **Coherencia del contrato:** se escribió una implementación desechable fuera del repositorio siguiendo este documento. Con ella se comprobaron los ejemplos, cada fila de las tablas de entradas inválidas y de rutas, y la carga y validación de los 1001 pares. No sustituye al parser, al validador ni a las pruebas de M3.
- **Límites:** los costos son analíticos y no se midieron tiempos porque el stack no está decidido. El perfil describe este conjunto de archivos y no otros formatos ni versiones del dataset.

## Adaptación a Python del núcleo (#26)

Con el [stack del #15](stack-and-tooling.md) ya integrado, el [issue #26](https://github.com/ZapataFrame/FHCP-Challenge/issues/26) implementa este contrato en `src/graphs/graph.py` y `src/graphs/routes.py`. Se importa desde `src.graphs`, ejecutando Python desde la raíz del checkout. Esta adaptación conserva la semántica de M2; los lectores (#27), la certificación (#28) y la procedencia verificada (#29) siguen en sus entregas.

| API pública | Adaptación |
| --- | --- |
| `Graph(external_labels, external_edges, *, source=None)` | Recibe iterables de etiquetas enteras estrictamente ascendentes y pares de etiquetas externas. No ordena las etiquetas ni elimina aristas inválidas. Acepta grafos sin aristas y de uno o dos vértices. |
| Operaciones del grafo | Conservan los nombres y costos descritos arriba. `edges()` devuelve un iterador de pares de enteros de Python; `neighbors(u)` devuelve una vista NumPy unidimensional `int32`, ordenada y de solo lectura. |
| `GraphError(ValueError)` | Expone `code` y `detail`. El universo vacío, desordenado, repetido o con etiquetas no enteras produce `invalid_labels`. Extremos de aristas o consultas de etiqueta con tipos inválidos producen `invalid_label_type`; los demás errores conservan `unknown_label`, `self_loop`, `duplicate_edge` e `invalid_vertex_index`. |
| `route_to_internal(graph, labels)` / `route_to_external(graph, route)` | Devuelven tuplas de enteros, conservando posiciones y repeticiones, incluso en prefijos o rutas con cierre explícito. Cada elemento debe pertenecer al dominio: `route_to_internal` falla con `unknown_label`/`invalid_label_type`; `route_to_external`, con `invalid_vertex_index`. No comprueban legalidad. |
| `check_route_legality(n, route)` | Recibe un tamaño positivo y una secuencia con longitud disponible, como lista, tupla o arreglo NumPy. Devuelve `RouteLegalityResult(valid, reason, position, vertices)` inmutable; `reason` y `position` son `None` y `vertices` es `()` al aceptar. El rechazo conserva el primer fallo de la secuencia acordada. Un contenedor sin posiciones, como un conjunto o diccionario, es un argumento Python inválido (`TypeError`). |
| `canonical_route(route)` | Infiere `n` de la longitud y exige una permutación de `0..n-1` no vacía. Devuelve una tupla; una secuencia ilegal levanta `GraphError` con su razón de legalidad. Un contenedor sin posiciones levanta `TypeError`, igual que en la comprobación de legalidad. No comprueba aristas ni certifica ciclos. |

Se aceptan enteros de Python y escalares enteros de NumPy; se rechazan booleanos de ambos, duraciones NumPy (`timedelta64`), reales y cadenas antes de cualquier conversión. Las etiquetas externas se conservan como enteros de Python y no están limitadas a 32 bits. Los índices y offsets del CSR usan `np.int32`; un tamaño o longitud de adyacencia que exceda su capacidad levanta `OverflowError`, sin truncamiento. Un argumento Python mal formado, como una arista sin exactamente dos extremos, levanta `TypeError` o `ValueError`; no es una línea de archivo y no recibe códigos del lector. Un `n` no entero o menor que uno en la comprobación de legalidad es un error de programación (`ValueError`).

El constructor copia las entradas. El CSR se respalda con bytes inmutables; cada llamada a `neighbors` crea únicamente una cabecera de arreglo sobre esos bytes, sin exponer la cabecera de los arreglos internos. Esto impide habilitar escritura y evita que cambios de forma o tipo en una vista alteren el grafo. `source` es un mapeo de solo lectura, copiado del argumento opcional, con claves y valores de texto; sus claves previstas son `instance_id`, `sha256`, `name` y `comment`. Por defecto está vacío. El núcleo conserva estos textos sin verificar hashes ni leer archivos; esa comprobación pertenece al #29. Metadatos con valores mutables o no textuales se rechazan con `TypeError`.

La legalidad solo comprueba la permutación: un grafo sin aristas puede tener rutas legales. La certificación independiente de aristas y cierre sigue correspondiendo a `validate_cycle` en el #28. Las pruebas del núcleo se repiten con los [comandos del README](../../README.md#núcleo-de-grafos-y-rutas); sus resultados concretos y plataforma se registran en la PR del #26.

## Adaptación a Python de los lectores (#27)

El [issue #27](https://github.com/ZapataFrame/FHCP-Challenge/issues/27) adapta el perfil cerrado anterior en `src/graphs/readers.py`, exportado desde `src.graphs`. Se eligen excepciones estructuradas para mantener el estilo de `GraphError` del núcleo; un archivo rechazado no produce un resultado parcial. Los lectores no verifican manifiestos (#29) ni certifican ciclos (#28).

| API pública | Adaptación |
| --- | --- |
| `read_hcp(file, *, source=None) -> Graph` | Construye mediante el núcleo CSR el universo completo `1..DIMENSION`, incluso sin aristas. Copia `source` con las mismas restricciones de claves y valores de texto del constructor. Los campos `NAME` y `COMMENT` presentes aportan `name` y `comment`, prevaleciendo sobre el argumento, incluso si están vacíos. Los ausentes no añaden claves. No calcula ni verifica hashes ni deriva identidad de `NAME`. |
| `read_tour(file, graph) -> tuple[int, ...]` | Exige dimensión igual al tamaño del grafo. Devuelve etiquetas externas en su orden original, sin revisar longitud, repeticiones ni pertenencia. El consumidor convierte explícitamente mediante `route_to_internal` y certifica después. |
| `ReaderError(GraphError)` | Expone `code`, `line` y `detail` no vacío. Conserva literalmente los códigos del perfil. Los fallos de E/S se propagan como `OSError`; argumentos Python ajenos a la interfaz no se convierten en errores de formato. |

`file` admite `str`, `os.PathLike[str]` o un flujo binario con `readline()`. Una ruta se abre como `rb` y se cierra tanto al aceptar como al rechazar. Un flujo del consumidor permanece abierto; se lee desde su posición actual, sin requerir `seek`. Esto permite al #29 verificar bytes y suministrarlos con `BytesIO`, sin una segunda lectura del archivo original.

La lectura es incremental por líneas, con decodificación ASCII estricta. Se admiten LF y CRLF, incluso combinados, y salto final opcional; un retorno de carro aislado se rechaza con el código de formato de la fase correspondiente. Solo espacios y tabuladores se eliminan en los extremos de cada línea; separan también los extremos de una arista. `DIMENSION` admite dígitos decimales cuyo valor sea positivo. El límite de capacidad CSR de 32 bits se señala como `OverflowError` antes de reservar vértices; se mantienen los límites de conversión de enteros del intérprete.

Las líneas de error son relativas al inicio del flujo y empiezan en 1. Un error léxico se informa al leer su línea, antes de inspeccionar las posteriores. Al terminar el encabezado se comprueban palabras clave obligatorias (en orden `TYPE`, `DIMENSION`, `EDGE_DATA_FORMAT` para HCP), sección, tipo, formato y dimensión. Un valor inválido apunta a su línea de encabezado; un requisito ausente apunta al marcador de sección o a la siguiente línea esperada al agotar el archivo. Un marcador de sección incorrecto produce `missing_section`. En los datos HCP se comprueban sintaxis, dominio, bucle y duplicado, en ese orden. Encontrar `EOF` antes de `-1` produce `missing_terminator`; cualquier línea distinta de `EOF` inmediatamente después de `-1` produce `trailing_content`. Después de `EOF` solo se admiten líneas vacías o con espacios/tabuladores.

Los [comandos del README](../../README.md#lectores-hcp-y-tour) reproducen las pruebas sintéticas de formato y la suite completa. La evidencia de plataforma y resultados se registra en la PR del #27; no acredita la integración de #29–#30 ni pruebas ejecutadas en Windows.

## Carga verificada de la selección FHCP (#29)

`load_fhcp_graph(instance_id, *, root=checkout)` busca un ID único en el manifiesto v1. Lee el miembro HCP indicado bajo `data/raw/FHCPCS/`, no usa `NAME` como identificador y no abre el tour. Comprueba SHA-256 sobre los bytes que entrega a `read_hcp` y coteja después dimensión y número de aristas. El grafo registra `instance_id` y `sha256` en `source`.

`load_fhcp_certificate(graph, *, root=checkout)` comprueba que ID, hash y conteos del grafo coinciden con la entrada seleccionada. Verifica el hash del miembro correspondiente en `data/raw/FHCPCS_sols/` antes de llamar a `read_tour`. Devuelve etiquetas externas sin certificar la ruta. Los miembros deben ser nombres de archivo locales, sin directorios, con extensión `.hcp` o `.hcp.tou` según su función.

Un hash de archivo distinto al declarado devuelve `GraphError` con `source_hash_mismatch`; un manifiesto incompatible, una selección ausente o ambigua, metadatos que no coinciden o un grafo sin procedencia correspondiente devuelven `manifest_mismatch`. Los fallos de E/S y los errores de formato de un archivo cuyo hash coincide se propagan desde la operación correspondiente. Se confía en el manifiesto del checkout para conocer los hashes esperados. `root` permite señalar otro checkout o una copia temporal con la misma estructura. No se modifican ni descargan datos.

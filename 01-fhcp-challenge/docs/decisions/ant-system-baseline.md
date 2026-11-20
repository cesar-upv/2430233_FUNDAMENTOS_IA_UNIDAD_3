# Ant System con penalización de pares ausentes

## Contexto y elección

El [issue #51](https://github.com/ZapataFrame/FHCP-Challenge/issues/51), a cargo de Junior Arturo Vázquez Leonel · @Arturo2430, implementa la [adaptación del #2, §5.5](../research/metaheuristics.md#55-adaptación-propuesta-a-fhcp). Se presenta para revisión como `ant_system_missing_pairs_v1`. Reutiliza el [grafo y ruta del #17](graph-and-route-contracts.md), el [costo del #18](fitness.md) y el [control de ejecución del #19/#39](solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39), integrados en M4.

[Dorigo, Maniezzo y Colorni (1996), §II y algoritmo ant-cycle](https://faculty.washington.edu/paymana/swarm/dorigo96-itsmc.pdf) describen la elección proporcional por feromona/visibilidad y la actualización tras recorridos completos. Aquí `rho` significa **fracción evaporada**, aplicando `(1-rho)*tau`; el artículo original llama rho al factor de persistencia. La visibilidad para pares ausentes, el depósito por costo y las cotas son adaptaciones del proyecto, no resultados experimentales ni una reproducción literal del TSP del artículo.

## API y parámetros efectivos

Se importa desde `src.algorithms`:

```text
AS_VARIANT = "ant_system_missing_pairs_v1"
resolve_as_parameters(parameters) -> dict[str, int | float]
solve_as(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult
```

Todos los parámetros son obligatorios, sin valores ajustados por defecto:

| Campo | Dominio |
| --- | --- |
| `ant_count` | Entero Python ≥ 1. |
| `alpha`, `beta` | Números Python finitos ≥ 0. |
| `rho`, `epsilon` | Números Python estrictamente entre 0 y 1. |
| `q` | Número Python finito y positivo. |
| `initial_pheromone`, `pheromone_min`, `pheromone_max` | Finitos y positivos, con `min <= initial <= max`. |

El resolvedor copia el mapa y normaliza los campos numéricos distintos de `ant_count` a `float` binario64. Rechaza claves no textuales o desconocidas, campos ausentes, booleanos, escalares NumPy, cadenas y valores no finitos o no representables como `float`. Comprueba tipo del mapa, claves de texto, claves desconocidas en orden lexicográfico, presencia y rangos en el orden de la tabla de la API: hormigas, alpha, beta, rho, q, epsilon, inicial, mínimo y máximo; finalmente comprueba las relaciones entre cotas.

`ASConfigurationError(ValueError)` expone `code` y `parameter`, usando `invalid_parameters`, `unknown_parameter`, `missing_parameter` e `invalid_parameter`. El solver convierte el rechazo a `error / invalid_config`, fase `input`, con contadores cero y sin iniciar reloj o RNG. Después `start_run` verifica grafo, semilla y `Budget` con los códigos comunes. No se modifica el esquema de `SolverResult`. La configuración queda copiada y estable durante todo el intento.

## Representación y asignación de memoria

Se almacena un único vector NumPy `float64` con `n*(n-1)//2` entradas. Para `u<v`, el índice es `u*(2*n-u-1)//2 + v-u-1`; invertir los extremos accede a la misma entrada. No existe diagonal. Esta simetría por representación evita escribir dos veces cada depósito no dirigido.

La mayor instancia de la selección, con 9,528 vértices, requeriría 363,093,024 bytes (unos 346 MiB) para ese vector. Es un cálculo, no una asignación ni una medición de rendimiento. Se eligió frente a una matriz completa de unos 693 MiB considerando los aproximadamente 31 GiB de RAM reportados por el equipo de desarrollo. La elección es fija; el algoritmo no consulta RAM disponible ni cambia de representación en cada ejecución.

Se valida el tamaño direccionable antes de `np.empty`. La inicialización rellena el vector en bloques de hasta 65,536 valores. Evaporación y aplicación de cotas reutilizan esas vistas y escriben en sitio. No se crea otra matriz de depósitos ni de visibilidad; el costo adicional de recorridos guardados es `O(ant_count*n)` y los candidatos/pesos temporales usan `O(n)`. Un `MemoryError` durante el estado del solver devuelve `runtime_error / allocation_failed`, con `pheromone_bytes` como tamaño previsto del vector, conservando el histórico. No se intenta agotar memoria real para probarlo.

## Construcción y política numérica

1. Inicializar la feromona positiva en todos los pares distintos; no se construyen ni evalúan candidatos durante esta inicialización.
2. Procesar las hormigas por ordinal. Tras admitir la construcción, elegir el origen con `rng.integers(n)` uniforme. Se permiten orígenes repetidos entre hormigas.
3. Enumerar todos los vértices no visitados por índice ascendente. Para cada candidato usar la operación pública `graph.has_edge`: visibilidad 1 para aristas y `epsilon` para pares ausentes. Estos últimos siguen siendo candidatos; no hay bloqueo, reparación, reinicio ni retroceso.
4. Calcular `score=alpha*log(tau)+beta*log(eta)`, restar el máximo, exponenciar y normalizar con `math.fsum`. Esto evita el desbordamiento/subdesbordamiento del cálculo directo de potencias en casos representables. Se preparan hasta 256 candidatos entre comprobaciones de presupuesto.
5. Elegir con `rng.choice(candidates, p=probabilities)`, incluso si queda un solo candidato. Cada construcción consume un origen y `n-1` elecciones, salvo interrupción. Todos los sorteos usan el PCG64 privado del intento; no se usa estado aleatorio global.
6. Solo una ruta completa pasa a `run.evaluate(route, evaluate_cost)`; se conservan juntos su tupla y costo. Cada solicitud reserva una evaluación, aunque repita una ruta. Un prefijo nunca recibe costo ni aparece en el mejor histórico.

La feromona observada durante construcción debe ser positiva y finita. Se permite subdesbordamiento a cero de probabilidades pequeñas, siempre con suma positiva y distribución finita. Scores o aritmética no finitos producen `non_finite_state`; distribuciones degeneradas producen `runtime_error / invalid_transition_weights`. No hay reparación uniforme silenciosa. Coeficientes finitos muy grandes pueden desbordar incluso el score logarítmico y causar ese error, en vez de cambiar la variante. Los contextos NumPy restauran la política numérica del llamador.

## Actualización de feromonas

La feromona permanece congelada para todas las hormigas de la ronda. Con todos los recorridos completos y evaluados, se exige nueva admisión antes de actualizar; si el presupuesto ya se agotó, no se evapora ni deposita. Se sigue así el pseudocódigo del #2, incluso si la última reserva completó todas las hormigas.

La actualización representa `clip((1-rho)*tau + sum(q/(1+C)), min, max)` por par. Primero se evapora por bloques. Después, en orden de hormiga y posición del recorrido, se deposita en cada par consecutivo y en el cierre. Se refuerzan también pares ausentes del grafo. Cada par se actualiza una sola vez en el vector y queda disponible en ambos sentidos.

Los depósitos son no negativos: se saturan en `pheromone_max` comparando el incremento con el espacio disponible, evitando sumar valores que desbordarían. Esta saturación superior anticipada conserva la actualización acotada. La cota inferior se aplica **después** de todos los depósitos: aplicarla inmediatamente tras evaporar cambiaría el resultado. Los valores transitorios tras evaporar pueden estar bajo el mínimo o redondear a cero; ninguna construcción los consulta. Un depósito extremadamente pequeño también puede redondear a cero.

Se comprueba admisión antes de cada bloque, depósito y cierre de actualización. Si se interrumpe, el intento termina y no se reutiliza la feromona parcialmente actualizada. No se necesita una segunda matriz transaccional. El plazo es cooperativo: una llamada nativa o evaluación puede sobrepasarlo; no se promete timeout duro.

## Fases, contadores y certificación

`iteration_unit` es `round`. La fase `initialization` planifica los bloques de feromona; un elemento terminado significa un bloque rellenado y no incrementa rondas. Cada fase `round` planifica `ant_count+1` elementos: primero los recorridos evaluados y, al final, la actualización completa de feromona. Si `completed_items=ant_count`, la actualización sigue pendiente o parcial. Una ronda cuenta únicamente al terminarla, comprobar el presupuesto y cerrar la fase.

| Contador de algoritmo | Unidad |
| --- | --- |
| `constructions_started` | Construcciones admitidas, antes de sortear el origen. |
| `construction_steps` | Vértices añadidos después del origen; incluye prefijos interrumpidos. |
| `pheromone_updates_started` | Actualizaciones admitidas antes de evaporar. |
| `pheromone_updates_completed` | Actualizaciones terminadas con cotas y última comprobación de admisión. |
| `pheromone_deposits` | Depósitos aplicados por par no dirigido, incluido cierre. |

Las claves ausentes equivalen a cero. Ningún contador adicional consume evaluaciones. Agotar exactamente `ant_count` evaluaciones durante la primera ronda deja `round / ant_count / ant_count+1`, cero rondas y ninguna actualización iniciada. Con presupuesto solo de una iteración, se evalúan `ant_count` recorridos y se termina su actualización sin otra evaluación.

El mejor histórico lo copia `SolverRun` y mantiene el primero ante empate. Tras registrar cada evaluación completada, un costo cero se certifica inmediatamente, incluida la última reserva, dejando la fase abierta. Se preservan éxito dentro del presupuesto, certificación no admitida por tiempo, certificado válido tardío, discrepancia fitness/validador y errores, sin atribuir hamiltonicidad al agotamiento.

## Verificación y alcance

Las pruebas contrastan indexación y actualización con una enumeración/diccionario de pares independiente, probabilidades conocidas, fórmulas de depósito, cotas, secuencia de candidatos, memoria y errores. Reloj y decisiones controlados cubren prefijos, rondas y actualizaciones interrumpidas, última reserva y fronteras de certificación. La reproducción compara trayectoria, ruta, costo y contadores con mismo entorno y presupuesto de evaluaciones, excluyendo tiempos.

Los [comandos del README](../../README.md#ant-system-con-penalización-de-pares-ausentes) reproducen la suite sintética y el ejemplo. La PR registra commit, plataforma y salidas reales. No se han medido tiempos o tasas de éxito sobre FHCP; CLI/RunRecord siguen en #55, integración de M5 en #56 y comparativas en M6.

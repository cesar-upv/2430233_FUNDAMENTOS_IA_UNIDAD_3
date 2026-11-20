# Contrato del solver y de su resultado

## Estado y alcance

**Estado:** propuesta completa para revisión del [issue #19](https://github.com/ZapataFrame/FHCP-Challenge/issues/19), M2, presentada en la [PR #25](https://github.com/ZapataFrame/FHCP-Challenge/pull/25). Responsable: **Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON**. No constituye una API implementada ni una decisión aceptada.

Base de revisión: `main` en `4ef50bb71213b36704d2869cf32e170949fd0cf2`. El contrato de [grafo y ruta](graph-and-route-contracts.md), #17, está integrado mediante PR #22; el [costo de búsqueda](fitness.md), #18, mediante PR #23. El [stack #15](stack-and-tooling.md) está integrado mediante la [PR #24](https://github.com/ZapataFrame/FHCP-Challenge/pull/24), en ese commit de `main`, con comprobación Windows aceptada. Las dos dependencias de cierre del #19 están satisfechas.

La propuesta se cotejó con CPython 3.14.10 estándar de 64 bits, NumPy 2.5.4, venv, pip 26.3 y pytest 9.2.0 del stack aceptado. Mantiene rutas con índices internos y cierre implícito, costo entero minimizado y certificación independiente. El issue #19 permanece abierto hasta revisar e integrar su propia entrega. No se implementan solvers, CLI, lectores ni validadores, ni se eligen repeticiones, semillas experimentales, valores de presupuesto o métodos de agregación de M6.

## Contexto y elección

Las [adaptaciones del #2](../research/metaheuristics.md) utilizan unidades de trabajo distintas y pueden detenerse dentro de una población. La [investigación del #6](../research/evaluation-metrics.md) exige separar costo, certificado, recursos y estado del intento. Esta decisión convierte esos requisitos en un contrato común para una ejecución individual; sus reglas son propuestas de diseño del proyecto.

Se propone una función conceptual, independiente de la CLI:

```text
solve(graph, *, algorithm, parameters, seed, budget) -> SolverResult
```

El coordinador de ejecución agrega procedencia, identidad y entorno al `SolverResult` para formar un `RunRecord`. El solver recibe el grafo ya cargado y comprobado; no recibe rutas a archivos, certificados oficiales, tiempos de referencia ni estadísticas de otros intentos. El coordinador no introduce esos datos mediante parámetros ocultos.

| Entrada | Dominio y obligación |
| --- | --- |
| `graph` | Grafo inmutable del #17, con `n >= 3`. Solo operaciones públicas, CSR compartido y sin modificar etiquetas o adyacencia. `n < 3` produce `error / invalid_input`, con código de detalle `graph_too_small`. |
| `algorithm` | Identificador de familia y variante, más versión de implementación. Debe distinguir GA, SA, ACO, ABC o The Bees Algorithm, DE y PSO. Un nombre genérico de colonia de abejas no identifica una variante. Una variante desconocida se rechaza. |
| `parameters` | Mapa de parámetros efectivos de la variante: inicialización, operadores, selección, empates, actualización y reinicios, cuando apliquen. El registro de cada variante define tipos, rangos y campos obligatorios; rechaza claves desconocidas y valores no finitos. Los valores por defecto se expanden y registran antes de iniciar. Este documento no elige operadores ni valores experimentales. |
| `seed` | Entero de `0` a `2**64-1`, obligatorio. Booleanos, reales, cadenas y `null` se rechazan sin conversión implícita. |
| `budget` | Mapa con `max_elapsed_ns`, `max_evaluations`, `max_iterations`. Cada valor es un entero positivo o `null`; al menos uno debe estar activo. Booleanos y valores cero, negativos, reales o infinitos se rechazan. |

La configuración debe ser una copia estable durante el intento. Entradas o configuración rechazadas producen un resultado de error con contadores cero, sin construir población ni consumir números aleatorios. El coordinador conserva el intento y su diagnóstico; un error no se transforma en agotamiento ni en prueba de inexistencia de ciclo.

## Aleatoriedad y reproducción

Con NumPy 2.5.4 del stack aceptado, se propone un generador privado por ejecución: `numpy.random.Generator(numpy.random.PCG64(seed))`. No se comparte estado global ni se mezcla con `random`, reloj o entropía del sistema. Se registra la semilla decimal, `PCG64`, la versión de NumPy y el orden de actualización de la variante. En la entrada Python la semilla es un entero; al serializar los metadatos se usa la cadena decimal `seed_decimal` para conservar los 64 bits también en consumidores JSON con enteros limitados. El primer alcance es secuencial: `workers = 1`; una variante que requiera paralelismo debe ampliar primero el contrato de recursos y subflujos.

Las iteraciones sobre conjuntos y vecinos deben tener orden definido; los empates de selección o reemplazo son parte de la variante. Para el **registro del mejor histórico**, un costo menor reemplaza al anterior y un empate conserva el primero. La ruta se copia al guardarla, sin referencias mutables a la población. No se canonicalizan rutas durante la búsqueda. Un exportador puede producir una forma canónica aparte, declarando esa transformación.

La documentación de [PCG64](https://numpy.org/doc/stable/reference/random/bit_generators/pcg64.html) describe la inicialización y su flujo entero; la [política de compatibilidad de NumPy](https://numpy.org/doc/stable/reference/random/compatibility.html) restringe la reproducción de `Generator` al mismo entorno, compilación y secuencia de llamadas. Por eso la semilla sola no garantiza trayectorias idénticas entre plataformas o versiones. Un límite temporal también puede cortar en puntos diferentes; la repetición de una trayectoria se comprobará con presupuesto de trabajo e igual entorno, sin prometer idénticos segundos medidos.

## Presupuestos, costo y contadores

El costo registrado es el entero `C` del #18, con minimización y cierre implícito. Se comprueba la legalidad antes de evaluar. Una ruta ilegal es un defecto del productor y produce `error / invalid_candidate`, con el código del #17; no recibe infinito, penalización ni una reparación silenciosa del evaluador. Un prefijo de ACO no es una ruta evaluada y no puede convertirse en el mejor candidato.

Se distinguen estas cantidades, enteras y no negativas:

| Contador | Regla |
| --- | --- |
| `evaluations_started` | Valoraciones de rutas completas admitidas al evaluador; incluye inicialización, reinicios y búsqueda local. Reserva una unidad **antes** de empezar cada valoración y nunca supera `max_evaluations`. |
| `evaluations_completed` | Valoraciones que terminaron con un costo legal. Se cumple `evaluations_completed <= evaluations_started`. Una evaluación interrumpida conserva su reserva. |
| `full_evaluations`, `incremental_evaluations`, `cache_hits` | Partición de las valoraciones completadas; su suma es `evaluations_completed`. La primera implementación usa recálculo completo. Si se introducen caché o incrementales, también consumen una reserva por cada valoración solicitada y se declaran como otra versión de instrumentación. Consultar un costo ya guardado para comparar individuos no es una nueva valoración. |
| `validations_started`, `validations_completed` | Llamadas al validador independiente y llamadas terminadas. No consumen una evaluación de costo, pero sí tiempo. |
| `iterations_completed` | Unidades completas de actualización de la variante, excluida inicialización. No se incrementa por una unidad incompleta. |
| `partial_iteration` | `null` si no hay trabajo parcial. En otro caso `{phase, completed_items, planned_items}`, incluida la fase de inicialización, sin redondear a una iteración completa. En una fase de tamaño variable, `planned_items` puede ser `null`, acompañado por su definición en la variante. |
| `restarts` y `algorithm_counters` | Reinicios ejecutados y trabajo propio: construcciones bloqueadas, propuestas aceptadas, etc. Se identifican nombre, unidad y definición; no se mezclan con evaluaciones completas. |

`max_iterations` se interpreta según esta tabla; registrar `iteration_unit` es obligatorio:

| Familia | Unidad completa |
| --- | --- |
| GA | Generación de descendientes evaluada y reemplazo terminado. |
| SA | Una propuesta de movimiento evaluada y decisión de aceptación terminada. La inicialización no es un movimiento. |
| ACO | Ronda de hormigas terminada y actualización de feromonas terminada; las construcciones bloqueadas se cuentan aparte. |
| ABC | Ciclo de empleadas, observadoras y exploradoras terminado. The Bees Algorithm requiere su propia definición declarada, sin reutilizar esta etiqueta. |
| DE | Generación de vectores de prueba evaluada y reemplazo terminado. |
| PSO | Ronda de partículas actualizadas y evaluadas, con memorias actualizadas. |

Una generación o ronda se puede interrumpir al agotar tiempo o evaluaciones. Si `max_iterations` está activo, antes de empezar la siguiente unidad se comprueba `iterations_completed < max_iterations`. Un límite `null` no se compara con el contador y no produce agotamiento. No se exige completar una población cuando ya no queda presupuesto. La inicialización consume tiempo y evaluaciones y puede acabar en agotamiento con `iterations_completed = 0`. Un ciclo encontrado durante ella puede producir éxito.

Las cantidades de iteraciones de métodos distintos no son equivalentes. Ni una evaluación lógica ni una consulta a la caché garantizan igual trabajo de CPU; los contadores permiten interpretar la ejecución, mientras M6 decidirá las condiciones de comparación.

## Relojes y alcance de tiempos

Se propone [`time.perf_counter_ns()` de Python](https://docs.python.org/3.14/library/time.html#time.perf_counter_ns), con diferencias en nanosegundos y reloj monótono; la fecha UTC es un identificador separado. No se serializa la lectura absoluta del reloj como si fuera una fecha. El contrato distingue:

| Campo | Intervalo |
| --- | --- |
| `preparation_ns` | En el coordinador: lectura, hash, parseo, comprobación del grafo y validación de configuración. Se mide antes de invocar el núcleo. |
| `solver_ns` | Desde inmediatamente antes de crear el RNG y el estado inicial hasta detener el núcleo. Incluye inicialización, copias, decodificación, evaluación, construcción, reparación declarada, reinicios, actualizaciones, comprobaciones de límite y certificación durante la búsqueda. Consume `max_elapsed_ns`. |
| `validation_ns` | Acumulado de validación independiente dentro de `solver_ns`. Es un desglose solapado: **no se suma otra vez** al total. |
| `finalization_ns` | Construcción final del registro y normalización de tipos para JSON, después de parar el núcleo. No permite continuar la búsqueda ni certificar otro candidato. |
| `total_ns` | Desde el inicio de preparación hasta disponer del registro en memoria. Debe ser al menos la suma de las tres fases no solapadas; cualquier intervalo adicional se identifica. Excluye escritura a disco o red. |
| `first_success` | `null` sin éxito dentro del presupuesto. En otro caso guarda `elapsed_ns` desde el inicio del núcleo y una instantánea de evaluaciones e iteraciones al terminar el primer certificado. |

Se incluyen implementación y resolución del reloj en el entorno. La CPU del proceso puede registrarse como medición adicional con alcance explícito; nunca sustituye `solver_ns`. Una cifra en nanosegundos es una unidad de representación, no una promesa de precisión física de un nanosegundo.

El alcance común propuesto para el límite temporal es el núcleo, incluida su inicialización y certificación. M6 elegirá valores y si necesita además un límite externo de extremo a extremo; no podrá llamar equivalentes a límites de distinto alcance. El coordinador debe informar tiempos de carga y total para conservar esa distinción.

## Terminación y certificación

La parada temporal es **cooperativa**. Se comprueba el límite antes de cada evaluación y validación, en cada propuesta o elemento de población y dentro de bucles de construcción/reparación y de las rutinas que permitan interrupción. Se registra el punto de comprobación de la variante. Una llamada nativa no interrumpible puede sobrepasar el límite; al regresar se detiene el trabajo y se informa `overrun_ns = max(0, solver_ns - max_elapsed_ns)`. No se promete una cota dura de sobrepaso.

Orden de decisión:

1. Rechazar entradas/configuración inválidas antes de iniciar. Durante el núcleo, un error de ejecución o de invariantes prevalece sobre un agotamiento simultáneo; se conserva el diagnóstico.
2. Antes de empezar trabajo, comprobar el tiempo y los límites de admisión correspondientes. Una valoración iniciada antes del límite de evaluaciones puede terminar y solicitar certificación incluso si agotó la última reserva. La validación no necesita otra reserva, pero debe empezar antes del límite temporal.
3. Tras obtener un costo, guardar una copia del mejor candidato legal. Si su costo es cero, llamar a `validate_cycle(graph, route)` del #17; el validador no recibe el costo ni confía en él. Si hay tiempo insuficiente para empezar esa llamada, parar por tiempo con certificación pendiente.
4. Si el validador rechaza un costo cero, devolver `error / fitness_validation_mismatch`, conservando su código, posición y vértices. No seguir buscando para ocultar la discrepancia.
5. Aceptar `success` solo si el certificado termina con `valid = true` y `elapsed_ns <= max_elapsed_ns`, cuando hay límite temporal; la evaluación utilizada y la unidad de iteración admitida también deben respetar sus límites. Guardar `first_success` y parar inmediatamente.
6. Si una certificación termina válida después del límite temporal, conservar la ruta y `validation.valid = true`, pero devolver `exhausted / time_limit`, `success_within_budget = false` y `first_success = null`. Una solución tardía no es un éxito dentro del límite.
7. Sin éxito ni error, parar al alcanzar cualquier límite. Si coinciden, usar prioridad `time_limit`, `evaluation_limit`, `iteration_limit` y registrar todos en `limits_reached`. Una regla declarada de la variante puede terminar con `algorithm_stop`; no se inventa una prueba de no hamiltonicidad.

Una parada sin candidato completo devuelve ruta y costo `null`; nunca un prefijo, una ruta rellenada o la última posición arbitraria. Un costo cero sin certificación conserva esa diferencia con `validation.valid = null` y motivo `not_run`. Si se interrumpe una evaluación, sus datos parciales no reemplazan al mejor evaluado.

Una terminación forzada del proceso puede impedir devolver `SolverResult`. El coordinador conserva el registro inicial del intento y, si recupera el fallo, emite `error / external_termination` con los campos desconocidos en `null` y `telemetry_complete = false`. No fabrica ceros, una duración ni un candidato. Un archivo parcial no se trata como un resultado correcto.

## Resultado y registro de ejecución

`SolverResult` tiene `schema_version = "fhcp-solver-result/1"` y los siguientes campos obligatorios. En JSON se usan índices y contadores enteros, `null` para ausencia y ningún `NaN` o infinito. Una ruta se convierte a enteros JSON sin alterar su orden ni aceptar tipos ilegales de entrada.

| Campo | Semántica |
| --- | --- |
| `status`, `stop_reason` | `success / validated_cycle`, `exhausted / {time_limit,evaluation_limit,iteration_limit,algorithm_stop}`, o `error` con motivo explícito. |
| `success_within_budget` | Verdadero únicamente para `status = success`, costo cero y certificado válido terminado dentro de los límites. |
| `best_route`, `best_cost` | Mejor ruta **legal y evaluada** y su costo entero del #18, o ambos `null`. Exactamente `n` índices con cierre implícito. No se devuelve el certificado oficial como solución del solver. |
| `validation` | `{valid, reason, position, vertices}` del #17 para esa misma ruta. `valid = null`, `reason = not_run` si no se ha validado. Un error en otro candidato lleva su contexto en `error`, sin atribuirlo al mejor histórico. |
| `counters` | Contadores anteriores y `iteration_unit`, definidos para la variante. |
| `timing` | `solver_ns`, `validation_ns`, `overrun_ns` y `first_success`; el coordinador agrega preparación, finalización y total. Sin límite temporal, `overrun_ns = null`. |
| `limits_reached` | Lista de límites alcanzados al parar. Llegar a la última evaluación permitida puede coexistir con éxito validado; la lista por sí sola no decide el estado. |
| `error` | `null` salvo error. En error: `{code, message, phase, detail}`; conservar códigos de dominio y diagnóstico, sin incluir credenciales ni datos ajenos a la ejecución. |
| `telemetry_complete` | Verdadero si se recuperó el resultado completo. En interrupción externa, campos desconocidos en `null` con su causa dentro de `error.detail`. |

La combinación `best_cost = 0` y `validation.valid = true` acredita factibilidad, pero no sustituye `success_within_budget`. En resultados normales, cada ruta/costo existe junto con el otro; una ruta ilegal no cabe en `best_route`. Si se conserva un mejor histórico tras un error posterior, `status` continúa siendo `error`.

Para `status = error`, `stop_reason` usa este vocabulario cerrado; el código específico y el contexto van en `error`:

| `stop_reason` | Situación |
| --- | --- |
| `invalid_input` | Grafo fuera del dominio o entrada de solver inválida; por ejemplo, `error.code = graph_too_small`. |
| `invalid_config` | Variante desconocida, semilla inválida, parámetro o presupuesto rechazado antes de iniciar. |
| `invalid_candidate` | El productor entrega una ruta ilegal; propagar el código de legalidad del #17. |
| `non_finite_state` | Claves, velocidades u otro estado numérico no finito antes de decodificar. |
| `fitness_validation_mismatch` | Costo cero rechazado por el validador independiente. |
| `runtime_error` | Otro fallo de ejecución, con tipo y fase recuperables. |
| `external_termination` | El supervisor recupera una terminación forzada sin resultado completo. |

El coordinador serializa el resultado dentro de un `RunRecord` con esta estructura. Es una descripción de campos, no código ejecutable:

```text
RunRecord = {
  schema_version: "fhcp-run-record/1",
  run, instance, procedure, randomness, budget,
  code, environment, timing, artifacts, missing_metadata,
  result: SolverResult
}
```

Todos los grupos están presentes. `missing_metadata` es una lista de objetos `{field, reason}`, con la ruta del campo y la causa de ausencia. Si un dato no se pudo recuperar, su valor es `null` y se añade esa explicación; no se inventan valores. Una lista vacía indica que se recuperaron los metadatos requeridos. Esto es distinto de `result.telemetry_complete`, que informa si se recuperaron los datos del núcleo.

| Grupo | Campos requeridos |
| --- | --- |
| `run` | `run_id`: cadena única; `started_at_utc`: fecha ISO 8601 con zona UTC; `retry_of`: ID del intento anterior o `null`; `batch_id`: ID de lote o `null` hasta definir M6. Un valor `null` no aplicable en `retry_of`/`batch_id` no es metadato perdido. |
| `instance` | `id`, `source_kind` (`fhcp` o `synthetic`), `sha256`, `source_path`, `manifest_revision`, `n`, `m`, `transformations` y `mapping`. Hash de los bytes originales; rutas relativas al proyecto. Para grafos en memoria: construcción serializada identificable y su hash, sin atribuirles un ID FHCP; `manifest_revision = null` si no aplica. `mapping` identifica índices internos y la regla reversible de etiquetas del #17. |
| `procedure` | `family`, `variant`, `implementation_version`, `parameters`, `initialization`, `tie_policy`, `fitness_version`, `decoder_version`, `validator_version` e `instrumentation_version`. Parámetros efectivos completos; `decoder_version = null` para variantes sin decodificador. No confundir versión de la propuesta con implementación existente. |
| `randomness` | `seed_decimal`, `generator` (`PCG64`), `library` (`numpy`) y `library_version`. La semilla decimal se serializa como cadena y conserva el valor entero de entrada. |
| `budget` | Los tres campos de entrada, incluidos sus `null`, y `time_scope = solver_including_initialization_and_validation`. Los valores concretos se eligen fuera de este contrato. |
| `code` | `commit`: hash Git completo; `dirty`: booleano; `patch_sha256`: hash del parche si hay cambios locales, o `null` con árbol limpio. Los archivos nuevos relevantes deben estar incluidos en el snapshot identificado por ese hash. |
| `environment` | `python_implementation`, `python_version`, `dependencies` (mapa de nombres y versiones exactas), `os`, `architecture`, `cpu`, `ram_bytes`, `workers`, `native_threads` y `concurrent_workload`. Se registra tanto el trabajador secuencial como los hilos nativos efectivos; la carga concurrente desconocida se declara con causa. |
| `timing` | `preparation_ns`, `finalization_ns`, `total_ns`, `clock` y `clock_resolution_ns`; `solver_ns` y el desglose de validación están en `result.timing`. Mantener las inclusiones y exclusiones de la tabla de tiempos. |
| `artifacts` | Lista de `{path, sha256, kind}` de archivos asociados; vacía si no hay. El resultado conserva índices internos; una exportación externa declara su transformación y mapeo. |
| `result` | El `SolverResult` completo de las tablas anteriores, con la misma versión de esquema que los ejemplos. |

El coordinador prepara el registro de identidad antes de ejecutar y conserva cada intento. No elimina errores o timeouts ni sobrescribe resultados anteriores. Tasas, promedios, precisión/recall/F1, selección de repeticiones y comparaciones publicadas pertenecen a M6, no a un `SolverResult` individual.

## Ejemplos conceptuales de salida

**Son ejemplos didácticos inventados, no mediciones ni ejecuciones de algoritmos.** Se muestran dos `SolverResult`; los metadatos del coordinador siguen siendo obligatorios para construir sus `RunRecord`. Se usa el grafo didáctico del #17: `n = 5`, aristas internas `{01,12,23,34,04,02,13}`. Se ilustra la inicialización de un GA con población de 128, sin llegar a una generación completa. Los límites ilustrativos son 10 000 000 ns, 100 evaluaciones y ninguna cota de iteraciones; no constituyen una configuración experimental elegida.

Éxito certificado en la cuarta evaluación, antes del límite:

```json
{
  "schema_version": "fhcp-solver-result/1",
  "status": "success",
  "stop_reason": "validated_cycle",
  "success_within_budget": true,
  "best_route": [0, 1, 2, 3, 4],
  "best_cost": 0,
  "validation": {"valid": true, "reason": null, "position": null, "vertices": null},
  "counters": {"evaluations_started": 4, "evaluations_completed": 4,
    "full_evaluations": 4, "incremental_evaluations": 0, "cache_hits": 0,
    "validations_started": 1, "validations_completed": 1,
    "iteration_unit": "generation", "iterations_completed": 0,
    "partial_iteration": {"phase": "initialization", "completed_items": 4, "planned_items": 128},
    "restarts": 0, "algorithm_counters": {}},
  "timing": {"solver_ns": 2000000, "validation_ns": 100000, "overrun_ns": 0,
    "first_success": {"elapsed_ns": 2000000, "evaluations_started": 4, "evaluations_completed": 4, "iterations_completed": 0}},
  "limits_reached": [],
  "error": null,
  "telemetry_complete": true
}
```

Timeout cooperativo con 30 000 ns de sobrepaso; la mejor ruta tiene una arista interna ausente, `2–4`. No se llamó al validador para esa ruta de costo positivo:

```json
{
  "schema_version": "fhcp-solver-result/1",
  "status": "exhausted",
  "stop_reason": "time_limit",
  "success_within_budget": false,
  "best_route": [0, 1, 3, 2, 4],
  "best_cost": 1,
  "validation": {"valid": null, "reason": "not_run", "position": null, "vertices": null},
  "counters": {"evaluations_started": 15, "evaluations_completed": 15,
    "full_evaluations": 15, "incremental_evaluations": 0, "cache_hits": 0,
    "validations_started": 0, "validations_completed": 0,
    "iteration_unit": "generation", "iterations_completed": 0,
    "partial_iteration": {"phase": "initialization", "completed_items": 15, "planned_items": 128},
    "restarts": 0, "algorithm_counters": {}},
  "timing": {"solver_ns": 10030000, "validation_ns": 0, "overrun_ns": 30000, "first_success": null},
  "limits_reached": ["time_limit"],
  "error": null,
  "telemetry_complete": true
}
```

Un tercer caso permite revisar la frontera: la misma ruta del primer ejemplo se certifica en 10 020 000 ns. Conserva costo cero y `validation.valid = true`, pero lleva `status = exhausted`, `stop_reason = time_limit`, `success_within_budget = false`, `first_success = null` y `overrun_ns = 20000`. No hay un tiempo hasta éxito dentro del presupuesto.

Si el productor entrega `[0,1,3,1,2]`, el resultado es `error / invalid_candidate`, con `error.code = repeated_vertex`, posición 3 e índice 1. El candidato rechazado no recibe costo; se conserva el mejor histórico previo o se devuelven ambos campos `null`. Si el evaluador asigna cero a `[1,0,2,3,4]` y el validador detecta `missing_closing_edge`, se informa `fitness_validation_mismatch`: no se declara éxito ni se continúa para encubrir el defecto.

## Alternativas y consecuencias

| Alternativa | Elección y consecuencia |
| --- | --- |
| Devolver solo un arreglo o `null` | Se descarta: pierde motivo, costo, presupuesto y error; se propone resultado estructurado y separado de metadatos del coordinador. |
| Usar únicamente fitness cero | Se descarta: un defecto del costo o del mapeo puede producir un falso éxito; el certificado independiente es obligatorio. |
| Equiparar generaciones de todas las familias | Se descarta: se registran unidad, avance parcial y evaluaciones. M6 decide cómo comparar recursos. |
| Completar siempre una generación o población | Se descarta: permite consumir más presupuesto del declarado. Se requieren comprobaciones internas y registro parcial. |
| Detener por tiempo excluyendo validación o inicialización | Se propone incluir ambas en el núcleo y registrar carga aparte. Así el certificado tardío permanece identificable. |
| Prometer timeout duro desde una función Python | Se descarta: llamadas nativas pueden sobrepasarlo. Un supervisor externo futuro debe registrar interrupción y telemetría perdida. |
| Reusar RNG global o depender del generador por defecto | Se propone RNG privado, nombre explícito y configuración registrada; hay que conservar entorno y secuencia de llamadas para reproducir. |
| Registrar certificados tardíos como éxito | Se descarta: conservar factibilidad y agotamiento en campos separados permite interpretar correctamente el intento. |

La estructura facilita intercambiar variantes y auditar un intento, a cambio de instrumentar trabajo parcial, fases, errores y límites. El contrato no asegura rapidez, éxito, igualdad numérica entre máquinas ni calidad de las variantes. No se crean experimentos ni resultados para justificar esas propiedades.

## Comprobación y criterios de implementación futura

Para revisar esta entrega: contrastar entradas y códigos con #17, costo y discrepancias con #18, contadores con #2 y evidencia de intentos con #6; verificar enlaces locales y sintaxis de los fragmentos JSON. Las comprobaciones efectivamente ejecutadas se registrarán en la PR, separadas de las pruebas futuras.

Cuando exista implementación, deberá cubrirse al menos:

- Rechazo de configuración antes de consumir RNG; semilla booleana, presupuesto cero, claves desconocidas y estado no finito.
- Reproducción con igual instancia, código, configuración, semilla y entorno usando límite de evaluaciones; un intento no altera el generador de otro.
- Inicialización agotada, última reserva de evaluación, interrupción parcial de población y reinicio contabilizado; nunca admitir una evaluación extra.
- Ruta nula antes del primer candidato; copia estable del mejor, empate sin reemplazo, cierre implícito y rechazo de ruta ilegal.
- Costo cero con certificado válido, discrepancia del validador, validación que no empieza por tiempo y certificado que termina tarde. Un reloj controlado permite comprobar exactamente la frontera sin esperar tiempo real.
- Contadores de inicio y terminación, partición de evaluaciones, tiempos de fases sin doble conteo y `first_success = null` en agotamiento/error.
- Fallo de infraestructura sin resultado completo: conservar intento, desconocidos y causa; cualquier repetición recibe otro ID.

Estas son obligaciones para M3–M5 y su instrumentación; no se afirma que hoy existan ni que los tres tests de entorno del #15 las comprueben.

## API de ejecución secuencial del #39

El GA puede importar `Budget`, `SolverResult` y `start_run` desde
`src.algorithms.execution`. Primero valida su variante y parámetros. Después
llama a `start_run(graph, seed=seed, budget=budget, iteration_unit="generation")`.
`Budget` conserva los tres límites del contrato. La semilla y los límites
activos deben ser enteros de Python (`int`) sin coerción. Si el grafo o la
configuración común se rechazan, `start_run` devuelve un `SolverResult` de error
con contadores en cero. En otro caso devuelve un `SolverRun` con un
`rng` privado que los operadores deben compartir dentro de ese intento.

1. Abrir la inicialización con `begin_phase("initialization", population_size)`
   y cada generación con `begin_phase("generation", planned_items, iteration=True)`.
   Si devuelve falso, el intento terminó. El tamaño planificado puede ser
   `None` para una fase de longitud variable.
2. Llamar a `checkpoint()` antes de generar cada candidato o admitir otro
   trabajo de búsqueda. `evaluate(route, cost_function)` verifica la permutación,
   reserva una evaluación y llama a `cost_function(graph, route)` con una
   tupla de índices internos. Una función de costo interrumpible puede
   consultar `time_expired()` y devolver `None` al agotarse el tiempo. La
   reserva sigue contabilizada. `evaluate` devuelve el costo entero o
   `None` si el intento terminó.
3. Llamar a `record_item()` al completar cada elemento planificado. Si el
   costo es cero, llamar inmediatamente a `certify_best()`, que devuelve el
   resultado terminal. La última reserva permite certificar si la llamada
   empieza antes del límite temporal.
4. Llamar a `complete_phase()` tras completar toda la fase, incluido el
   reemplazo cuando corresponda. La generación cuenta solo en ese punto.
   Si se necesita trabajo adicional para completarla, consultar
   `time_expired()` antes de hacerlo. `record_restart()` y `count(name)`
   contabilizan eventos de la variante.
5. Recuperar el resultado con `finish()` al agotar un límite o al aplicar la
   regla de parada de la variante. Para errores detectados por la variante,
   usar `fail(reason, code, message, **detail)` con el contexto del fallo.
   El coordinador puede convertir el resultado con `dataclasses.asdict`;
   `RunRecord` añade los metadatos de la ejecución.

El reloj es cooperativo e inyectable para pruebas. Al cumplirse exactamente
el límite ya no se admite trabajo nuevo. Una certificación admitida puede
terminar justo en el límite y ser exitosa. Si termina después, se conserva
el certificado y se registra el sobrepaso con estado de agotamiento. Esta
API trabaja con un solo flujo de ejecución. La CLI del #41 construye el
`RunRecord` a partir de su resultado.

## Coordinación por CLI (#41)

`python -m src.cli` valida configuración, carga un grafo con `load_fhcp_graph` y llama a `solve_ga`. El grafo conserva `source_path` y `manifest_revision` además de su ID y SHA-256. La revisión es el hash de los bytes del manifiesto que resolvió la carga. El coordinador añade esos datos a `instance` y conserva los índices internos del `SolverResult`. [API y decisiones del GA](ga-baseline.md).

Cada intento que supera el análisis de argumentos recibe un UUID y fecha UTC. Los resultados y diagnósticos usan stdout y stderr, respectivamente. Se publica el JSON completo con `allow_nan=False`. El guardado opcional reserva un directorio por UUID y renombra un temporal al cerrar la escritura. La reserva exclusiva protege registros anteriores y permite distinguir archivos completos de escrituras interrumpidas. Frente a una ruta de archivo reutilizable, este formato permite guardar varios intentos consecutivos en la misma carpeta. [Comandos y códigos de salida](../../README.md#cli-individual-del-ga).

`code.commit` y `code.dirty` identifican el checkout. Para un árbol con cambios, `patch_sha256` identifica el hash del diff binario respecto a `HEAD` y los hashes de los archivos sin seguimiento en orden de ruta. Las versiones de implementación, costo, validador e instrumentación se identifican por el SHA-256 de sus módulos. `missing_metadata` explica valores `null` cuando Git, el sistema o la carga carecen del dato. Los hilos nativos efectivos y la carga concurrente se registran como desconocidos porque esta CLI carece de mediciones para esos campos.

El tiempo de preparación comprende la configuración, la carga y la captura de metadatos. `result.timing` conserva el reloj y los contadores del GA, incluida su certificación. La finalización comprende la conversión del resultado en campos serializables. El total se mide desde el inicio del intento hasta armar el registro en memoria e incluye la llamada completa al solver. La codificación JSON y la escritura se realizan después. Una interrupción del solver detectada por la CLI registra `external_termination` con telemetría incompleta.

## Fuentes de la decisión

- [#17: grafo, ruta, mapeo, legalidad y certificación](graph-and-route-contracts.md), PR #22 integrada.
- [#18: costo, dominio, rechazos y adaptación por algoritmo](fitness.md), PR #23 integrada.
- [#2: variantes, unidades de trabajo y propuestas de actualización](../research/metaheuristics.md).
- [#6: éxito, tiempos, errores, censura y evidencia mínima](../research/evaluation-metrics.md).
- [#16: procedencia, selección y separación de certificados](dataset-selection.md).
- [PR #24: stack aceptado y comprobaciones de #15](https://github.com/ZapataFrame/FHCP-Challenge/pull/24), integrada en `main` mediante `4ef50bb`.
- Documentación oficial de [PCG64](https://numpy.org/doc/stable/reference/random/bit_generators/pcg64.html), [compatibilidad del RNG](https://numpy.org/doc/stable/reference/random/compatibility.html) y [reloj de Python](https://docs.python.org/3.14/library/time.html#time.perf_counter_ns), consultada el 9 de noviembre de 2026 para las propiedades concretas descritas. Las reglas del presupuesto y del resultado son decisiones propuestas del proyecto, no garantías atribuidas a esas fuentes.

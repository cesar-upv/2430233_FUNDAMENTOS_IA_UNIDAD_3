# Recocido simulado con intercambio

## Contexto y elección

El [issue #50](https://github.com/ZapataFrame/FHCP-Challenge/issues/50), a cargo de César Euresti · @cesar-upv, implementa la [adaptación SA del #2, §4.5](../research/metaheuristics.md#45-adaptación-propuesta-a-fhcp). Se apoya en Sean Luke, *Essentials of Metaheuristics*, segunda edición, versión en línea 2.4, [§2.4, pp. 25–26, algoritmo 13](https://people.cs.gmu.edu/~sean/book/metaheuristics/Essentials.pdf). El issue remite a §2.1; el apartado específico de SA en esa copia es §2.4. Se adopta minimización con enfriamiento geométrico por niveles y vecindad simétrica de intercambio de dos posiciones distintas.

La variante `SA_VARIANT = "geometric_swap_v1"` reutiliza `initialize_route`, `swap_mutation`, `evaluate_cost` y `SolverRun`, ya integrados en M4. Respeta los contratos de [rutas](graph-and-route-contracts.md), [costo entero](fitness.md) y [ejecución](solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39). No introduce CLI, acceso al dataset, reinicios, reparación, caché ni evaluación incremental. Los ajustes y comparativas pertenecen a M6.

## API y configuración efectiva

Desde `src.algorithms` se exportan `SA_VARIANT`, `SAConfigurationError`, `resolve_sa_parameters(parameters)` y `solve_sa(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult`. Se reutiliza `Budget` de `src.algorithms.execution`; el reloj inyectable devuelve nanosegundos.

Los cuatro parámetros son obligatorios, sin valores de ajuste predeterminados:

| Parámetro | Dominio |
| --- | --- |
| `initial_temperature` | Número Python finito representable como `float`, estrictamente positivo. |
| `cooling_factor` | Número Python finito con `0 < gamma < 1`. |
| `minimum_temperature` | Número Python finito con `0 <= minimum_temperature < initial_temperature`. |
| `moves_per_temperature` | Entero Python estrictamente positivo. |

El resolvedor copia el mapa y normaliza las tres magnitudes térmicas a `float`. Rechaza booleanos, escalares NumPy, cadenas, valores no finitos y enteros fuera del rango de `float`. No convierte el número de movimientos desde otros tipos. El orden de validación es: tipo de mapa y claves, claves desconocidas en orden lexicográfico, presencia de las cuatro claves en el orden de la tabla, conversión finita de las tres magnitudes, dominios térmicos y número de movimientos. `SAConfigurationError(ValueError)` expone `code` y `parameter`: `invalid_parameters`, `unknown_parameter`, `missing_parameter` o `invalid_parameter`.

El solver resuelve otra copia antes de iniciar reloj o RNG. Convierte un rechazo en `error / invalid_config`, fase `input`, con `error.detail.parameter` y contadores cero. Después `start_run` valida grafo (`n >= 3`), semilla y presupuesto. Se conserva el esquema `fhcp-solver-result/1`; el coordinador puede registrar los parámetros efectivos mediante el mismo resolvedor.

## Orden de búsqueda, aceptación y enfriamiento

1. Generar una permutación con `initialize_route(n, run.rng)` y evaluarla una vez. Conservar candidato actual y costo guardado. No fijar origen ni canonicalizar.
2. Mientras `T > minimum_temperature` y se admita trabajo, proponer `swap_mutation(current, rng=run.rng)` y evaluar el vecino una vez, incluido el cierre. Una permutación legal no acredita aristas válidas.
3. Con `delta = neighbor_cost - current_cost`, aceptar mejoras y empates sin consumir un uniforme. Para un empeoramiento y `T > 0`, consumir exactamente un `U = run.rng.random()` y aceptar si `U == 0` o `log(U) < -delta / T`. Rechazar en igualdad. La guarda para `T <= 0` rechaza empeoramientos sin consumir RNG; el bucle normal ya se detiene al llegar a cero.
4. Si se acepta, sustituir candidato actual y costo guardado; si se rechaza, conservar ambos. El mejor histórico lo guarda por copia `SolverRun` tras cada evaluación, con reemplazo solo por mejora estricta y conservación del primero en empate. Puede diferir del candidato actual.
5. Tras `moves_per_temperature` decisiones terminadas, aceptadas o rechazadas, calcular `T = T * cooling_factor` y reiniciar la cuenta del nivel. No se enfría tras una propuesta interrumpida. No se generan vecinos a temperatura igual o inferior al mínimo.

La comparación logarítmica evita calcular una exponencial que podría subdesbordar. El caso `U == 0`, posible en NumPy, se trata antes del logaritmo y de la división: a temperatura positiva se acepta incluso si la probabilidad exponencial no es representable. Si `delta / T` desborda a infinito positivo, cualquier `U > 0` se rechaza, sin excepción ni división por cero. El enfriamiento puede redondear a cero; entonces se detiene. Si redondea a la misma temperatura positiva, se detiene también por estancamiento numérico, evitando niveles térmicos idénticos indefinidos. Estas paradas naturales producen `exhausted / algorithm_stop`, salvo que coincida un límite común, que tiene prioridad.

Todas las decisiones usan el único `Generator(PCG64(seed))` privado del intento: primero `permutation(n)`, después `choice(n, size=2, replace=False)` por intercambio y únicamente para empeoramientos un uniforme. No hay sorteo de probabilidad de mutación. Cambiar el número de movimientos por nivel o las ramas de aceptación cambia la secuencia de decisiones. La reproducción exige mismo entorno y presupuesto de trabajo; un límite temporal puede cortar trayectorias diferentes.

## Presupuestos, fases y contadores

La inicialización abre `begin_phase("initialization", 1)` sin contar iteración. Cada propuesta abre `begin_phase("move", 1, iteration=True)`. Su elemento es el vecino evaluado: se registra con `record_item()` tras obtener un costo válido. Solo se completa la fase y se incrementa `iterations_completed` cuando termina la decisión y queda tiempo. `iteration_unit` es `"move"`. Los niveles térmicos no son iteraciones.

Cada costo se solicita mediante `run.evaluate`, que comprueba legalidad y reserva antes de evaluar. No se reevalúan costos guardados. Hay comprobaciones antes de construir el candidato inicial y cada vecino, en la admisión de evaluaciones, y antes y después de la decisión de aceptación. Estas últimas consultan solo el tiempo: agotar la última reserva de evaluaciones no impide terminar la decisión del movimiento ya admitido. La siguiente admisión aplica límites de tiempo, evaluaciones e iteraciones con la prioridad común.

Un costo cero se certifica **inmediatamente** con `certify_best()`, incluida la última reserva. No se espera al enfriamiento ni a la decisión de aceptación: queda una fase parcial con un elemento evaluado; la propuesta certificada no incrementa movimientos completos. Se conservan éxito dentro del presupuesto, certificado válido tardío, certificación no admitida por tiempo y discrepancia `fitness_validation_mismatch`, sin modificar el control común. Un timeout durante evaluación o aceptación conserva el mejor histórico ya evaluado y no fabrica una iteración completa.

`algorithm_counters` contiene solo eventos ocurridos, en unidades enteras: `accepted_moves` y `rejected_moves` cuentan decisiones completadas; `cooling_steps`, multiplicaciones térmicas tras un nivel completo; `cooling_stalls`, paradas por temperatura redondeada sin descenso. No hay reinicios. Los errores de legalidad conservan sus códigos; un `GraphError` de operador produce `invalid_candidate` y otros fallos producen `runtime_error`, conservando el mejor histórico. La parada cooperativa puede sobrepasar tiempo dentro de una llamada no interrumpible y registra ese exceso. Un agotamiento no demuestra no hamiltonicidad.

## Alternativas, consecuencias y comprobación

Se conserva intercambio frente a inversión de segmentos para seguir la variante del #2 y reutilizar los operadores del #38. Se elige enfriar después de un número explícito de movimientos frente a hacerlo después de cada propuesta; `moves_per_temperature = 1` permite este último caso. Los cuatro parámetros obligatorios evitan atribuir un ajuste experimental a valores arbitrarios. Cada movimiento usa tiempo y memoria auxiliar `O(n)`, incluidas copia, comprobación de legalidad y evaluación completa, además del grafo compartido.

Las pruebas usan grafos sintéticos, operadores reales y decisiones/reloj controlados: aceptación, enfriamiento, subdesbordamiento y cero, candidatos legales, conservación del mejor, reservas, fases parciales, certificación, errores y reproducción con aislamiento de RNG global. Los [comandos del README](../../README.md#recocido-simulado-con-intercambio) son los ejecutados en Linux x86_64 con CPython 3.14.10, NumPy 2.5.4 y pytest 9.2.0. No se comprobó esta entrega en Windows ni se midió rendimiento FHCP; la PR registra resultados y limitaciones.

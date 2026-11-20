# PSO global sobre claves reales

## Contexto y elección

El [#54](https://github.com/ZapataFrame/FHCP-Challenge/issues/54), a cargo de Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON, implementa la adaptación de PSO del [#2, §8.5](../research/metaheuristics.md#85-adaptación-propuesta-a-fhcp). La variante `global_real_keys_v1` usa topología global y rondas síncronas. El movimiento sigue la formulación descrita en *Algorithms for Optimization*, primera edición, §9.4, de Kochenderfer y Wheeler, y en *Essentials of Metaheuristics*, §3.5, de Luke. El orden de actualización, la representación de rutas y la política de desempate se fijan para FHCP. [Kochenderfer y Wheeler](https://algorithmsbook.com/optimization/) · [Luke](https://people.cs.gmu.edu/~sean/book/metaheuristics/).

Se reutilizan el [grafo y la ruta internos](graph-and-route-contracts.md), el [decodificador de claves reales del #49](real-key-decoder.md), el [costo entero](fitness.md) y el [control de ejecución](solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39). Una ruta candidata representa los índices internos de los vértices. El costo cuenta las aristas ausentes, incluido el cierre. El validador independiente certifica cada candidato de costo cero.

## API y parámetros

`src.algorithms` exporta `PSO_VARIANT`, `PSOConfigurationError`, `resolve_pso_parameters(parameters)` y `solve_pso(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult`.

| Parámetro | Dominio | Presencia |
| --- | --- | --- |
| `swarm_size` | Entero Python mayor o igual que 2. | Obligatorio. |
| `inertia` | Coeficiente ω, finito y no negativo. | Obligatorio. |
| `cognitive_coefficient` | Coeficiente c1, finito y no negativo. | Obligatorio. |
| `social_coefficient` | Coeficiente c2, finito y no negativo. | Obligatorio. |
| `velocity_limit` | L, finito y positivo, o `None` para desactivar la cota. | Opcional. Por defecto `None`. |

El resolvedor copia el mapa y normaliza coeficientes y cota a `float` de rango binario64. Acepta valores de tipo `int` o `float` de Python para esos campos. Rechaza booleanos, escalares NumPy, texto, infinito, NaN y enteros que exceden el rango finito al convertirlos. Las claves deben ser de texto y pertenecer a la tabla. `PSOConfigurationError` identifica `code` y `parameter`. `solve_pso` convierte una configuración inválida en `error / invalid_config` antes de acceder al reloj o al RNG. `start_run` verifica el grafo, la semilla y el `Budget` explícito.

## Movimiento, memoria y RNG

1. Inicializar y evaluar las partículas por índice. Para cada una, extraer primero `rng.random(n)` para las claves en `[0, 1)` y luego `rng.random(n) - 0.5` para las velocidades en `[-0.5, 0.5)`. Ambos sorteos son uniformes de tipo `float64`. Con cota, recortar las velocidades a `[-L, L]` antes de guardarlas. Si `L < 0.5`, el recorte acumula los valores de las colas en los extremos. Tras evaluar, copiar la posición al mejor personal y considerar su costo para el mejor global.
2. Abrir cada ronda con el mejor global de la ronda anterior. En orden de partícula, extraer dos vectores independientes de uniformes en `[0, 1)`, primero `r1` y luego `r2`, incluso cuando su coeficiente sea cero. Usar el PCG64 privado del intento para todos los sorteos.
3. Calcular `v_nueva = ω*v + c1*r1*(pbest - x) + c2*r2*(gbest - x)` por coordenada. Comprobar que sea finita antes del recorte opcional y aplicar `x_nueva = x + v_nueva` con la velocidad resultante. Las claves pueden tomar cualquier valor finito. El decodificador ordena por `(clave, índice interno)` y resuelve así los empates de claves.
4. Reservar y evaluar cada propuesta una vez, incluidas las rutas repetidas. Guardar la posición y la velocidad nuevas como estado actual. Actualizar las memorias con copias solo ante un costo estrictamente menor. Un empate personal conserva la memoria previa y un empate global conserva la primera evaluación que alcanzó ese costo. El estado de la ronda anterior sigue disponible durante la construcción de la siguiente.
5. Tras evaluar todas las propuestas, preparar las memorias y comprobar el plazo, sustituir el estado y completar la ronda. El mejor global actualizado guía la siguiente ronda. `SolverRun` mantiene en paralelo la mejor ruta evaluada, con el mismo desempate por orden de evaluación.

## Límites y consecuencias

La inicialización se registra como fase `initialization` y la iteración del resultado tiene unidad `round`. Una fase parcial conserva las evaluaciones realizadas y la mejor ruta histórica. Una ronda solo incrementa el contador de iteraciones tras completar sus evaluaciones y memorias. Si la última reserva deja la ronda completa y el plazo sigue vigente, se registra como completa. Un costo cero se certifica inmediatamente, incluso en la última reserva. El control común distingue éxito dentro del presupuesto, certificado tardío, discrepancia de validación, agotamiento y error. Devuelve el `SolverResult` con esquema `fhcp-solver-result/1`.

Las operaciones del movimiento detectan desbordamientos y resultados inválidos. Una clave o velocidad no finita devuelve `error / non_finite_state` antes de decodificar o reservar otra evaluación. El recorte de velocidad se aplica a valores finitos y permite limitar el paso de cada coordenada. El plazo es cooperativo, con comprobaciones entre operaciones, y el resultado registra el sobrepaso observado. Agotar el presupuesto deja abierta la existencia de un ciclo hamiltoniano.

Para P partículas y n vértices, las posiciones, velocidades y memorias usan `O(Pn)` espacio. Cada propuesta requiere `O(n)` operaciones de movimiento y una ordenación de claves con `O(n log n)` comparaciones, además del costo de evaluación. La semilla y el presupuesto de evaluaciones permiten reproducir la ruta, el costo y los contadores en el mismo entorno. La [verificación de Windows](../../README.md#pso-global-sobre-claves-reales) incluye pruebas controladas y un éxito certificado en un grafo sintético. La CLI y su verificación de integración corresponden a #55 y #56. El ajuste y las comparativas corresponden a M6.

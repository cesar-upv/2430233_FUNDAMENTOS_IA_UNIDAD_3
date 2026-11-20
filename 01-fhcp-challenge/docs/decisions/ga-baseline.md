# GA generacional base

## Contexto y alcance

El [issue #40](https://github.com/ZapataFrame/FHCP-Challenge/issues/40), a cargo de Junior Arturo Vázquez Leonel · @Arturo2430, integra la [adaptación del GA del #2](../research/metaheuristics.md#35-adaptación-propuesta-a-fhcp) sobre los contratos de [grafo y ruta](graph-and-route-contracts.md), [costo](fitness.md) y [ejecución](solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39). Las dependencias #37, #38 y #39 están integradas mediante las PR #44, #45 y #43. La variante se presenta para revisión como parte de esta entrega; sus valores por defecto son decisiones de configuración acordadas, no resultados de ajuste experimental.

Se implementa un GA secuencial con torneo de minimización, OX, intercambio por descendiente y reemplazo generacional con elitismo. Reutiliza el [contrato de operadores](ga-permutation-operators.md). No modifica esos operadores ni el control de ejecución. CLI, `RunRecord` e integración FHCP del solver siguen en #41–#42; no se incluyen variantes de M5 ni benchmarks de M6.

## API y parámetros efectivos

Se importa desde `src.algorithms`:

```python
GA_VARIANT = "generational_ox_swap_v1"
resolve_ga_parameters(parameters) -> dict[str, int | float]
solve_ga(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult
```

`parameters` es un mapa; el resolvedor devuelve una copia con las cinco claves efectivas. El solver vuelve a resolver y conserva su propia copia estable antes de iniciar. Esto permite al coordinador del #41 registrar la misma configuración sin duplicar las reglas. `budget` es el `Budget` del #39; el reloj inyectable devuelve nanosegundos y existe para comprobar fronteras sin esperar tiempo real. El solver no recibe rutas a archivos ni certificados oficiales.

| Parámetro | Dominio | Valor por defecto |
| --- | --- | --- |
| `population_size` | Entero Python ≥ 2. | Obligatorio. |
| `tournament_size` | Entero Python entre 1 y `population_size`. | Obligatorio. |
| `crossover_rate` | Número Python finito en `[0, 1]`. | `0.8`. |
| `mutation_rate` | Número Python finito en `[0, 1]`, por descendiente. | `0.010`. |
| `elite_count` | Entero Python entre 0 y `population_size - 1`. | `max(1, population_size // 100)`. |

El elitismo por defecto es 1% truncado con mínimo de una élite: poblaciones 2, 50, 99, 100 y 128 conservan una; 200 y 250 conservan dos. Un `elite_count` explícito, incluido cero, sustituye ese cálculo. No se admite una segunda clave de porcentaje. Las tasas aceptan `int` o `float` de Python y se normalizan a `float`; los tamaños solo admiten `int` de Python. Se rechazan booleanos, escalares NumPy, cadenas, valores no finitos y conversiones implícitas.

`resolve_ga_parameters` levanta `GAConfigurationError(ValueError)` con `code`, `parameter` y mensaje. El orden es: tipo del mapa y sus claves, claves desconocidas en orden lexicográfico, presencia de población y torneo, rangos de población, torneo, cruce, mutación y élites. Los códigos son `invalid_parameters`, `unknown_parameter`, `missing_parameter` e `invalid_parameter`.

`solve_ga` convierte esos rechazos en `error / invalid_config`, fase `input`, con el campo afectado en `error.detail.parameter`, contadores cero y sin iniciar reloj, población o RNG. Después delega semilla, presupuesto y grafo a `start_run`; se conservan sus códigos y tipos estrictos. No se cambia el esquema `fhcp-solver-result/1`.

## Variante y orden de actualización

1. **Inicialización:** generar y evaluar `population_size` permutaciones mediante `initialize_route`. Se admite repetición de individuos; no hay deduplicación, reparación, canonicalización ni caché. Cada ruta se guarda como tupla y cada costo se calcula mediante `evaluate_cost`, contando cierre implícito.
2. **Élites:** ordenar por costo guardado de forma estable. Un empate conserva el orden actual de población. Copiar los mejores `elite_count` individuos con su costo, sin solicitar evaluaciones.
3. **Padres:** seleccionar dos torneos independientes sobre la población anterior, congelada durante toda la generación. Cada torneo muestrea con `rng.choice(population_size, size=tournament_size, replace=False)`; gana la pareja mínima `(costo, índice de población)`. Un individuo no se repite dentro de un torneo, pero puede ganar ambos.
4. **Descendiente:** consumir una extracción `rng.random()` y aplicar OX si es menor que `crossover_rate`; de lo contrario, copiar el primer padre. Consumir después otra extracción y aplicar intercambio si es menor que `mutation_rate`. Las dos probabilidades se sortean incluso con tasas 0 o 1; los operadores consumen sus decisiones adicionales solo al aplicarse. Se produce un hijo por vuelta, sin hijo complementario automático.
5. **Evaluación y reemplazo:** evaluar cada hijo una vez, aunque repita una ruta, y añadirlo después de las élites. Al completar los descendientes y quedar tiempo, sustituir la población anterior. El orden de los hijos es el de producción.

Todas las decisiones usan el mismo `Generator(PCG64(seed))` privado del intento. No hay aleatoriedad global, reinicios ni regla de estancamiento. El mejor histórico lo conserva `SolverRun`: una mejora estricta lo sustituye; un empate mantiene el primero, aunque otro individuo lo desplace en la población. Comparar costos guardados no es evaluar.

## Presupuestos y resultados

La inicialización abre `begin_phase("initialization", population_size)` y no cuenta como generación. Cada generación abre `begin_phase("generation", population_size - elite_count, iteration=True)`: sus elementos son **descendientes evaluados**, excluidas las élites. Una fase parcial puede tener todos sus elementos terminados y aun así no ser una generación completa si falta el reemplazo.

Se consulta `checkpoint()` antes de generar candidatos, copiar cada élite y entre selección de padres, cruce y mutación. Solo `run.evaluate` reserva una evaluación, antes de ejecutarla, y registra el mejor candidato legal. Tras cada evaluación completada se registra un elemento. Si su costo es cero, se llama inmediatamente a `certify_best`; la fase permanece abierta incluso si era su último elemento.

Al terminar los descendientes se consulta `time_expired()`, no `checkpoint()`: la última evaluación permitida puede haber agotado su límite sin impedir el reemplazo admitido. Si queda tiempo, se reemplaza la población y se llama a `complete_phase`. Si no queda tiempo, se conserva la fase parcial y no se incrementa la generación. La próxima admisión detecta el límite de evaluaciones o iteraciones, sin reservar trabajo extra. Completar el registro de inicialización tampoco consume otra evaluación.

El control es cooperativo: muestreo, ordenación, operadores, costo y validador pueden sobrepasar el límite durante una llamada; se comprueba de nuevo en sus fronteras. No se promete un timeout duro. La certificación independiente consume tiempo pero no evaluaciones de costo. Se preservan los estados del #39: éxito validado dentro del presupuesto, agotamiento, costo cero sin validación admitida, certificado válido tardío y discrepancia `fitness_validation_mismatch`.

Los errores inesperados de ejecución se registran mediante `run.fail`, conservando el mejor histórico. Una ruta ilegal producida al evaluar conserva los códigos del #17; un `GraphError` de un operador se informa como `invalid_candidate`, y otros fallos como `runtime_error`. No se devuelven datos privados de mensajes de excepciones imprevistas. Agotar cualquier límite no demuestra que el grafo sea no hamiltoniano.

## Alternativas, consecuencias y comprobación

Se eligen torneos sin reemplazo frente a permitir repeticiones dentro de cada torneo, y un hijo por vuelta frente a generar pares: ambas decisiones afectan el consumo de RNG y deben conservarse para reproducir la variante. El porcentaje truncado mantiene al menos una élite en poblaciones pequeñas; no equivale exactamente a 1% en ellas. Los valores explícitos permiten desactivar elitismo y cambiar probabilidades sin presentar estos valores como óptimos.

La ordenación de élites y las copias consumen tiempo, pero no evaluaciones. No se reevaluará la población para seleccionar ni para obtener el mejor histórico. La certificación separada evita declarar éxito por costo cero sin comprobar las aristas.

Las pruebas usan grafos sintéticos, operadores reales y dobles controlados para aislar selección, reemplazo, fallos y reloj. Comprueban parámetros efectivos, invariantes, secuencia de RNG, reservas, fases parciales y reproducción con presupuesto de evaluaciones. Los [comandos del README](../../README.md#ga-generacional-base) permiten repetirlas; plataforma, commit y resultados se registran en la PR del #40. No son mediciones de rendimiento ni evidencia de éxito sobre FHCP.

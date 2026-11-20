# Artificial Bee Colony discreto

## Contexto y elección

Entrega del [#52](https://github.com/ZapataFrame/FHCP-Challenge/issues/52), responsable Eder Omar Zúñiga Zavala · @KirbyStone69. Implementación presentada para revisión e integración. Se adopta la adaptación propia de [#2 §6.5](../research/metaheuristics.md#65-adaptación-propuesta-a-fhcp): fuentes que son permutaciones, empleadas, observadoras y hasta una exploradora. No se traslada una ecuación continua a índices ni se implementa The Bees Algorithm. La investigación distingue el ABC numérico original de esta vecindad discreta propuesta para FHCP.

Se reutilizan los contratos de [grafo/ruta](graph-and-route-contracts.md), [costo](fitness.md) y [ejecución](solver-and-result-contracts.md), junto con `SolverRun`. No se modifica el control común ni el GA. La CLI y RunRecord multialgoritmo corresponden al #55; ajuste de parámetros y comparativas, a M6. No se afirma superioridad experimental.

## API y parámetros

Desde `src.algorithms`:

```python
ABC_VARIANT = "sequential_partner_swap_v1"
resolve_abc_parameters(parameters) -> dict[str, int]
solve_abc(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult
```

Los dos parámetros son obligatorios: `source_count` (S, entero Python >= 2) y `limit` (entero Python >= 1). No se aceptan booleanos, reales, enteros NumPy ni claves desconocidas. Las S propuestas de observadoras y el máximo de una exploradora son constantes de la variante, no parámetros ocultos configurables. El resolvedor copia el mapa antes de reloj/RNG y expone `ABCConfigurationError` con `code` y `parameter`; el solver convierte el rechazo en `error / invalid_config` con diagnóstico y contadores cero. Semilla y Budget se validan mediante `start_run`, antes de iniciar reloj o PCG64. No se cambian parámetros durante el intento.

## Secuencia, selección y desempates

1. Inicializar S permutaciones independientes con `initialize_route`; evaluar una vez cada una, en orden de índice, con `trials=0`. Inspeccionar inmediatamente todo costo cero.
2. Empleadas: recorrer fuentes de 0 a S-1. Elegir socio uniforme k != i; elegir uniformemente una posición donde ambas rutas difieran y colocar allí el vértice del socio mediante intercambio. Si coinciden, intercambiar dos posiciones distintas al azar. Las actualizaciones son secuenciales: las fuentes posteriores ven las mejoras anteriores.
3. Aceptar solo costo estrictamente menor y reiniciar `trials=0`. En empate o empeoramiento conservar ruta/costo e incrementar `trials` en uno. Se comparan costos guardados, sin reevaluarlos.
4. Observadoras: calcular y congelar pesos `1/(1+C)` con los costos posteriores a empleadas; normalizar una vez. Realizar S selecciones con reemplazo, cada una seguida de socio, vecino, evaluación y la misma regla de aceptación. Las probabilidades no cambian durante esta fase, aunque las rutas sí.
5. Exploración: elegir como máximo una fuente con `trials>=limit`: mayor trials, menor índice en empate. Tras admitir trabajo, registrar abandono e inicializar una permutación nueva. Al completar su evaluación reemplazar la fuente sin comparar costos, con trials cero; registrar renovación y reinicio. Si no hay candidata, registrar exploración omitida.

El histórico lo conserva `SolverRun` por copia, con mejora estricta y primero en empate: abandonar su fuente no lo elimina. Rotación y orientación no se canonicalizan. La vecindad preserva permutaciones, no garantiza aristas ni mejora.

## Aleatoriedad y política numérica

Únicamente el PCG64 privado del intento. Inicialización y renovación consumen una `permutation(n)`. Para socio se extrae `integers(S-1)` y se salta el índice i. Para vecino se enumeran diferencias en orden ascendente, se extrae `integers(cantidad)` y se busca el vértice en la ruta actual; en coincidencia se usa `choice(n, size=2, replace=False)`. Cada observadora primero consume `choice(S, p=probabilidades)` y después las extracciones de socio/vecino. No se sortean exploradoras ni desempates.

Costos, trials y contadores son enteros. Los pesos usan flotantes de Python y `math.fsum` para su suma; son positivos y finitos para el dominio CSR aceptado y S representable en memoria. La selección proporcional usa NumPy sin redondear pesos a enteros. Reproducción se exige con mismas versiones, semilla y presupuesto de evaluaciones; con tiempo real, los puntos de corte pueden variar. No se fijan probabilidades empíricas ni tiempos exactos.

## Fases, presupuesto y resultado

La inicialización es `begin_phase("initialization", S)` y no cuenta como ciclo. El ciclo completo usa una fase compuesta `begin_phase("abc_cycle", 2*S+1, iteration=True)` para conservar el formato común sin modificar su API:

| Elementos completados | Trabajo pendiente |
| --- | --- |
| 0 a S-1 | Empleada del índice indicado por ese contador. |
| S a 2S-1 | Observadora del ordinal `completed_items-S`. |
| 2S | Decisión de exploración o renovación pendiente. |
| 2S+1 | Exploración terminada; falta registrar cierre del ciclo si el tiempo se agotó. |

Un elemento es una propuesta evaluada y aplicada; el último elemento es la decisión de exploración, incluso si no hace falta renovar. Solo se incrementa `iterations_completed` después de terminar las tres fases y comprobar tiempo. Una interrupción conserva el prefijo completado; una certificación inmediata deja abierto el ciclo incluso en su último elemento.

`algorithm_counters` registra `employed_proposals`, `employed_improvements`, `onlooker_proposals`, `onlooker_improvements`, `scout_abandonments`, `scout_renewals` y `scout_skips`. Claves ausentes equivalen a cero. Abandono cuenta una renovación admitida, aunque una interrupción posterior impida evaluarla; renovación y `restarts` cuentan reemplazos completados. La fuente anterior se conserva hasta obtener el nuevo costo. Ninguno de estos contadores consume evaluaciones adicionales.

Se comprueban límites en los bucles y antes de proponer/renovar; `run.evaluate` reserva cada evaluación antes de ejecutarla. Al cerrar el ciclo se consulta tiempo, sin exigir otra reserva: si se agotó la última evaluación y no hay fuente expirada, puede terminar la exploración vacía y completar el ciclo. Si hay que renovar, el ciclo permanece parcial cuando no existe reserva. Las operaciones son cooperativas, no hay timeout duro dentro de una llamada a NumPy, vecindad, evaluación o certificación.

Todo costo cero se certifica inmediatamente con `certify_best`, incluso en la última reserva. Se conservan éxito dentro del presupuesto, agotamiento, certificado tardío, discrepancia y errores del contrato #19. `GraphError` de operador produce `invalid_candidate`; otros errores imprevistos, `runtime_error`, conservando el histórico. Agotar el presupuesto no prueba inexistencia de ciclo.

## Consecuencias y comprobación

La actualización secuencial y probabilidades congeladas son parte de la variante; reemplazarlas por actualización simultánea o pesos dinámicos cambia el algoritmo. Un limit pequeño puede consumir presupuesto en renovaciones y abandonar buenas fuentes. El histórico separado evita perder la mejor ruta, pero no garantiza hallar un ciclo. Vecindad y copias requieren O(n); un ciclo cuesta O(S(n+E(n))) más O(S²) por las S selecciones NumPy con vector de probabilidades, con E(n) el costo completo aceptado. La memoria de fuentes es O(Sn).

Las pruebas controlan decisiones de vecindad/socio, trials, selección de exploradora y pesos, presupuestos en las tres fases, reproducción, RNG global, último permiso y fronteras temporales de certificación. Son pruebas sintéticas, no benchmarks ni evidencia de rendimiento sobre FHCP. Los [comandos del README](../../README.md#artificial-bee-colony-discreto) describen la comprobación en Linux; Windows no se ha ejecutado para esta entrega.

# Costo incremental, recalentamiento y feromonas por arista

## Contexto y elección

Por solicitud del responsable se implementan tres extensiones independientes de
las [variantes guiadas v2](graph-guided-search.md): costo incremental para SA/ABC,
recalentamiento de SA y almacenamiento de feromonas por arista en AS. No se
modifican los resultados, presupuestos o configuraciones congeladas de M6.
Tampoco se agregan reparación local ni cambios de diversidad en esta revisión.

Las opciones se activan explícitamente; sin ellas se conservan las políticas v1/v2.
La [configuración exploratoria v3](../../experiments/configs/search-enhanced-v3-presets.json)
activa las tres extensiones sobre los presets guiados anteriores. No es un plan
aceptado por el coordinador de M6 ni una nueva selección de parámetros.

## Evaluación incremental de SA y ABC

- `cost_mode=incremental` activa los deltas; `full` conserva el recálculo previo.
- `incremental_check_interval` es un entero positivo; con modo incremental vale
  1000 por defecto. No se admite este intervalo con el modo completo.
- Inicialización y exploradoras de ABC siguen evaluándose de forma completa.
  Las propuestas swap o inversión se describen con índices y se materializan
  como permutaciones nuevas, sin modificar la ruta de origen.

Un swap solo cambia las conexiones incidentes a sus dos posiciones; se
deduplican los índices cuando son contiguas o cruzan el cierre. Una inversión
conserva sus aristas interiores porque el grafo es no dirigido, y solo cambia
dos conexiones de frontera. Invertir toda la ruta o no cambiar posiciones deja
el costo intacto. El delta consulta como máximo ocho aristas para swap o cuatro
para inversión, contando las consultas antes y después. Esto no convierte todo
el movimiento en O(1): copiar la ruta, invertir un segmento y comprobar la
permutación siguen costando O(n); `has_edge` conserva su costo CSR.

`SolverRun.evaluate_incremental` comprueba la legalidad y reserva una evaluación
antes de calcular el costo. Una mejora del mejor histórico —incluido cualquier
costo cero— se recalcula con el evaluador completo. También se recalcula cada
`incremental_check_interval` propuestas incrementales completadas. Si hay
inconsistencia se termina con `fitness_validation_mismatch` y código
`incremental_cost_mismatch`; no se acepta ni corrige silenciosamente el delta.
El candidato con costo cero todavía necesita certificación independiente dentro
del presupuesto, incluso si agotó la última reserva disponible.

Los contadores mantienen `full_evaluations + incremental_evaluations =
evaluations_completed`; cada valoración consume una sola reserva. Las
comprobaciones completas de control pertenecen a esa misma valoración y se
registran además en `algorithm_counters.incremental_full_checks`. No son nuevas
propuestas ni otra reserva. No se ha implementado caché; `cache_hits` sigue en cero.
El cambio de instrumentación se identifica por el hash de `execution.py`.

## Recalentamiento de SA

`reheat_after` es un entero no negativo, con cero o ausencia como desactivación.
Cuando es positivo, cuenta propuestas consecutivas sin mejorar el mejor costo
histórico. Al alcanzar ese número, tocar la temperatura mínima o detectar
estancamiento numérico del enfriamiento, SA vuelve a su mejor ruta y restaura
`initial_temperature`. Reinicia el contador de estancamiento y los movimientos
de la temperatura actual; no reinicia presupuesto, reloj, semilla ni contadores
globales. `reheats` y `restarts` registran cada evento.

El reinicio forma parte de la transición del movimiento admitido; no evalúa otra
ruta ni añade reservas. No se aplica después de un éxito ni permite sobrepasar
el límite de iteraciones. La aceptación de Metropolis, el factor de enfriamiento
y el número de movimientos por temperatura conservan sus valores explícitos.
Sin recalentamiento, la parada por temperatura mínima continúa disponible.

## Feromonas dispersas de AS

`pheromone_storage=edges` almacena un vector `float64` de longitud m y un índice
por par no dirigido real; consulta ambos sentidos en la misma entrada. Se
inicializa y actualiza en O(m) espacio, sin asignar un vector de n(n−1)/2 pares.
`all_pairs` conserva el almacenamiento anterior. El diccionario de índices añade
memoria: el tamaño del vector no es el RSS total, y en grafos densos esta
representación puede tener más sobrecarga que el vector anterior.

Las aristas reales conservan evaporación, depósito y cotas previas. Los pares
ausentes tienen feromona virtual constante `pheromone_min`; no se almacenan,
evaporan ni reciben depósitos. Se cuentan los depósitos omitidos en
`pheromone_missing_deposits_skipped`. Con `neighbor_guided`, la construcción usa
solo vecinos reales mientras existan, y salta uniformemente si se bloquea;
esos saltos siguen teniendo costo. Con `all_vertices`, los pares ausentes siguen
siendo candidatos con su valor virtual y penalización `epsilon`.

Se comprueba el presupuesto al construir el índice, inicializar bloques y
actualizar feromonas. Una interrupción conserva fase parcial y no reutiliza ese
estado. El detalle `pheromone_bytes` ante un fallo de asignación identifica el
payload numérico solicitado, sin atribuirle el tamaño del diccionario.

## CLI, registros y verificación

Las opciones CLI son `--cost-mode`, `--incremental-check-interval`,
`--reheat-after` y `--pheromone-storage`, restringidas a las familias aplicables.
Cuando se activa alguna extensión, `procedure.variant` termina en `_enhanced_v3`.
Además de los hashes de solver, evaluador, validador e instrumentación, el registro
identifica `local_moves_version` para costo incremental y
`pheromone_storage_version` para almacenamiento por aristas. Parámetros y
presupuestos efectivos quedan en el RunRecord.

`tests/test_search_enhancements.py` contrasta swaps/inversiones con el costo
completo en grafos completos, dispersos y desconectados, incluyendo cierre,
posiciones adyacentes y segmentos completos. Comprueba contadores, detección de
deltas incorrectos, éxito en la última reserva, cero tardío, reproducción de
trayectorias completas/incrementales, recalentamiento/restauración del mejor,
presupuestos, simetría, actualización por fórmula independiente y ausencia de
asignación cuadrática en el modo disperso. Las comprobaciones sintéticas no son
mediciones de rendimiento del FHCP.

Las pruebas individuales deben conservar nuevos UUID y separarse de M6. Una
comprobación corta con una semilla acredita integración; las tasas de éxito y
la comparación de rendimiento requieren una campaña nueva con varias semillas,
presupuestos y condiciones fijados. Para reproducir M6 se utiliza su checkout
original y entorno, no los módulos modificados de esta entrega.

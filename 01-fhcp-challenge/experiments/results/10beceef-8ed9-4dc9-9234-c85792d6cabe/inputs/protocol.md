# Protocolo de comparación FHCP — M6 v1

## Contexto, alcance y alternativas

**Estado:** propuesta para revisión del [#67](https://github.com/ZapataFrame/FHCP-Challenge/issues/67).
Responsable: César Euresti · @cesar-upv. Base integrada: `469bef2`, incluida la
[PR #66](https://github.com/ZapataFrame/FHCP-Challenge/pull/66) del #56.
Su humo prueba integración; no mide calidad comparativa. Esta decisión y
[`benchmark-v1.json`](../../experiments/configs/benchmark-v1.json) fijan el plan
antes de observar resultados. La campaña, el ajuste y la congelación material
corresponden al #70, después de integrar ejecutor #68 y agregador #69.
No hay resultados de ajuste ni configuraciones ganadoras en esta entrega.

Se conservan los contratos de [ejecución y RunRecord](solver-and-result-contracts.md),
la [selección #16](dataset-selection.md) y las [métricas #6](../research/evaluation-metrics.md).
El catálogo identifica exactamente las variantes integradas:

| CLI / familia | Variante | Decisión | Iteración completa |
| --- | --- | --- | --- |
| `ga` / GA | `generational_ox_swap_v1` | [GA](ga-baseline.md) | Generación y reemplazo |
| `sa` / SA | `geometric_swap_v1` | [SA](sa-baseline.md) | Movimiento y aceptación |
| `as` / ACO | `ant_system_missing_pairs_v1` | [Ant System](ant-system-baseline.md) | Construcciones y actualización |
| `abc` / ABC | `sequential_partner_swap_v1` | [ABC](abc-baseline.md) | Empleadas, observadoras y exploración |
| `de` / DE | `rand_1_bin_real_keys_v1` | [DE](de-baseline.md) | Generación y reemplazo |
| `pso` / PSO | `global_real_keys_v1` | [PSO](pso-baseline.md) | Ronda y memorias |

Se elige igual cupo de evaluaciones con plazo cooperativo común y supervisor
externo. Evaluaciones solas permiten trayectorias repetibles pero no acotan el
costo de construcciones AS; tiempo solo permite trabajo muy distinto y cortes
variables; igual número de iteraciones no representa trabajo comparable.
Se registran ambos recursos sin afirmar igualdad de CPU por evaluación.
El mismo presupuesto de intentos y dos candidatos por familia acotan el ajuste,
frente a búsquedas extensas de parámetros o elegir después de ver evaluación.
No ajustar sería una línea base más barata, pero dejaría sin explorar siquiera
una sensibilidad local. Dos candidatos tampoco equivalen a optimizar una familia.

## Partición y fases preregistradas

No se cambian IDs ni usos del #16. Las semillas se enumeran como cadenas decimales
en el JSON; no son rangos a decidir durante la campaña. Todas las familias usan
las mismas semillas en cada fase. Una semilla común no implica sorteos equivalentes.

| Fase | Instancias | Configuración | Semillas / repeticiones por celda | Evaluaciones / plazo solver | Ensayos |
| --- | --- | --- | --- | --- | ---: |
| `smoke` | graph1, graph2 | c1 por familia | 17 / 1 | 20 / 5 s | 12 |
| `tuning` | graph58, graph268 | c1 y c2 por familia | 101, 211, 307, 401, 503 / 5 | 2,000 / 10 s | 120 |
| `evaluation` | graph48, graph175, graph74, graph479 | Ganadora congelada por familia | 1001 a 1030, enumeradas / 30 | 10,000 / 30 s | 720 |
| `scale` | graph1001 | La misma ganadora | Las mismas 30 | 10,000 / 30 s | 180 |
| `verification` | graph1 | Ganadora congelada | 17 / 1 par de repeticiones | 100 / sin plazo cooperativo | 6 pares |

`max_iterations=null` siempre. El supervisor externo limita **cada proceso** a
120 s en todas las fases, incluida verificación. Esta fase produce 12 intentos
para seis identidades, sin contribuir a tasas primarias; si interviene el
supervisor, no se declara repetición de trayectoria comprobada.
Las demás fases tienen exactamente un intento primario por identidad.
El subconjunto intencional no permite inferencia sobre los 1001 grafos.
Graph1001 se presenta separado, sin promediarlo con evaluación. No hay exclusiones
previstas. Los motivos estructurales se toman del #16, sin nuevas inferencias.

Graph1/graph2 ya se reutilizaron en desarrollo y pruebas M3–M5. La partición fue
inspeccionada para carga y certificación; eso no constituye ajuste. No consta una
campaña de ajuste previa en esta base. En #70 se declarará cualquier otro uso
previo conocido. No consultar tours oficiales, resultados reservados ni tiempos
externos para elegir parámetros. El solver solo recibe el grafo verificado.
Las certificaciones históricas del dataset no autorizan usar sus rutas para
inicializar, reparar, ajustar o decidir parada. La auditoría usa las aristas y
el candidato producido, sin comparar contra un tour oficial único.

## Candidatos, selección y congelación

El JSON es la fuente de valores efectivos completos; incluso los valores por
defecto están expandidos. Son elecciones previas, no parámetros óptimos medidos.
Cada c2 cambia un parámetro de c1, manteniendo los restantes:

| Familia | c1 | Cambio en c2 |
| --- | --- | --- |
| GA | P=20, torneo=3, cruce=0.8, mutación=0.01, élites=1 | Mutación=0.1 |
| SA | T=2, factor=0.95, mínimo=0.000001, 50 movimientos/nivel | Factor=0.99 |
| AS | 20 hormigas, alpha=1, beta=2, rho=0.2, q=1, epsilon=0.05, feromona inicial=1, min=0.1, max=10 | beta=4 |
| ABC | 20 fuentes, limit=50 | limit=200 |
| DE | P=20, F=0.5, CR=0.8 | F=0.8 |
| PSO | 20 partículas, inercia=0.5, c1=c2=1, cota velocidad=0.5 | Inercia=0.8 |

Son 20 ensayos de ajuste por familia (dos candidatos × dos grafos × cinco
semillas), sin rondas adaptativas, ampliaciones ni parada temprana del lote por
buenos resultados. El éxito individual sí detiene su solver. Costo de ajuste
máximo nominal: 200 s de solver y 40,000 evaluaciones por familia.

Con el ajuste conciliado y auditado, elegir por familia el mínimo lexicográfico
`(-S, E, mean(C/n), ordinal)` sobre sus diez primarios por candidato:

- `S`: certificados dentro de presupuesto, según las reglas de éxito siguientes.
- `E`: intentos con error, interrupción externa, JSON ausente/corrupto o evidencia
  contradictoria. Un timeout cooperativo normal no es error.
- `C/n`: mejor costo legal recalculado, dividido entre vértices de su grafo;
  usar 1 si no existe candidato auditable o el intento es error. Éxito aporta 0.
  La media usa las diez celdas con igual peso (cinco por grafo), sin excluir fallos.
- `ordinal`: 1 antes que 2; resuelve todo empate sin mirar tiempos de evaluación.

No seleccionar con ensayos pendientes. Si ambos candidatos de una familia tienen
los diez intentos en error, detener la campaña y corregir mediante revisión previa;
no sustituir la familia ni inventar una ganadora. Con cero éxitos sí se puede
elegir por errores y costo normalizado, declarando esa limitación.

Antes de iniciar **cualquier** ensayo de evaluación o escala, #70 publicará un
artefacto inmutable `freeze.json`, versión `fhcp-benchmark-freeze/1`, con estos
campos obligatorios:

| Campo | Contenido |
| --- | --- |
| `schema_version`, `protocol_id`, `created_at_utc` | Versión, `fhcp-m6-v1` y fecha UTC |
| `config_sha256`, `protocol_sha256` | Hash de bytes del JSON y de esta decisión aceptados |
| `tuning_batches` | Lista de `{batch_id, manifest_path, manifest_sha256}`; incluye todos los ensayos de ajuste |
| `selection` | Seis objetos `{algorithm, config_id, parameters, score}`; score guarda `successes`, `errors`, `mean_normalized_cost`, `ordinal` |
| `code`, `environment`, `seeds_decimal`, `budgets` | Commit limpio y hashes de módulos; perfil real fijado; lista final explícita y límites copiados del plan para evaluación y escala |
| `artifacts` | Rutas relativas y hashes de la tabla de selección y auditoría de ajuste |

Los parámetros finales deben coincidir exactamente con uno de los dos candidatos
por familia y con sus resolvedores. Se conserva el catálogo entero. La regla de
elección, las semillas y los límites quedan fijados **ahora**; únicamente la
identidad de la ganadora depende del ajuste. #70 materializa esos valores efectivos
y registra el hash de `freeze.json` antes de evaluar; no redefine el protocolo.
El ejecutor rechazará evaluación/escala sin congelación completa y coherente.
Ajuste y evaluación usan el mismo commit limpio y perfil de entorno.
Cambiar candidatos, semillas, partición, límites, máquina o regla exige nueva
versión revisada antes de evaluar, conservando intentos y congelaciones anteriores.

## Presupuestos, medición y recursos

El presupuesto admite hasta `max_evaluations` valoraciones de rutas completas,
incluidas inicialización y reinicios. AS puede invertir tiempo en una construcción
sin completar ninguna evaluación; DE/PSO añaden decodificación y sus poblaciones
tienen otros costos. No equiparar contadores de iteración entre familias.
Un `algorithm_stop` de SA conserva su duración y presupuesto no consumido; no se
rellena con trabajo adicional. No se implementan otros operadores para igualar tiempos.

`max_elapsed_ns` usa el reloj monótono del solver e incluye RNG, inicialización,
construcción, evaluación, actualizaciones y certificación. El límite es
cooperativo y se conserva `overrun_ns`. Una certificación válida que termina tarde
no es éxito dentro de presupuesto. La última reserva de evaluaciones puede
certificarse sin otra reserva si respeta el tiempo, conforme al #19.

El supervisor mide 120 s desde lanzar el proceso CLI hasta su salida, incluyendo
carga y guardado; al vencer, termina el proceso y registra causa/señal, tiempo
observado, stdout/stderr y cualquier JSON completo recuperable. No fabrica un
`SolverResult` si falta. El supervisor protege el lote de bloqueos y no es un
presupuesto alternativo para acreditar éxitos; una terminación externa cuenta
como fallo primario aun si hay un candidato parcial. Las operaciones de guardado
del coordinador se miden aparte y no prolongan búsqueda ni certifican soluciones.

| Tiempo guardado | Alcance y unidad |
| --- | --- |
| `timing.preparation_ns` del RunRecord | Configuración, carga verificada y metadatos; no es carga pura |
| `result.timing.solver_ns` | Núcleo completo, con inicialización y certificación |
| `result.timing.validation_ns` | Subintervalo del solver: no sumarlo otra vez |
| `timing.finalization_ns`, `timing.total_ns` | Conversión en memoria y total CLI antes de serializar/escribir |
| `process_elapsed_ns` del manifiesto | Proceso CLI completo, incluidos serialización y guardado CLI |
| `capture_write_ns` del manifiesto | Publicación de stdout/stderr y artefactos por el coordinador, después del proceso |
| `load_ns` del manifiesto | `null` en CLI actual; no llamar carga pura a preparación |

No obtener escritura restando relojes de distinto proceso. El guardado CLI queda
incluido en `process_elapsed_ns`, sin desglose exacto en esta versión. La escritura
del coordinador sí tiene intervalo propio. Valores desconocidos son `null` con
motivo, nunca cero. La auditoría posterior se mide aparte y no reduce el tiempo
original hasta certificado. Un certificado no obtenido en búsqueda no se vuelve
éxito retrospectivo al auditarlo.

Perfil elegido para la campaña: equipo x86_64 con AMD Ryzen 7 7730U, 8 núcleos / 16
hilos lógicos, 16,060,186,624 bytes de RAM física, CachyOS Linux; CPython 3.14.10
estándar con GIL, NumPy 2.5.4 y dependencias de `requirements-dev.txt` (pip 26.3).
Es el recurso disponible para planificar, **no un entorno de campaña ya medido**.
#70 guardará kernel, paquetes/build de Python y NumPy, CPU, RAM física/disponible,
reloj/resolución y política energética reales en la congelación.

Ejecutar conectado a corriente, con política energética constante registrada,
`workers=1`, un único proceso solver activo y afinidad a un único CPU lógico,
elegido y registrado antes del ajuste y mantenido en todas las fases. No cargar
su hermano SMT con otro trabajo. Fijar antes de importar NumPy las cuatro
variables del JSON a `1`; registrar backend NumPy y evidencia de hilos efectivos
mediante inspección del proceso. Si no puede comprobarse un campo, consignarlo
como desconocido y resolverlo antes de comparar tiempos finales. No falsear los
`null` de la CLI: el manifiesto agrega evidencia con fuente y método.
Cerrar cargas de usuario, builds y pruebas concurrentes. Registrar carga del
sistema previa y durante cada proceso y eventos de suspensión/competencia.
Una incidencia conserva el intento y se marca; no se elimina por ser lento.
Si impide condiciones comparables, detener antes del siguiente ensayo y revisar
la campaña. Otra máquina o cambio de versiones define otro estrato de entorno:
no mezclar tiempos ni completar silenciosamente la misma celda con otro equipo.

AS usa `8*n*(n-1)/2` bytes de feromona: graph1001 requiere **363,093,024 bytes**
(aprox. 346.27 MiB), más rutas, objetos Python, grafo y temporales. Es una
estimación analítica del vector, no memoria máxima observada. Se exige al menos
4 GiB disponibles antes de iniciar cada proceso, también en escala; comprobar
ausencia de intercambio activo en el preflight de #70 y registrar RSS máximo de
AS durante la campaña.
El mínimo deja margen sobre el vector, sin garantizar la asignación. Si falta
memoria, no iniciar nuevas celdas ni reducir hormigas/instancia silenciosamente:
revisar el plan. Un `allocation_failed` iniciado permanece en el denominador.
La construcción AS es cuadrática en n y puede consumir 30 s sin completar ruta
en graph1001. Eso es un resultado admisible de escala, no razón para excluirlo.

## Viabilidad prevista

Hay 1,032 ensayos primarios (12 + 120 + 720 + 180) y 12 intentos de verificación:
**1,044 procesos**, antes de reintentos diagnósticos. El techo nominal de solver
con plazo es 60 + 1,200 + 21,600 + 5,400 = **28,260 s (7.85 h)**, más carga,
finalización, escritura, sobrepasos y verificación. No es una cota dura ni una
predicción medida. El supervisor da un cupo nominal de 125,280 s (**34.8 h**) de
procesos incluyendo verificación, más coordinación, auditoría y escritura.
Reservar dos días de máquina disponible y espacio de al menos 1 GiB para crudos y
diagnósticos; comprobar capacidad real antes de la campaña. Las rutas serializadas
suman orden de decenas de MB; no se guardan trayectorias completas. Un diagnóstico
excepcional puede superar esa previsión y debe conservarse o archivarse con hash.
No se presenta esta estimación como rendimiento. El preflight verifica recursos
y humo sin medir ni elegir sobre los grafos de evaluación. Si el cupo no es viable,
proponer revisión antes de la campaña; no recortar repeticiones a posteriori.

## Configuración, identidad y orden — contrato v1

JSON UTF-8 sin NaN, infinito, claves duplicadas ni campos desconocidos; no hay
coerción de tipos. `schema_version` desconocida se rechaza. Rutas relativas a la
raíz del repositorio, sin escapes `..` ni rutas absolutas para artefactos.
El validador de entrada de #68 implementará las obligaciones siguientes; las
pruebas de esta entrega comprueban los valores versionados contra APIs reales.

| Campo del `fhcp-benchmark-config/1` | Tipo / regla |
| --- | --- |
| `protocol_id` | Cadena no vacía; identifica la revisión del plan |
| `dataset_manifest` | `{path, sha256}` de bytes; debe concordar con el cargador |
| `instances` | Lista única de `{id, partition, sha256, dimension, edge_count}`; copia de los nueve miembros del #16 |
| `algorithms` | Lista ordenada exacta `ga, sa, as, abc, de, pso` |
| `configurations` | Lista única de `{config_id, algorithm, family, variant, iteration_unit, parameters}`; dos candidatos por familia, orden c1/c2; todos los parámetros efectivos |
| `phases` | Mapa con las cinco fases; cada una contiene `instances`, `seeds_decimal`, `configuration_source`, `budget`, `external_timeout_ns`, `expected_trials` |
| `budget` de fase | Los tres campos de `Budget`; enteros positivos o null, al menos uno activo; sin booleanos |
| `seeds_decimal` | Lista sin duplicados, cadenas canónicas de enteros entre 0 y 2**64-1; convertir a int solo al invocar el solver |
| `configuration_source` | `candidate_1_per_algorithm`, `all_candidates` o `frozen_selection` según la fase |
| `expected_trials` | Entero positivo, número de identidades, excluidos reintentos y segundo intento de verificación |
| `selection`, `order`, `attempts`, `execution` | Objetos con las claves y valores fijos del JSON v1; cambiar sus reglas requiere nueva versión revisada |

Los campos de ejecución no son parámetros ocultos del algoritmo. #68 reutiliza
`VARIANTS[algorithm].resolve` y la CLI individual; #69 consume contratos sin
depender del coordinador. Esta entrega no añade una entrada de lote provisional.

Se define `J(x)` como `json.dumps(x, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False).encode("ascii")`, sin salto final. Resolver
primero los parámetros (incluidos floats efectivos), sin redondear después.
`configuration_sha256 = SHA256(J({algorithm, family, variant, parameters}))`.

La identidad `trial_id` es el hexadecimal SHA-256 de `J(identity)` con exactamente:
`protocol_id`, `phase`, `instance_id`, `instance_sha256`, `algorithm`, `variant`,
`configuration_sha256`, `seed_decimal`, `budget` (solo los tres límites) y
`external_timeout_ns`. La procedencia de código/entorno se fija en el manifiesto
para todo el lote; otro entorno genera otro lote/estrato, aunque repita trial_id.
El perfil estable incluye CPU, RAM física, SO/kernel, builds/versiones, backend,
afinidad, política energética y hilos; las muestras dinámicas se guardan aparte.
La unidad de unión entre artefactos es `(batch_id, trial_id, attempt_id)`.
Los hashes de archivos usan bytes originales, distintos de estos hashes de JSON
canónico. Todo hash usa SHA-256 hexadecimal minúsculo de 64 caracteres.

Expandir el producto de instancias × candidatos aplicables × semillas.
No barajar con RNG del solver. Dentro de cada fase ordenar por el par
`(SHA256(UTF8(protocol_id + "\n" + phase + "\n" + trial_id)), trial_id)`
lexicográficamente, y asignar `ordinal` desde 0. Se materializa la lista completa
antes de empezar. Igual entrada/congelación produce igual plan y orden.
Ejecutar fases en orden humo, ajuste, evaluación, escala, verificación, con
congelación entre ajuste y evaluación. La reanudación conserva ordinal y atiende
pendientes; no reordena según éxitos. Registrar pausas y fechas para interpretar
posibles derivas térmicas o carga. No se promete eliminar sesgos temporales.

## Manifiesto e intentos — contrato v1 para #68 y #69

Guardar `experiments/results/<batch_id>/manifest.json` antes del primer proceso;
`batch_id` es UUID nuevo. Una fase por lote; evaluación y escala referencian la
misma congelación. El manifiesto lleva `schema_version=fhcp-batch-manifest/1`:

| Campo obligatorio | Contenido |
| --- | --- |
| `batch_id`, `protocol_id`, `phase`, `created_at_utc`, `updated_at_utc` | Identidad y fechas UTC |
| `status` | `planned`, `running`, `incomplete` o `complete` |
| `inputs` | Lista de `{role, path, sha256}` para decisión, config, manifiesto FHCP y congelación cuando aplica; copias conservadas en el lote |
| `code` | Commit completo limpio, `dirty=false`, hashes de implementación, fitness, validador, instrumentación y decodificador cuando aplica |
| `environment` | Perfil real anterior, `environment_id` hash de J del perfil estable (excluye fechas, carga, RAM disponible y RSS); CPU, RAM, SO/kernel, versiones/builds, afinidad, política energética, hilos y métodos de comprobación |
| `expected_trials`, `trials` | Cantidad y lista completa ordenada; ninguna celda se descubre al agregar |
| `artifacts`, `missing_metadata`, `deviations` | Listas de archivos con hashes, campos desconocidos con motivo y desviaciones con evidencia; vacías si no hay |

Cada objeto `trials[]` tiene `trial_id`, `ordinal`, `identity` (la entrada exacta
del hash), `config_id`, `state` y `attempts` inicialmente vacío.
`state` es `pending` (nunca iniciado), `started`, `finished` (proceso terminado y
artefactos conciliados) o `interrupted` (no hay salida terminal fiable).
`finished` no implica éxito. Un error terminal o timeout externo documentado
puede quedar `finished`; se conserva su clasificación propia en el intento.
`complete` exige que cada ensayo tenga primario terminal conciliado (y ambos
intentos en verificación), incluso si fracasó. Nunca iniciar no equivale a error
observado y mantiene el lote incompleto. Un cierre explícito de un intento
interrumpido requiere diagnóstico terminal, sin inventar telemetría.

Antes de lanzar cada proceso, reservar y persistir un UUID `attempt_id` distinto
del `run_id` que la CLI creará, con `state=started`. Cada intento contiene:

- `attempt_id`, `retry_of` (UUID del intento previo o null), `role`
  (`primary`, `diagnostic_retry`, `verification_repeat`), fechas UTC de inicio/fin;
- `command` como lista exacta de argumentos, directorio de trabajo y variables
  aplicadas; `exit_code`, `signal`, `external_timeout` y `diagnostic`;
- `run_id` o null, `record_path` y `record_sha256` o null, rutas/hashes de stdout y
  stderr incluso vacíos; artefactos parciales separados, nunca como JSON completo;
- `process_elapsed_ns`, `capture_write_ns`, `load_ns`, `peak_rss_bytes`, carga
  observada y desconocidos con motivo. Duraciones desconocidas son null;
- `state` (`started`, `finished`, `interrupted`) y `outcome`
  (`success`, `exhausted`, `cooperative_timeout`, `external_timeout`,
  `config_error`, `runtime_error`, `save_error`, `interrupted`, `invalid_evidence`),
  o null mientras está activo.

Usar directorios exclusivos `attempts/<attempt_id>/`, conservar `run.json`
original, stdout, stderr y cualquier diagnóstico. El manifiesto vincula el
`run_id` real con batch/trial/attempt; la CLI actual deja `run.batch_id` y
`run.retry_of` en null. No reescribir esos bytes para completar el enlace; la
relación en el manifiesto es autoritativa y debe ser única. Si se amplía la CLI
en #68, documentar esa evolución conservando `fhcp-run-record/1` compatible.

Para que los artefactos nuevos no falseen `code.dirty`, #68 debe reservar la
carpeta UUID del lote y excluir **solo esa ruta** localmente en `.git/info/exclude`
del checkout de ejecución antes de escribir el manifiesto o invocar la CLI.
Guardar en `code.artifact_exclusion` la ruta, regla exacta y motivo; verificar
árbol limpio antes y después de cada proceso. No excluir código, configuraciones
ni otras rutas. La exclusión no forma parte del commit y no elimina archivos;
#70 conserva y publica el lote explícitamente (la exclusión local puede requerir
agregar esa ruta de forma explícita), sin subir la configuración local de Git.
Los artefactos de lotes anteriores deben estar versionados o excluidos por sus
rutas exactas declaradas, sin ocultar cambios ajenos. El hash solo no sustituye
una copia recuperable: conservar también commit, entradas y fuentes usadas.

Publicar manifiesto y artefactos completos mediante temporal y reemplazo
atómico; conservar revisiones del manifiesto con número creciente y hash de la
anterior bajo `manifest-history/`; no incluir el propio manifiesto actual en
su lista de hashes de artefactos. No truncar registros previos al reanudar.
Un corte entre escribir archivos y actualizar manifiesto exige conciliación por
ID/hash: recuperar el intento reservado, no ejecutar de nuevo sin registrarlo.
Un JSON de stdout recuperado ante fallo de guardado sirve para auditoría, pero
`save_error` sigue siendo fallo primario del pipeline. El código CLI 0 también
significa agotamiento: clasificar con resultado y límites, no solo exit code.

## Éxito, denominadores, faltantes y reintentos

Éxito requiere conjuntamente salida normal sin fallo de guardado, identidad y
hashes coherentes, `status=success`, `success_within_budget=true`, costo cero,
ruta legal con aristas y cierre, `validation.valid=true`, `telemetry_complete=true`,
`first_success` no null, reservas dentro del límite y certificado terminado en
plazo. #70 recertifica todos los éxitos, recalcula costo de todo candidato disponible
y audita mapeo. Contradicciones producen `invalid_evidence`, sin corregir el crudo.
Los detalles de límites y fases siguen #19; no se exige un contador adicional
para certificar la última evaluación admitida.

`exhausted/time_limit` es timeout cooperativo; `overrun_ns` puede ser positivo.
Un certificado tardío conserva factibilidad pero aporta cero éxitos y no recibe
`first_success`. Costo cero sin certificación no basta. Agotamientos de evaluación,
`algorithm_stop`, errores y timeouts permanecen en el denominador. Un agotamiento
no demuestra no hamiltonicidad.

Por celda instancia/familia/configuración/presupuesto/entorno se fija N=30 en
evaluación y escala (N=5 por candidato en ajuste). El **primer intento iniciado**
es el primario irrevocable. No hay reintentos automáticos. Reintentar solo para
diagnóstico, con nuevo UUID y `retry_of`, conservando el original; nunca sustituye
su resultado ni añade una repetición primaria. Verificación tiene dos intentos
predefinidos con roles primary/verification_repeat y no entra en evaluación.
Dos primarios para la misma identidad o un run_id usado por dos intentos es
conflicto, no una oportunidad de elegir el mejor. Copias idénticas por hash se
detectan y se señalan sin contarlas dos veces; conflicto no resuelto bloquea cierre.

Mostrar N previsto, resueltos, pendientes, éxitos, agotamientos, timeouts y errores.
Mientras haya pendientes no publicar una tasa final: mostrar `S/N previsto` como
cota inferior provisional y cobertura `resueltos/N`. No usar solo los completados
como denominador. #70 debe resolver cada celda o revisar alcance de antemano para
cerrar; una campaña parcial no acredita el plan final.

## Agregación acordada para #69

Publicar tablas por instancia y familia con configuración/variante, entorno,
presupuesto, N, S, `100*S/N` (%), y conteos de errores separados por tipo.
Para dispersión de éxito mostrar desviación estándar muestral de los indicadores
binarios `sqrt(N*p*(1-p)/(N-1))` si N>1, con p=S/N; no se presenta como intervalo
de confianza ni como incertidumbre sobre todo FHCP. Con N=1 es N/A.
No se requieren pruebas de significación ni ranking global con este diseño.

Para duraciones con telemetría conocida: n observado/n ausente, media, mediana,
cuartiles Q1/Q3 (interpolación lineal, posición `(n-1)*q`, para q=0.25/0.75) y desviación muestral
(divisor n-1; N/A si n<2), en segundos (`ns/1e9`). Reportar `solver_ns` de **todos**
los primarios con dato, incluidos errores, y `process_elapsed_ns` aparte para todos
los procesos; no sumar sus medias ni imputar ceros. Preparación, validación,
finalización y escritura tienen sus propios tamaños de muestra y alcance.
Reportar sobrepasos y máxima memoria observada; no confundir RSS con feromona.

Tiempos hasta éxito usan exclusivamente `first_success.elapsed_ns`: n=S,
media/mediana/cuartiles/desviación por separado, N/A si S=0. No son tiempo esperado
incondicional para resolver. Informar censura temporal en el plazo solver de
la fase (5, 10 o 30 s) para timeouts cooperativos, aunque el proceso sobrepase; en el supervisor, marcar
censura al tiempo de proceso observado en una columna de alcance diferente,
sin convertirlo a tiempo solver desconocido. Agotamiento de evaluaciones censura
en presupuesto de evaluaciones (tiempo consumido disponible, sin asumir que habría
seguido buscando); `algorithm_stop` es terminación sin éxito. Errores se muestran
aparte, sin tratarlos como censura administrativa ni ajustar supervivencia.
No se estima una mediana global de tiempo hasta solución con solo éxitos.

Guardar evaluaciones iniciadas/completadas y su partición, validaciones, reinicios,
iteraciones con unidad, fases parciales y contadores por familia definidos en sus
decisiones. Nunca sumar generaciones con movimientos o ciclos ABC como trabajo
común. Graficar tasas y distribuciones de tiempos con unidades y N; escala va en
panel separado. Cada análisis crea un directorio nuevo con versión, configuración
y hashes de entradas, y una tabla de procedencia por intento para regeneración.

Precisión, recall y F1 son **N/A para esta tarea de búsqueda**, conforme al #6:
no hay clase negativa FHCP y no encontrar certificado no es predecir inexistencia.
Comparar posiciones/aristas contra un único tour también rechazaría ciclos válidos
alternativos. No se crean TP/FP/FN/TN artificiales. Una auditoría del validador
con casos sintéticos etiquetados es otra tarea y no una métrica de esta campaña.

## Consecuencias y entrega

El plan consume tiempo acotado de máquina y conserva fallos a costa de archivos y
metadatos adicionales. El corte combinado no garantiza trayectorias iguales ni
igual CPU por evaluación. Se limita a seis variantes, nueve instancias y ajuste
local mínimo; cero éxitos es un resultado posible. No se extrapola superioridad.

La prueba de reproducción predefinida usa graph1, semilla 17, cada ganadora,
100 evaluaciones y dos procesos, sin plazo cooperativo; compara ruta, costo,
estado y contadores, excluyendo identidades y tiempos. Los ensayos se conservan
separados. Si se quisiera repetir una trayectoria temporal de evaluación, solo
puede contrastarse con cautela: no se promete el mismo punto de corte.

Las referencias técnicas de variantes, datos y métricas son las decisiones e
investigaciones locales enlazadas arriba; no se introducen nuevas cifras de una
publicación externa. El contraste con fuentes primarias y cierre de M6 pertenece
al #71; LaTeX, a M7. Los comandos comprobados para revisar este plan están en
[README](../../README.md#protocolo-del-benchmark-m6). Ejecutar el lote, congelar
sus ganadoras y medir recursos sigue pendiente de #68–#70. Integrar #67 no cierra M6.

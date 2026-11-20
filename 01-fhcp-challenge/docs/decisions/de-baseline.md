# DE/rand/1/bin sobre claves reales

## Contexto y elección

El [issue #53](https://github.com/ZapataFrame/FHCP-Challenge/issues/53), a cargo de Diego Eduardo Zapata Aguilar · @ZapataFrame, implementa la adaptación del [#2, §7.5](../research/metaheuristics.md#75-adaptación-propuesta-a-fhcp). Su dependencia #49 se integró mediante la PR #58. Se reutilizan el [decodificador de claves](real-key-decoder.md), el [costo entero](fitness.md) y el [control de ejecución](solver-and-result-contracts.md#api-de-ejecución-secuencial-del-39).

La variante `rand_1_bin_real_keys_v1` usa población congelada, cruce binomial y selección por mejora estricta. La base de DE se describe en Kochenderfer y Wheeler, *Algorithms for Optimization*, primera edición, §9.3, p. 157, ya citado en la investigación del #2. Storn y Price describen donantes distintos, mutación, coordenada obligatoria y selección en su artículo original, §2, pp. 344–345. La aplicación de esas operaciones a claves de rutas hamiltonianas es una adaptación del proyecto. [Libro de los autores](https://algorithmsbook.com/optimization/) · [Storn y Price, 1997](https://sci2s.ugr.es/sites/default/files/files/Teaching/GraduatesCourses/Metaheuristicas/Bibliography/DE-Storn-Price-1997.pdf).

## API y parámetros

Desde `src.algorithms` se importan `DE_VARIANT`, `DEConfigurationError`, `resolve_de_parameters(parameters)` y `solve_de(graph, *, parameters, seed, budget, clock=perf_counter_ns) -> SolverResult`.

| Parámetro obligatorio | Dominio |
| --- | --- |
| `population_size` | Entero Python de al menos 4. |
| `differential_weight` | F, número Python finito y positivo representable como `float`. |
| `crossover_rate` | CR, número Python finito en `[0,1]`. |

El resolvedor copia la configuración y normaliza F y CR a `float`. Comprueba mapa, claves de texto, claves desconocidas en orden lexicográfico, presencia de las tres claves y sus dominios en el orden de la tabla. Rechaza booleanos, escalares NumPy y conversiones implícitas desde texto. `DEConfigurationError` expone `code` y `parameter`, con códigos `invalid_parameters`, `unknown_parameter`, `missing_parameter` e `invalid_parameter`.

El solver convierte ese rechazo en `error / invalid_config` antes de llamar a `start_run`, que valida grafo, semilla y presupuesto. La configuración efectiva permanece estable durante la ejecución. Los tres parámetros son obligatorios para registrar explícitamente cada configuración utilizada.

## Estado, operaciones y aleatoriedad

1. Inicializar cada vector con `run.rng.random(n)`, de tipo `float64`, uniforme en `[0,1)`. Decodificar y evaluar cada vector una vez, en orden de población. Guardar juntos una copia de sus claves, su ruta inmutable y su costo.
2. Abrir una generación y preparar la población siguiente. La población anterior permanece congelada durante todos los objetivos.
3. Para el objetivo i, extraer tres índices con `rng.choice(P-1, size=3, replace=False)`. Los índices mayores o iguales a i se incrementan en uno para excluir el objetivo. El orden obtenido identifica a, b y c.
4. Calcular el donante `z = x_a + F*(x_b-x_c)` sobre las claves. Extraer la coordenada obligatoria con `rng.integers(n)` y después n uniformes con `rng.random(n)`. El hijo toma z donde el uniforme es menor que CR o en la coordenada obligatoria. El resto procede del objetivo. Se generan los n uniformes también con CR igual a cero o uno.
5. Decodificar y solicitar una evaluación de la ruta, incluso cuando coincida con otra ya valorada. Una mejora estricta sustituye al objetivo en la población siguiente, conservando juntos claves, ruta y costo. Un empate conserva el objetivo.
6. Tras terminar todos los objetivos y comprobar el tiempo, sustituir la población anterior y completar la generación.

Todos los sorteos usan el PCG64 privado del intento. El decodificador aplica el desempate por índice. `SolverRun` conserva por copia la mejor ruta evaluada y mantiene la primera en empate. El resultado público conserva el esquema `fhcp-solver-result/1`; las claves forman parte del estado interno de DE.

## Política numérica y consecuencias

Las claves actualizadas pueden ser finitas fuera de `[0,1]`, conforme a la propuesta del #2. El hijo se construye en un arreglo nuevo y las poblaciones conservan sus claves por copia. F admite todo valor finito positivo, como exige el issue. Valores grandes pueden agotar el rango de `float64`.

La mutación usa `numpy.errstate(over="raise", invalid="raise", under="ignore")`. Un desbordamiento o una operación inválida produce `error / non_finite_state` antes de decodificar o reservar otra evaluación. El contexto restaura la política numérica del llamador. El subdesbordamiento redondea a valores finitos, incluido cero. Un `KeyDecodingError` no finito conserva su código y posición en el diagnóstico. Otros errores del decodificador se contextualizan como `runtime_error`. Los errores inesperados conservan tipo, fase y mejor histórico sin incluir el mensaje original de la excepción.

La selección estricta puede inmovilizar vectores que produzcan rutas de igual costo. Distintas claves pueden decodificar la misma permutación y la coordenada obligatoria puede heredar el mismo valor que ya tenía el objetivo. Cada propuesta sigue consumiendo una evaluación. La población y las claves requieren memoria auxiliar `O(P*n)`; la decodificación añade `O(n log n)` comparaciones por propuesta. Estas cotas describen operaciones, no mediciones de rendimiento.

## Presupuesto y certificación

La inicialización abre `initialization` con P elementos. Cada generación abre `generation` con P propuestas y `iteration=True`. Un elemento cuenta tras terminar su evaluación. Una generación cuenta únicamente después del reemplazo completo. Una generación interrumpida conserva su avance y el mejor candidato ya evaluado.

Hay comprobaciones de admisión antes de cada vector inicial y objetivo, y antes de decodificar su vector. `run.evaluate` comprueba el límite de nuevo antes de reservar y valorar. Antes de seleccionar un superviviente y antes del reemplazo final se comprueba el tiempo. La última evaluación admitida puede terminar selección y reemplazo con el tiempo disponible. La siguiente admisión detecta los límites de evaluaciones o iteraciones sin reservar otra valoración.

Todo costo cero se certifica inmediatamente mediante `certify_best`, incluida la última reserva. El certificado deja la fase abierta, con la propuesta evaluada. Se conservan éxito dentro del presupuesto, certificación pendiente al alcanzar el límite, certificado válido tardío y discrepancia del fitness. El reloj es cooperativo; muestreo, operaciones NumPy, decodificación, evaluación y certificación pueden sobrepasar el límite dentro de una llamada. El resultado registra ese sobrepaso.

## Verificación y alcance

Las pruebas usan operadores reales y decisiones controladas para contrastar ecuaciones, donantes, cruce obligatorio, asociación de claves/ruta/costo, selección congelada, empates, desbordamientos, fases parciales, errores y certificación independiente. Comparan trayectoria y resultado con igual semilla y presupuesto de evaluaciones en un entorno fijo y comprueban el aislamiento del RNG global.

Los [comandos del README](../../README.md#evolución-diferencial-sobre-claves-reales) permiten repetir las comprobaciones. La evidencia de plataforma, commit y salidas se registra en la PR. La integración de DE en la CLI corresponde al #55 y la comprobación conjunta de M5 al #56. Los parámetros de los ejemplos son didácticos. Los ajustes y comparativas pertenecen a M6.

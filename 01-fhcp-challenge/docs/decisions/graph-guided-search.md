# Variantes exploratorias con información del grafo

## Contexto

El responsable solicitó incorporar inicialización voraz y movimientos guiados
tras comparar la campaña M6 con scripts y resultados de otro equipo. El ZIP de
scripts recibido no incluye el módulo `core`; por ello no se afirma reproducir
su inicialización o sus deltas. Se implementan los operadores descritos aquí
con nuestras estructuras, PCG64 y control de ejecución. La revisión v2 no incorpora
deltas ni recalentamiento; esas extensiones posteriores se describen en
[las mejoras v3](search-enhancements.md). Ninguna revisión redefine el protocolo M6.

Los 1,044 procesos de M6 y la prueba posterior de graph2 son evidencia de las
variantes anteriores. Sus configuraciones, semillas, límites y archivos se
conservan. El contraste y cierre de M6 pertenecen al #71; estas mejoras tienen
alcance independiente y no se agregan a su PR.

## Elección

Las nuevas políticas son explícitas y opcionales. Sin sus argumentos se conserva
la trayectoria aleatoria anterior; los candidatos aceptados de benchmark-v1/v2/v3
mantienen sus opciones y valores. No se añaden defaults a los JSON congelados.

| Familia | Opciones nuevas |
| --- | --- |
| GA, SA, ABC | `initialization=uniform/greedy`; `guided_move_rate` entre 0 y 1 |
| DE, PSO | `initialization=uniform/greedy` |
| AS | `construction=all_vertices/neighbor_guided` |

Con `greedy` se inicia en un vértice uniforme. Se continúa por un vecino real no
visitado con menor número de vecinos todavía no visitados; los empates se sortean
sobre el orden estable de CSR. Si hay bloqueo, se elige uniformemente un vértice
restante y se registra `greedy_jumps`. No se repara el cierre ni se garantiza un
ciclo. La construcción conserva una permutación completa o se interrumpe sin
atribuir fitness a un prefijo. Las exploradoras de ABC usan la misma política.
En DE/PSO esa permutación se codifica como claves de rango distintas en [0,1),
conservando su orden al decodificar; no se redondean índices de vértices.

La inversión guiada elige un ancla y uno de sus vecinos reales que todavía no
sea consecutivo en la ruta cíclica. Invierte el segmento que los hace adyacentes.
No modifica la entrada ni introduce vértices repetidos. Crear una arista real
puede destruir otras: cada candidato se evalúa completo y conserva las reglas de
aceptación existentes. Sin vecino elegible, la propuesta es un no-op evaluado y
contabilizado. En GA, la tasa guiada se aplica dentro de la mutación ya admitida;
en SA/ABC se aplica a cada propuesta. El complemento usa el operador anterior
(swap en GA/SA, intercambio guiado por otra fuente en ABC). No se agregan
inversiones aleatorias ni aceptación de empates en ABC.

En AS, `neighbor_guided` limita candidatos a vecinos reales no visitados y usa
pesos proporcionales a `tau**alpha / (1 + remaining_degree)**beta`. Cuando hay
bloqueo salta uniformemente a un vértice restante y registra
`neighbor_guided_jumps`. Conserva el almacenamiento de feromona para todos los
pares y su actualización previa, incluidos pares ausentes, en el modo v2. No implementa la variante MAX-MIN del
otro equipo. El almacenamiento disperso posterior es una opción v3 independiente.

La inicialización y la guía comprueban el presupuesto durante sus bucles. Cada
candidato completo consume una evaluación y el éxito sigue requiriendo costo
cero más certificación independiente dentro del presupuesto. No hay acceso a
archivos, CLI, tours oficiales o RNG global desde estos operadores.

## Contrato y procedencia

La CLI admite `--initialization`, `--guided-move-rate` y `--construction` según
familia. Los parámetros efectivos se guardan completos en RunRecord. Cuando se
activa una política nueva, `procedure.variant` termina en `_graph_guided_v2` y
`procedure.initialization` describe la construcción. El campo opcional
`procedure.search_operator_version` conserva el SHA-256 de `graph_guidance.py`,
además de los hashes de implementación, fitness y validador existentes.

`uniform`, `all_vertices` y una tasa cero preservan los identificadores v1.
Solicitar un nombre de variante incompatible con los parámetros es un error.
Las opciones exploratorias se distinguen de `Variant.options`, que describe los
parámetros congelados de M6, mediante `Variant.optional_options`.

Los [presets exploratorios](../../experiments/configs/graph-guided-v2-presets.json)
reutilizan los parámetros numéricos seleccionados de M6 y añaden las políticas
nuevas: tasa 0.5 en GA/SA/ABC. Son una configuración para pruebas individuales,
no un plan aceptado por `benchmark_campaign` ni un ajuste de parámetros nuevo.
Para reproducir la campaña anterior debe usarse su checkout original y entorno;
los hashes de los módulos de esta entrega son distintos aunque las políticas
anteriores sigan disponibles.

## Verificación y limitaciones

La suite `tests/test_graph_guidance.py` cubre permutaciones, aristas creadas,
bloqueos, entradas inválidas, codificación de claves, reproducibilidad, límite
de evaluaciones, interrupciones temporales, éxito en la última evaluación,
compatibilidad de políticas anteriores y procedencia CLI para las seis familias.
Las pruebas de éxito usan ciclos sintéticos; no son mediciones FHCP.

Una comprobación local de integración usa graph2, semilla 1001, 10,000
evaluaciones o 5 segundos por familia, con RunRecord y recálculo independiente.
Sus registros quedan en `.tools/graph-guided-v2-check/`; es una comprobación
exploratoria de una semilla y no una nueva campaña. No permite afirmar
superioridad, tasas de éxito ni extrapolar a los 1001 grafos. La comparación con
múltiples semillas y presupuestos fijados queda pendiente de una campaña separada.

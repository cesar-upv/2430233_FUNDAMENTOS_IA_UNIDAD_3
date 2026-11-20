# Cierre de la evaluación distribuida FHCP · corte del 17 de noviembre de 2026

**Responsable de consolidación:** Junior Arturo Vázquez Leonel · @Arturo2430.
Seguimiento: [#94](https://github.com/ZapataFrame/FHCP-Challenge/issues/94).

Se recuperaron las cinco entregas y se certificaron **14 grafos distintos** en
**7,383 intentos**: 300 éxitos por intento, 7,071 agotamientos y 12 incidencias
conservadas. No hubo timeouts externos. Se evaluaron 125 grafos: 121 con las
60 combinaciones conciliadas y cuatro parciales. Los 876 restantes no se
iniciaron en los paquetes entregados. Hay 52,677 combinaciones pendientes de
la reserva original de 60,060; no se contabilizan como fallos.

## Expectativa y decisión de cierre

Arturo indicó al cerrar esta entrega que **se esperaban aproximadamente 20
grafos resueltos** y pidió aceptar el corte actual. El resultado medido es 14,
seis menos que esa referencia aproximada. Esa expectativa se registra con su
procedencia al cierre, sin presentarla como una hipótesis preregistrada.
La meta original del plan era 60 y tampoco se alcanzó. El plan, semillas,
presupuestos y datos originales se conservan intactos.

Se cierra **esta entrega parcial**, sin ejecutar búsquedas adicionales ni
completar las combinaciones restantes. Los cuatro grafos parciales se incluyen
con sus resultados disponibles, sin imputaciones ni reintentos; la tabla de
comparación con cobertura balanceada se limita a los 121 grafos completos.
Los pendientes quedan como reserva fuera del alcance de esta entrega, sin
compromiso de otra etapa. Esta decisión se registra en
[cierre de alcance](../decisions/distributed-evaluation-cutoff.md).

## Resultados certificados

`graph2`, `graph6`, `graph10`, `graph14`, `graph18`, `graph23`, `graph27`,
`graph31`, `graph56`, `graph72`, `graph79`, `graph90`, `graph96`, `graph150`.

Un mismo grafo resuelto por varias semillas o familias cuenta una sola vez.
La validación volvió a comprobar permutación, aristas consecutivas y cierre,
además de costo, presupuesto, identidad, parámetros y hashes del código.
Agotar el presupuesto no demuestra que el grafo carezca de ciclo.

[Tablas por integrante, algoritmo y cada grafo iniciado](../../experiments/results/team-evaluation-20261117/tables.md).
[CSV de los 1001 grafos, incluidos los no iniciados](../../experiments/results/team-evaluation-20261117/by-graph.csv).
[Resultados por algoritmo y equipo](../../experiments/results/team-evaluation-20261117/by-algorithm.csv).
[Una fila por intento](../../experiments/results/team-evaluation-20261117/attempts.csv).
[Totales y hashes](../../experiments/results/team-evaluation-20261117/totals.json).

## Protocolo y equipos

Código de ejecución `19ac5eaa46fbacc5a034dae6d14befbf171928db`;
plan UUID `45f464ae-50be-441b-b7ff-a261fba5028e`, SHA-256 canónico
`348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.
GA, SA, AS, ABC, DE y PSO; semillas 1001–1010, hasta 60 s por solver
incluida inicialización/validación y hasta 120 s externos incluyendo carga
/arranque, sin límite de evaluaciones ni iteraciones. Una búsqueda a la vez
por equipo; hilos nativos fijados a uno. Todos los perfiles registran
CPython 3.14.10 estándar con GIL, 64 bits y NumPy 2.5.4.

| Integrante | CPU declarada en la entrega | RAM física (GiB) | Sistema |
| --- | --- | ---: | --- |
| Arturo | Intel Core i5-12450H | 31.01 | CachyOS Linux 7.2.9 |
| Zapata | Intel Core i5-1334U | 15.30 | CachyOS Linux 7.3.1 |
| César | AMD Ryzen 7 7730U | 14.96 | CachyOS Linux 7.3.3 |
| Eder | AMD Ryzen 5 4600G | 21.31 | Debian 13, Linux 6.12.113 |
| Elías | AMD Ryzen 5 7535HS | 15.21 | Windows 11, compilación 26300 |

La CPU y RAM completas proceden de la preparación/issue de cada integrante;
los perfiles automáticos de algunos equipos Linux tienen el campo CPU vacío.
[Perfiles y sesiones originales](../../experiments/results/team-evaluation-20261117/machines-and-sessions.json)
conserva esa distinción. No se normalizan tiempos entre máquinas.

Las duraciones de 7,381 procesos están disponibles; dos interrupciones de
Zapata carecen de esa medición. Suman 427,237.302 s (118.677 h) **de procesos
entre todos los equipos**, incluyendo arranque/carga y procesos censurados.
No es duración calendario ni tiempo exclusivo de solver. Las tablas explicitan
el número de duraciones disponibles y separan equipo y algoritmo; sus medias
no representan tiempo medio hasta resolver.

## Cobertura parcial e incidencias

| Integrante | Grafo parcial | Intentos | Pendientes |
| --- | --- | ---: | ---: |
| Arturo | graph185 | 17/60 | 43 |
| Zapata | graph104 | 5/60 | 55 |
| César | graph153 | 53/60 | 7 |
| Eder | graph106 | 48/60 | 12 |

Se conservan tres interrupciones de Arturo, seis de Zapata, dos de César y
una de Eder, sin reintentos ocultos. Se incluyen en todos los denominadores
correspondientes. Las tablas identifican cada intento con miembro, grafo,
algoritmo y semilla; los casos sin costo/tiempo se mantienen sin inventar datos.

El corte de Elías concilia 600 resultados. El inicio posterior de
`graph57-ga-1001` quedó fuera de su ZIP y de esta agregación, como documentó
su entrega: no se contabiliza como resultado admitido ni se certifica aquí.
Los registros originales permanecen con el responsable. Los resúmenes de
sesión de ese paquete llegan a 570 y falta el historial de la primera sesión
por el error de longitud de ruta de Windows ya documentado. Los 600 primarios
sí se recuperaron y validaron; se usa su tiempo de proceso disponible y no
se presenta la suma de historiales de sesión como duración total.
El historial inicial de Zapata tampoco cubre de forma completa todos los
procesos previos a su recuperación. Se conservan ambos historiales sin
reconstruir duraciones que no estén medidas.

## Integridad, recuperación y procedencia

Se comprobó SHA-256 de los cinco ZIP contra sus entregas, CRC e inventario
sin entradas repetidas, enlaces simbólicos ni rutas fuera del destino.
Después de extraer en directorios separados, `combine` oficial releyó los
7,383 intentos y recertificó sus candidatos contra las instancias originales.
Las celdas recalculadas de cada integrante coinciden exactamente con su
`summary.json` original; no hay miembros ausentes ni combinaciones duplicadas.
El resultado fue:

```text
7383/60060; éxitos=300; grafos distintos resueltos=14; errores=12
```

[Manifiesto de paquetes, enlaces y hashes](../../experiments/results/team-evaluation-20261117/packages.json).
Los ZIP de Arturo y Zapata están en el repositorio; los de César, Eder y
Elías están en sus carpetas de Drive. Los respaldos históricos y las entregas
previas se mantienen separados. No se modificaron los ZIP ni los primarios.

| Integrante | Intentos | Archivos del ZIP | SHA-256 |
| --- | ---: | ---: | --- |
| Arturo2430 | 2417 | 14547 | `def1148bfd3b676f29f42634668dbb25147fbbc89397f8c89be3432b87958cbc` |
| ZapataFrame | 1325 | 7997 | `a56c43a7949c2633d6096ae8c6420c82beb0f4f7db9c5a9ab43404182c4415f0` |
| cesar-upv | 1853 | 11163 | `cb25bbcddbd480b758f82dabd59eb27d97178d0a18beab2de47d2f3136800fca` |
| KirbyStone69 | 1188 | 7190 | `27be57458f2b653af83a3e7d1170af44bbac327ff88c0373965eb3d19ae9027d` |
| ELIASDEJESUSZUNIGADELEON | 600 | 3654 | `5d02eb32701b6999a3ee54948321dbbc32b4447440348c84c9720a63aade3721` |

## Reproducción

El [ZIP de agregación](../../experiments/results/team-evaluation-20261117/combined-evidence.zip)
contiene las salidas oficiales: plan, inventario de entradas/auditorías,
filas por intento y tres resúmenes. Para regenerar las tablas descriptivas,
desde la raíz del repositorio, elegir destinos que aún no existan:

```bash
cd experiments/results/team-evaluation-20261117
sha256sum -c combined-evidence.zip.sha256
cd ../../..
python -m zipfile -e experiments/results/team-evaluation-20261117/combined-evidence.zip /tmp/fhcp-combined-restored
python experiments/analysis/summarize_distributed_evaluation.py \
  --combined /tmp/fhcp-combined-restored/combined \
  --packages experiments/results/team-evaluation-20261117/packages.json \
  --output /tmp/fhcp-tables-reproduced
```

Este script produce tablas desde registros ya auditados; no sustituye la
recertificación de primarios. Para repetir esta última, preparar el entorno y
dataset del commit de ejecución fijado (README), recuperar los cinco ZIP del
manifiesto, verificar sus SHA-256, extraer cada uno en una carpeta distinta y
usar los directorios que contienen `machine.json`:

```bash
python -m src.cli.distributed_campaign combine \
  --plan experiments/configs/distributed-fhcp-10x60.json \
  --inputs /tmp/fhcp-inputs/Arturo2430/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-Arturo2430 \
  /tmp/fhcp-inputs/ZapataFrame/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ZapataFrame \
  /tmp/fhcp-inputs/cesar-upv/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-cesar-upv \
  /tmp/fhcp-inputs/KirbyStone69/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-KirbyStone69 \
  /tmp/fhcp-inputs/ELIASDEJESUSZUNIGADELEON/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ELIASDEJESUSZUNIGADELEON \
  --output /tmp/fhcp-combined-revalidated
```

Las rutas de `/tmp/fhcp-inputs/` representan la extracción local de cada ZIP,
no rutas incluidas en Git. Los comandos oficiales `combine` y regeneración
fueron ejecutados con los destinos equivalentes de la revisión. La identidad
de las entradas se comprueba con hashes; las rutas absolutas del inventario
oficial identifican la auditoría realizada y cambian al repetirla en otro equipo.

## Interpretación y límites

La tasa observada por intento es 300/7,383 = **4.06 %**, incluidos errores.
Son 14/125 grafos iniciados (11.2 %); entre los 121 con cobertura completa,
14 tienen ciclo certificado. No son tasas del conjunto completo de 1001:
la selección consiste en prefijos de las colas asignadas y no es representativa.
Los cuatro grafos parciales tienen cobertura desigual y se conservan aparte
de la comparación balanceada. Las tablas por algoritmo registran éxitos y
costos bajo estos presupuestos, sin inferir ausencia de ciclo ni superioridad
general. Ni el cierre de #94 ni el de las asignaciones individuales completan
por sí solos M6, el informe académico o la meta original.

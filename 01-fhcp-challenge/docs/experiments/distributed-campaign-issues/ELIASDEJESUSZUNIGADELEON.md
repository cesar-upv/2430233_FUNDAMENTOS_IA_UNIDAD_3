## Overview

**Evaluación experimental FHCP.** Ejecutar por sesiones los grafos asignados a @ELIASDEJESUSZUNIGADELEON, conservar los resultados originales de los seis algoritmos y subir la entrega final a su carpeta de Drive.

- **Responsable:** @ELIASDEJESUSZUNIGADELEON · Elías de Jesús Zúñiga de León
- **Hito:** evaluación experimental posterior a M6; seguimiento separado de #71. Sin milestone nuevo.
- **Depende para inicio de:** instalación y comprobación del equipo con la revisión fijada.
- **Versión fijada:** commit `19ac5eaa46fbacc5a034dae6d14befbf171928db`. Usar esta revisión de código y el plan compartido durante toda la evaluación.
- **Plan compartido:** `experiments/configs/distributed-fhcp-10x60.json`; UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`. No regenerarlo ni editarlo.
- **Protocolo:** GA, SA, AS, ABC, DE y PSO; 10 semillas (1001–1010); hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones. Termina antes si encuentra un ciclo certificado. Cupo externo: 120 s por proceso, incluidos arranque y carga.
- **Cola asignada:** 195 grafos, 11,700 intentos si se agota. Cada grafo completo representa 60 intentos y hasta 60 min de búsqueda, más sobrecarga. Toda esta cola supone hasta 195 h de búsqueda; es un techo de presupuesto, no tiempo medido.
- **Objetivo del equipo:** 60 grafos **distintos resueltos y certificados entre todos**. La cola es una reserva: no se exige recorrerla completa si se alcanza el objetivo. Resolver el mismo grafo con varias semillas o algoritmos cuenta una sola vez.
- **Entrega final:** [FHCP-results / FHCP-evaluation / Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut). Esta carpeta ya existe en el Drive institucional de Arturo y el equipo tiene permiso de edición.

### Grafos asignados

El ejecutador usa automáticamente esta lista, en este orden; no hay que introducir los IDs manualmente. No ejecutar los grafos de otro integrante.

`graph5`, `graph10`, `graph15`, `graph21`, `graph26`, `graph30`, `graph35`, `graph41`, `graph46`, `graph52`, `graph57`, `graph59`, `graph64`, `graph69`, `graph75`, `graph81`, `graph84`, `graph92`, `graph97`, `graph102`, `graph107`, `graph109`, `graph119`, `graph124`, `graph127`, `graph128`, `graph131`, `graph135`, `graph137`, `graph139`, `graph143`, `graph144`, `graph156`, `graph157`, `graph164`, `graph174`, `graph175`, `graph184`, `graph189`, `graph195`, `graph196`, `graph200`, `graph201`, `graph209`, `graph221`, `graph230`, `graph233`, `graph234`, `graph243`, `graph255`, `graph258`, `graph261`, `graph263`, `graph276`, `graph282`, `graph289`, `graph290`, `graph294`, `graph296`, `graph300`, `graph304`, `graph319`, `graph321`, `graph326`, `graph328`, `graph335`, `graph343`, `graph346`, `graph350`, `graph363`, `graph366`, `graph369`, `graph373`, `graph375`, `graph380`, `graph387`, `graph388`, `graph394`, `graph400`, `graph404`, `graph411`, `graph418`, `graph420`, `graph434`, `graph445`, `graph447`, `graph456`, `graph458`, `graph460`, `graph467`, `graph469`, `graph470`, `graph473`, `graph474`, `graph476`, `graph477`, `graph483`, `graph493`, `graph514`, `graph517`, `graph532`, `graph550`, `graph556`, `graph559`, `graph560`, `graph568`, `graph571`, `graph574`, `graph577`, `graph583`, `graph589`, `graph590`, `graph592`, `graph597`, `graph599`, `graph603`, `graph613`, `graph621`, `graph632`, `graph634`, `graph635`, `graph643`, `graph654`, `graph655`, `graph661`, `graph662`, `graph664`, `graph674`, `graph682`, `graph692`, `graph697`, `graph701`, `graph702`, `graph703`, `graph704`, `graph709`, `graph722`, `graph730`, `graph737`, `graph739`, `graph740`, `graph742`, `graph747`, `graph748`, `graph753`, `graph755`, `graph756`, `graph761`, `graph773`, `graph777`, `graph779`, `graph784`, `graph790`, `graph792`, `graph795`, `graph798`, `graph800`, `graph801`, `graph805`, `graph816`, `graph819`, `graph832`, `graph833`, `graph834`, `graph837`, `graph841`, `graph843`, `graph845`, `graph858`, `graph867`, `graph870`, `graph876`, `graph885`, `graph886`, `graph890`, `graph895`, `graph907`, `graph915`, `graph918`, `graph930`, `graph933`, `graph945`, `graph947`, `graph948`, `graph954`, `graph957`, `graph958`, `graph968`, `graph978`, `graph980`, `graph984`, `graph989`, `graph993`, `graph994`, `graph995`

### 1. Preparación

Instalar Git y **CPython 3.14.10 estándar, con GIL, x86_64**, según el [entorno documentado](https://github.com/ZapataFrame/FHCP-Challenge#entorno-de-desarrollo). Usar un checkout nuevo para preservar otros trabajos. Ejecutar cada comando por separado y detenerse ante errores.

Estos comandos Git sirven en Linux y PowerShell:

```text
git clone -c core.autocrlf=false https://github.com/ZapataFrame/FHCP-Challenge.git FHCP-evaluation-ELIASDEJESUSZUNIGADELEON
cd FHCP-evaluation-ELIASDEJESUSZUNIGADELEON
git fetch origin 19ac5eaa46fbacc5a034dae6d14befbf171928db
git checkout --detach 19ac5eaa46fbacc5a034dae6d14befbf171928db
git rev-parse HEAD
git status --short
```

El commit debe coincidir y no deben existir modificaciones de fuentes ni del plan. No actualizar el código durante la evaluación. El checkout contiene las instancias originales; no hacen falta tours ni LKH.

Linux, con `python3.14` apuntando a la versión exacta indicada:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip --isolated install --only-binary=:all: pip==26.3
.venv/bin/python -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q -W error tests/test_distributed_campaign.py
.venv/bin/python -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member ELIASDEJESUSZUNIGADELEON
```

Windows PowerShell, con el lanzador `py` seleccionando CPython 3.14.10 estándar de 64 bits:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: pip==26.3
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -W error tests/test_distributed_campaign.py
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member ELIASDEJESUSZUNIGADELEON
```

`check` valida versiones, fuentes, catálogo y hashes de todos tus grafos, sin lanzar solvers; si falla, conservar el error y comentarlo aquí antes de iniciar. Adjuntar su salida y las pruebas al issue, junto con CPU, RAM y sistema operativo. Las pruebas usan grafos sintéticos y no cuentan como resultados FHCP.

### 2. Ejecutar y reanudar por sesiones

Primera sesión de hasta 60 min, más el proceso que ya esté activo. Linux:

```bash
systemd-inhibit --what=sleep:idle --mode=block --why="Evaluación experimental FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member ELIASDEJESUSZUNIGADELEON --max-session-minutes 60
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member ELIASDEJESUSZUNIGADELEON --max-session-minutes 60
```

Repetir **el mismo comando** para continuar desde los pendientes. El límite de sesión no reduce los 60 s de cada intento ni las 10 semillas. Código de salida 3 significa pausa con pendientes; código 0 significa que se recorrió toda la cola, incluso si hubo errores. No significa que todos los grafos se resolvieron.

Mantener el mismo equipo y entorno, un proceso a la vez, laptop conectada, terminal abierta y tapa abierta. Windows inhibe la suspensión por inactividad durante la ejecución; Linux usa `systemd-inhibit`. No apagar ni suspender manualmente. Si se interrumpe, reanudar sin borrar archivos ni repetir primarios. Los intentos interrumpidos quedan como incidencias; informar errores, timeouts y pausas por recursos.

Tras cada sesión comentar aquí: grafos con los 60 intentos ya conciliados, grafos distintos certificados, intentos realizados/pendientes, errores y ruta de resultados. Una sesión puede pausar a mitad de grafo: completarlo en las siguientes antes de darlo por terminado. El equipo revisará el total global; al alcanzar 60 resueltos, coordinar la parada y completar las combinaciones de algoritmos/semillas del grafo iniciado. No hay parada global automática.

### 3. Tablas, logs y entrega final en Drive

Los resultados quedan en `experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ELIASDEJESUSZUNIGADELEON/`: `terminal.log`, `plan.json`, perfil de máquina, snapshot de fuentes, historial de sesiones, `attempts/` con rutas originales/RunRecords, stderr y auditorías, y `summary.md`, `summary.csv`, `summary.json`. Las tablas se actualizan cada 25 intentos y al terminar cada sesión. Conservar éxitos, agotamientos, errores y pendientes.

Con el ejecutador detenido, crear el ZIP fuera del directorio de resultados. Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ELIASDEJESUSZUNIGADELEON --output FHCP-evaluation-ELIASDEJESUSZUNIGADELEON-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ELIASDEJESUSZUNIGADELEON --output FHCP-evaluation-ELIASDEJESUSZUNIGADELEON-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

**Subir manualmente a [tu carpeta Elias en FHCP-evaluation](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut):**

1. `FHCP-evaluation-ELIASDEJESUSZUNIGADELEON-45f464ae-50be-441b-b7ff-a261fba5028e.zip`, completo, sin quitar intentos ni logs.
2. `FHCP-evaluation-ELIASDEJESUSZUNIGADELEON-45f464ae-50be-441b-b7ff-a261fba5028e.zip.sha256`, generado junto al ZIP.
3. Copias de `summary.md`, `summary.csv` y `summary.json` para consultar las tablas sin extraer el ZIP.

El comando `pack` crea los archivos locales; **no los sube automáticamente a Drive**. Subirlos a la carpeta personal indicada. Si se comparte una entrega parcial y después otra final, añadir un sufijo diferente al ZIP (por ejemplo `-final-20261115`) para conservar ambas; `pack` rechaza sobrescrituras. Conservar también el directorio local para reanudar o auditar.

Al entregar, comentar en este issue el enlace al ZIP final, SHA-256, grafos evaluados/resueltos/pendientes, errores y tiempo observado. Arturo verificará la recuperación e integridad y combinará las cinco entregas con el mismo plan para deduplicar los 60 grafos. No cerrar este issue solo porque acabó una sesión o se subió un archivo.

## Criteria

- [ ] Registrar commit, CPU, RAM, SO, instalación, pruebas y `check` satisfactorios antes del lote.
- [ ] Ejecutar únicamente los grafos asignados con las seis familias, 10 semillas y 60 s por intento en el mismo equipo; conservar el plan congelado.
- [ ] Documentar sesiones, grafos completados y pendientes, errores/timeouts/interrupciones, conservando todos los primarios sin reintentos ocultos.
- [ ] Certificar los ciclos con el validador independiente; distinguir grafos distintos resueltos de éxitos por intento y del presupuesto agotado.
- [ ] Subir ZIP + SHA-256 y las tres tablas finales a **FHCP-evaluation / Elias**, y enlazarlos aquí.
- [ ] Verificar recuperación/integridad e incorporar la entrega a la agregación conjunta. Acordar con Arturo el alcance final si quedan candidatos pendientes por haberse alcanzado el objetivo global.
- [ ] Enlazar la evidencia/PR de resultados aceptada y registrar las limitaciones de comparación entre equipos antes del cierre.

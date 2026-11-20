## Overview

**Evaluación experimental FHCP.** Ejecutar por sesiones los grafos asignados a @ZapataFrame, conservar los resultados originales de los seis algoritmos y subir la entrega final a su carpeta de Drive.

- **Responsable:** @ZapataFrame · Diego Eduardo Zapata Aguilar
- **Hito:** evaluación experimental posterior a M6; seguimiento separado de #71. Sin milestone nuevo.
- **Depende para inicio de:** instalación y comprobación del equipo con la revisión fijada.
- **Versión fijada:** commit `19ac5eaa46fbacc5a034dae6d14befbf171928db`. Usar esta revisión de código y el plan compartido durante toda la evaluación.
- **Plan compartido:** `experiments/configs/distributed-fhcp-10x60.json`; UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`. No regenerarlo ni editarlo.
- **Protocolo:** GA, SA, AS, ABC, DE y PSO; 10 semillas (1001–1010); hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones. Termina antes si encuentra un ciclo certificado. Cupo externo: 120 s por proceso, incluidos arranque y carga.
- **Cola asignada:** 196 grafos, 11,760 intentos si se agota. Cada grafo completo representa 60 intentos y hasta 60 min de búsqueda, más sobrecarga. Toda esta cola supone hasta 196 h de búsqueda; es un techo de presupuesto, no tiempo medido.
- **Objetivo del equipo:** 60 grafos **distintos resueltos y certificados entre todos**. La cola es una reserva: no se exige recorrerla completa si se alcanza el objetivo. Resolver el mismo grafo con varias semillas o algoritmos cuenta una sola vez.
- **Entrega final:** [FHCP-results / FHCP-evaluation / Zapata](https://drive.google.com/drive/folders/1CvuyOAML9oLtvmFrB-rIOGorJOliTwF_). Esta carpeta ya existe en el Drive institucional de Arturo y el equipo tiene permiso de edición.

### Grafos asignados

El ejecutador usa automáticamente esta lista, en este orden; no hay que introducir los IDs manualmente. No ejecutar los grafos de otro integrante.

`graph2`, `graph7`, `graph12`, `graph17`, `graph23`, `graph28`, `graph32`, `graph37`, `graph43`, `graph49`, `graph54`, `graph60`, `graph66`, `graph70`, `graph76`, `graph78`, `graph83`, `graph87`, `graph88`, `graph90`, `graph94`, `graph99`, `graph104`, `graph111`, `graph114`, `graph140`, `graph147`, `graph152`, `graph158`, `graph161`, `graph162`, `graph165`, `graph169`, `graph179`, `graph181`, `graph186`, `graph191`, `graph197`, `graph203`, `graph206`, `graph211`, `graph215`, `graph224`, `graph225`, `graph226`, `graph238`, `graph242`, `graph246`, `graph254`, `graph256`, `graph262`, `graph264`, `graph268`, `graph270`, `graph279`, `graph283`, `graph298`, `graph299`, `graph301`, `graph306`, `graph307`, `graph313`, `graph318`, `graph332`, `graph337`, `graph345`, `graph348`, `graph352`, `graph358`, `graph361`, `graph367`, `graph370`, `graph374`, `graph382`, `graph396`, `graph397`, `graph403`, `graph407`, `graph415`, `graph423`, `graph433`, `graph443`, `graph449`, `graph452`, `graph455`, `graph461`, `graph465`, `graph471`, `graph479`, `graph486`, `graph491`, `graph496`, `graph499`, `graph502`, `graph507`, `graph512`, `graph518`, `graph519`, `graph523`, `graph528`, `graph529`, `graph531`, `graph537`, `graph538`, `graph539`, `graph540`, `graph542`, `graph548`, `graph554`, `graph555`, `graph565`, `graph573`, `graph581`, `graph588`, `graph600`, `graph604`, `graph610`, `graph617`, `graph623`, `graph624`, `graph629`, `graph633`, `graph636`, `graph638`, `graph648`, `graph649`, `graph653`, `graph657`, `graph663`, `graph665`, `graph668`, `graph671`, `graph680`, `graph683`, `graph687`, `graph688`, `graph695`, `graph696`, `graph711`, `graph724`, `graph733`, `graph738`, `graph744`, `graph764`, `graph766`, `graph772`, `graph775`, `graph778`, `graph780`, `graph783`, `graph787`, `graph796`, `graph802`, `graph806`, `graph814`, `graph815`, `graph820`, `graph822`, `graph823`, `graph826`, `graph842`, `graph847`, `graph849`, `graph850`, `graph851`, `graph852`, `graph854`, `graph856`, `graph869`, `graph875`, `graph884`, `graph898`, `graph900`, `graph904`, `graph906`, `graph919`, `graph921`, `graph923`, `graph931`, `graph934`, `graph935`, `graph943`, `graph949`, `graph950`, `graph952`, `graph959`, `graph960`, `graph965`, `graph966`, `graph972`, `graph976`, `graph982`, `graph986`, `graph991`, `graph1000`, `graph1001`

### 1. Preparación

Instalar Git y **CPython 3.14.10 estándar, con GIL, x86_64**, según el [entorno documentado](https://github.com/ZapataFrame/FHCP-Challenge#entorno-de-desarrollo). Usar un checkout nuevo para preservar otros trabajos. Ejecutar cada comando por separado y detenerse ante errores.

Estos comandos Git sirven en Linux y PowerShell:

```text
git clone -c core.autocrlf=false https://github.com/ZapataFrame/FHCP-Challenge.git FHCP-evaluation-ZapataFrame
cd FHCP-evaluation-ZapataFrame
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
.venv/bin/python -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member ZapataFrame
```

Windows PowerShell, con el lanzador `py` seleccionando CPython 3.14.10 estándar de 64 bits:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: pip==26.3
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -W error tests/test_distributed_campaign.py
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member ZapataFrame
```

`check` valida versiones, fuentes, catálogo y hashes de todos tus grafos, sin lanzar solvers; si falla, conservar el error y comentarlo aquí antes de iniciar. Adjuntar su salida y las pruebas al issue, junto con CPU, RAM y sistema operativo. Las pruebas usan grafos sintéticos y no cuentan como resultados FHCP.

### 2. Ejecutar y reanudar por sesiones

Primera sesión de hasta 60 min, más el proceso que ya esté activo. Linux:

```bash
systemd-inhibit --what=sleep:idle --mode=block --why="Evaluación experimental FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member ZapataFrame --max-session-minutes 60
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member ZapataFrame --max-session-minutes 60
```

Repetir **el mismo comando** para continuar desde los pendientes. El límite de sesión no reduce los 60 s de cada intento ni las 10 semillas. Código de salida 3 significa pausa con pendientes; código 0 significa que se recorrió toda la cola, incluso si hubo errores. No significa que todos los grafos se resolvieron.

Mantener el mismo equipo y entorno, un proceso a la vez, laptop conectada, terminal abierta y tapa abierta. Windows inhibe la suspensión por inactividad durante la ejecución; Linux usa `systemd-inhibit`. No apagar ni suspender manualmente. Si se interrumpe, reanudar sin borrar archivos ni repetir primarios. Los intentos interrumpidos quedan como incidencias; informar errores, timeouts y pausas por recursos.

Tras cada sesión comentar aquí: grafos con los 60 intentos ya conciliados, grafos distintos certificados, intentos realizados/pendientes, errores y ruta de resultados. Una sesión puede pausar a mitad de grafo: completarlo en las siguientes antes de darlo por terminado. El equipo revisará el total global; al alcanzar 60 resueltos, coordinar la parada y completar las combinaciones de algoritmos/semillas del grafo iniciado. No hay parada global automática.

### 3. Tablas, logs y entrega final en Drive

Los resultados quedan en `experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ZapataFrame/`: `terminal.log`, `plan.json`, perfil de máquina, snapshot de fuentes, historial de sesiones, `attempts/` con rutas originales/RunRecords, stderr y auditorías, y `summary.md`, `summary.csv`, `summary.json`. Las tablas se actualizan cada 25 intentos y al terminar cada sesión. Conservar éxitos, agotamientos, errores y pendientes.

Con el ejecutador detenido, crear el ZIP fuera del directorio de resultados. Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ZapataFrame --output FHCP-evaluation-ZapataFrame-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ZapataFrame --output FHCP-evaluation-ZapataFrame-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

**Subir manualmente a [tu carpeta Zapata en FHCP-evaluation](https://drive.google.com/drive/folders/1CvuyOAML9oLtvmFrB-rIOGorJOliTwF_):**

1. `FHCP-evaluation-ZapataFrame-45f464ae-50be-441b-b7ff-a261fba5028e.zip`, completo, sin quitar intentos ni logs.
2. `FHCP-evaluation-ZapataFrame-45f464ae-50be-441b-b7ff-a261fba5028e.zip.sha256`, generado junto al ZIP.
3. Copias de `summary.md`, `summary.csv` y `summary.json` para consultar las tablas sin extraer el ZIP.

El comando `pack` crea los archivos locales; **no los sube automáticamente a Drive**. Subirlos a la carpeta personal indicada. Si se comparte una entrega parcial y después otra final, añadir un sufijo diferente al ZIP (por ejemplo `-final-20261115`) para conservar ambas; `pack` rechaza sobrescrituras. Conservar también el directorio local para reanudar o auditar.

Al entregar, comentar en este issue el enlace al ZIP final, SHA-256, grafos evaluados/resueltos/pendientes, errores y tiempo observado. Arturo verificará la recuperación e integridad y combinará las cinco entregas con el mismo plan para deduplicar los 60 grafos. No cerrar este issue solo porque acabó una sesión o se subió un archivo.

## Criteria

- [ ] Registrar commit, CPU, RAM, SO, instalación, pruebas y `check` satisfactorios antes del lote.
- [ ] Ejecutar únicamente los grafos asignados con las seis familias, 10 semillas y 60 s por intento en el mismo equipo; conservar el plan congelado.
- [ ] Documentar sesiones, grafos completados y pendientes, errores/timeouts/interrupciones, conservando todos los primarios sin reintentos ocultos.
- [ ] Certificar los ciclos con el validador independiente; distinguir grafos distintos resueltos de éxitos por intento y del presupuesto agotado.
- [ ] Subir ZIP + SHA-256 y las tres tablas finales a **FHCP-evaluation / Zapata**, y enlazarlos aquí.
- [ ] Verificar recuperación/integridad e incorporar la entrega a la agregación conjunta. Acordar con Arturo el alcance final si quedan candidatos pendientes por haberse alcanzado el objetivo global.
- [ ] Enlazar la evidencia/PR de resultados aceptada y registrar las limitaciones de comparación entre equipos antes del cierre.

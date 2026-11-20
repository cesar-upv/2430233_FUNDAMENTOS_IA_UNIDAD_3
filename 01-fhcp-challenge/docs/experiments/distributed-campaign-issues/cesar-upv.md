## Overview

**Evaluación experimental FHCP.** Ejecutar por sesiones los grafos asignados a @cesar-upv, conservar los resultados originales de los seis algoritmos y subir la entrega final a su carpeta de Drive.

- **Responsable:** @cesar-upv · César Euresti
- **Hito:** evaluación experimental posterior a M6; seguimiento separado de #71. Sin milestone nuevo.
- **Depende para inicio de:** instalación y comprobación del equipo con la revisión fijada.
- **Versión fijada:** commit `19ac5eaa46fbacc5a034dae6d14befbf171928db`. Usar esta revisión de código y el plan compartido durante toda la evaluación.
- **Plan compartido:** `experiments/configs/distributed-fhcp-10x60.json`; UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`. No regenerarlo ni editarlo.
- **Protocolo:** GA, SA, AS, ABC, DE y PSO; 10 semillas (1001–1010); hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones. Termina antes si encuentra un ciclo certificado. Cupo externo: 120 s por proceso, incluidos arranque y carga.
- **Cola asignada:** 195 grafos, 11,700 intentos si se agota. Cada grafo completo representa 60 intentos y hasta 60 min de búsqueda, más sobrecarga. Toda esta cola supone hasta 195 h de búsqueda; es un techo de presupuesto, no tiempo medido.
- **Objetivo del equipo:** 60 grafos **distintos resueltos y certificados entre todos**. La cola es una reserva: no se exige recorrerla completa si se alcanza el objetivo. Resolver el mismo grafo con varias semillas o algoritmos cuenta una sola vez.
- **Entrega final:** [FHCP-results / FHCP-evaluation / Cesar](https://drive.google.com/drive/folders/1sYY6HrJQUxUdfW4p6QDTnwCBs8hAOv1-). Esta carpeta ya existe en el Drive institucional de Arturo y el equipo tiene permiso de edición.

### Grafos asignados

El ejecutador usa automáticamente esta lista, en este orden; no hay que introducir los IDs manualmente. No ejecutar los grafos de otro integrante.

`graph3`, `graph8`, `graph13`, `graph18`, `graph19`, `graph24`, `graph33`, `graph39`, `graph44`, `graph50`, `graph55`, `graph61`, `graph62`, `graph67`, `graph71`, `graph72`, `graph80`, `graph89`, `graph100`, `graph105`, `graph112`, `graph116`, `graph117`, `graph121`, `graph125`, `graph133`, `graph141`, `graph148`, `graph149`, `graph150`, `graph153`, `graph163`, `graph166`, `graph170`, `graph172`, `graph182`, `graph192`, `graph193`, `graph204`, `graph207`, `graph213`, `graph216`, `graph218`, `graph220`, `graph223`, `graph228`, `graph232`, `graph239`, `graph240`, `graph248`, `graph250`, `graph253`, `graph259`, `graph267`, `graph271`, `graph273`, `graph284`, `graph309`, `graph311`, `graph315`, `graph324`, `graph327`, `graph330`, `graph336`, `graph341`, `graph351`, `graph354`, `graph355`, `graph360`, `graph364`, `graph371`, `graph377`, `graph378`, `graph386`, `graph390`, `graph398`, `graph402`, `graph406`, `graph410`, `graph414`, `graph417`, `graph421`, `graph422`, `graph428`, `graph432`, `graph435`, `graph437`, `graph442`, `graph450`, `graph459`, `graph468`, `graph482`, `graph487`, `graph488`, `graph492`, `graph495`, `graph497`, `graph510`, `graph511`, `graph513`, `graph515`, `graph520`, `graph521`, `graph526`, `graph530`, `graph534`, `graph536`, `graph544`, `graph547`, `graph551`, `graph558`, `graph562`, `graph563`, `graph570`, `graph579`, `graph582`, `graph585`, `graph593`, `graph595`, `graph596`, `graph598`, `graph602`, `graph606`, `graph609`, `graph615`, `graph619`, `graph627`, `graph639`, `graph640`, `graph646`, `graph650`, `graph651`, `graph656`, `graph659`, `graph667`, `graph675`, `graph677`, `graph691`, `graph699`, `graph705`, `graph708`, `graph710`, `graph713`, `graph720`, `graph727`, `graph732`, `graph735`, `graph741`, `graph751`, `graph752`, `graph759`, `graph760`, `graph763`, `graph768`, `graph769`, `graph776`, `graph793`, `graph809`, `graph818`, `graph824`, `graph836`, `graph840`, `graph844`, `graph846`, `graph860`, `graph864`, `graph866`, `graph868`, `graph873`, `graph878`, `graph880`, `graph889`, `graph891`, `graph893`, `graph897`, `graph899`, `graph902`, `graph905`, `graph913`, `graph917`, `graph922`, `graph925`, `graph929`, `graph939`, `graph942`, `graph946`, `graph951`, `graph956`, `graph963`, `graph971`, `graph977`, `graph983`, `graph988`, `graph997`, `graph999`

### 1. Preparación

Instalar Git y **CPython 3.14.10 estándar, con GIL, x86_64**, según el [entorno documentado](https://github.com/ZapataFrame/FHCP-Challenge#entorno-de-desarrollo). Usar un checkout nuevo para preservar otros trabajos. Ejecutar cada comando por separado y detenerse ante errores.

Estos comandos Git sirven en Linux y PowerShell:

```text
git clone -c core.autocrlf=false https://github.com/ZapataFrame/FHCP-Challenge.git FHCP-evaluation-cesar-upv
cd FHCP-evaluation-cesar-upv
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
.venv/bin/python -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member cesar-upv
```

Windows PowerShell, con el lanzador `py` seleccionando CPython 3.14.10 estándar de 64 bits:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: pip==26.3
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -W error tests/test_distributed_campaign.py
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member cesar-upv
```

`check` valida versiones, fuentes, catálogo y hashes de todos tus grafos, sin lanzar solvers; si falla, conservar el error y comentarlo aquí antes de iniciar. Adjuntar su salida y las pruebas al issue, junto con CPU, RAM y sistema operativo. Las pruebas usan grafos sintéticos y no cuentan como resultados FHCP.

### 2. Ejecutar y reanudar por sesiones

Primera sesión de hasta 60 min, más el proceso que ya esté activo. Linux:

```bash
systemd-inhibit --what=sleep:idle --mode=block --why="Evaluación experimental FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member cesar-upv --max-session-minutes 60
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member cesar-upv --max-session-minutes 60
```

Repetir **el mismo comando** para continuar desde los pendientes. El límite de sesión no reduce los 60 s de cada intento ni las 10 semillas. Código de salida 3 significa pausa con pendientes; código 0 significa que se recorrió toda la cola, incluso si hubo errores. No significa que todos los grafos se resolvieron.

Mantener el mismo equipo y entorno, un proceso a la vez, laptop conectada, terminal abierta y tapa abierta. Windows inhibe la suspensión por inactividad durante la ejecución; Linux usa `systemd-inhibit`. No apagar ni suspender manualmente. Si se interrumpe, reanudar sin borrar archivos ni repetir primarios. Los intentos interrumpidos quedan como incidencias; informar errores, timeouts y pausas por recursos.

Tras cada sesión comentar aquí: grafos con los 60 intentos ya conciliados, grafos distintos certificados, intentos realizados/pendientes, errores y ruta de resultados. Una sesión puede pausar a mitad de grafo: completarlo en las siguientes antes de darlo por terminado. El equipo revisará el total global; al alcanzar 60 resueltos, coordinar la parada y completar las combinaciones de algoritmos/semillas del grafo iniciado. No hay parada global automática.

### 3. Tablas, logs y entrega final en Drive

Los resultados quedan en `experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-cesar-upv/`: `terminal.log`, `plan.json`, perfil de máquina, snapshot de fuentes, historial de sesiones, `attempts/` con rutas originales/RunRecords, stderr y auditorías, y `summary.md`, `summary.csv`, `summary.json`. Las tablas se actualizan cada 25 intentos y al terminar cada sesión. Conservar éxitos, agotamientos, errores y pendientes.

Con el ejecutador detenido, crear el ZIP fuera del directorio de resultados. Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-cesar-upv --output FHCP-evaluation-cesar-upv-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-cesar-upv --output FHCP-evaluation-cesar-upv-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

**Subir manualmente a [tu carpeta Cesar en FHCP-evaluation](https://drive.google.com/drive/folders/1sYY6HrJQUxUdfW4p6QDTnwCBs8hAOv1-):**

1. `FHCP-evaluation-cesar-upv-45f464ae-50be-441b-b7ff-a261fba5028e.zip`, completo, sin quitar intentos ni logs.
2. `FHCP-evaluation-cesar-upv-45f464ae-50be-441b-b7ff-a261fba5028e.zip.sha256`, generado junto al ZIP.
3. Copias de `summary.md`, `summary.csv` y `summary.json` para consultar las tablas sin extraer el ZIP.

El comando `pack` crea los archivos locales; **no los sube automáticamente a Drive**. Subirlos a la carpeta personal indicada. Si se comparte una entrega parcial y después otra final, añadir un sufijo diferente al ZIP (por ejemplo `-final-20261115`) para conservar ambas; `pack` rechaza sobrescrituras. Conservar también el directorio local para reanudar o auditar.

Al entregar, comentar en este issue el enlace al ZIP final, SHA-256, grafos evaluados/resueltos/pendientes, errores y tiempo observado. Arturo verificará la recuperación e integridad y combinará las cinco entregas con el mismo plan para deduplicar los 60 grafos. No cerrar este issue solo porque acabó una sesión o se subió un archivo.

## Criteria

- [ ] Registrar commit, CPU, RAM, SO, instalación, pruebas y `check` satisfactorios antes del lote.
- [ ] Ejecutar únicamente los grafos asignados con las seis familias, 10 semillas y 60 s por intento en el mismo equipo; conservar el plan congelado.
- [ ] Documentar sesiones, grafos completados y pendientes, errores/timeouts/interrupciones, conservando todos los primarios sin reintentos ocultos.
- [ ] Certificar los ciclos con el validador independiente; distinguir grafos distintos resueltos de éxitos por intento y del presupuesto agotado.
- [ ] Subir ZIP + SHA-256 y las tres tablas finales a **FHCP-evaluation / Cesar**, y enlazarlos aquí.
- [ ] Verificar recuperación/integridad e incorporar la entrega a la agregación conjunta. Acordar con Arturo el alcance final si quedan candidatos pendientes por haberse alcanzado el objetivo global.
- [ ] Enlazar la evidencia/PR de resultados aceptada y registrar las limitaciones de comparación entre equipos antes del cierre.

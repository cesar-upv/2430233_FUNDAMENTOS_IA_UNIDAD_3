## Overview

**Evaluación experimental FHCP.** Ejecutar por sesiones los grafos asignados a @KirbyStone69, conservar los resultados originales de los seis algoritmos y subir la entrega final a su carpeta de Drive.

- **Responsable:** @KirbyStone69 · Eder Omar Zúñiga Zavala
- **Hito:** evaluación experimental posterior a M6; seguimiento separado de #71. Sin milestone nuevo.
- **Depende para inicio de:** instalación y comprobación del equipo con la revisión fijada.
- **Versión fijada:** commit `19ac5eaa46fbacc5a034dae6d14befbf171928db`. Usar esta revisión de código y el plan compartido durante toda la evaluación.
- **Plan compartido:** `experiments/configs/distributed-fhcp-10x60.json`; UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`. No regenerarlo ni editarlo.
- **Protocolo:** GA, SA, AS, ABC, DE y PSO; 10 semillas (1001–1010); hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones. Termina antes si encuentra un ciclo certificado. Cupo externo: 120 s por proceso, incluidos arranque y carga.
- **Cola asignada:** 195 grafos, 11,700 intentos si se agota. Cada grafo completo representa 60 intentos y hasta 60 min de búsqueda, más sobrecarga. Toda esta cola supone hasta 195 h de búsqueda; es un techo de presupuesto, no tiempo medido.
- **Objetivo del equipo:** 60 grafos **distintos resueltos y certificados entre todos**. La cola es una reserva: no se exige recorrerla completa si se alcanza el objetivo. Resolver el mismo grafo con varias semillas o algoritmos cuenta una sola vez.
- **Entrega final:** [FHCP-results / FHCP-evaluation / Eder](https://drive.google.com/drive/folders/1GO8g4-chyUJnl6u7ah-2Bjfq6mdfAd3A). Esta carpeta ya existe en el Drive institucional de Arturo y el equipo tiene permiso de edición.

### Grafos asignados

El ejecutador usa automáticamente esta lista, en este orden; no hay que introducir los IDs manualmente. No ejecutar los grafos de otro integrante.

`graph4`, `graph9`, `graph14`, `graph20`, `graph25`, `graph29`, `graph34`, `graph40`, `graph45`, `graph51`, `graph56`, `graph63`, `graph68`, `graph73`, `graph74`, `graph79`, `graph91`, `graph95`, `graph101`, `graph106`, `graph110`, `graph118`, `graph122`, `graph123`, `graph129`, `graph134`, `graph136`, `graph142`, `graph145`, `graph155`, `graph159`, `graph167`, `graph171`, `graph173`, `graph183`, `graph187`, `graph194`, `graph198`, `graph205`, `graph208`, `graph214`, `graph219`, `graph222`, `graph227`, `graph229`, `graph235`, `graph241`, `graph247`, `graph249`, `graph260`, `graph265`, `graph269`, `graph274`, `graph278`, `graph281`, `graph285`, `graph287`, `graph291`, `graph293`, `graph302`, `graph308`, `graph312`, `graph317`, `graph320`, `graph325`, `graph329`, `graph334`, `graph340`, `graph342`, `graph344`, `graph349`, `graph353`, `graph356`, `graph365`, `graph372`, `graph376`, `graph379`, `graph383`, `graph384`, `graph385`, `graph399`, `graph405`, `graph409`, `graph412`, `graph416`, `graph424`, `graph426`, `graph430`, `graph431`, `graph439`, `graph440`, `graph446`, `graph453`, `graph466`, `graph472`, `graph475`, `graph480`, `graph481`, `graph489`, `graph494`, `graph500`, `graph503`, `graph505`, `graph506`, `graph509`, `graph516`, `graph522`, `graph525`, `graph541`, `graph543`, `graph549`, `graph552`, `graph561`, `graph564`, `graph567`, `graph576`, `graph578`, `graph584`, `graph587`, `graph591`, `graph594`, `graph601`, `graph605`, `graph611`, `graph614`, `graph616`, `graph620`, `graph631`, `graph641`, `graph642`, `graph645`, `graph658`, `graph666`, `graph672`, `graph676`, `graph679`, `graph681`, `graph685`, `graph686`, `graph690`, `graph693`, `graph698`, `graph706`, `graph719`, `graph721`, `graph726`, `graph729`, `graph734`, `graph736`, `graph745`, `graph758`, `graph765`, `graph774`, `graph786`, `graph788`, `graph791`, `graph804`, `graph807`, `graph808`, `graph811`, `graph812`, `graph813`, `graph828`, `graph829`, `graph835`, `graph838`, `graph861`, `graph862`, `graph872`, `graph874`, `graph877`, `graph879`, `graph883`, `graph894`, `graph896`, `graph901`, `graph909`, `graph911`, `graph916`, `graph926`, `graph928`, `graph940`, `graph944`, `graph953`, `graph955`, `graph962`, `graph967`, `graph970`, `graph973`, `graph974`, `graph975`, `graph981`, `graph985`, `graph992`, `graph998`

### 1. Preparación

Instalar Git y **CPython 3.14.10 estándar, con GIL, x86_64**, según el [entorno documentado](https://github.com/ZapataFrame/FHCP-Challenge#entorno-de-desarrollo). Usar un checkout nuevo para preservar otros trabajos. Ejecutar cada comando por separado y detenerse ante errores.

Estos comandos Git sirven en Linux y PowerShell:

```text
git clone -c core.autocrlf=false https://github.com/ZapataFrame/FHCP-Challenge.git FHCP-evaluation-KirbyStone69
cd FHCP-evaluation-KirbyStone69
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
.venv/bin/python -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member KirbyStone69
```

Windows PowerShell, con el lanzador `py` seleccionando CPython 3.14.10 estándar de 64 bits:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: pip==26.3
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -W error tests/test_distributed_campaign.py
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member KirbyStone69
```

`check` valida versiones, fuentes, catálogo y hashes de todos tus grafos, sin lanzar solvers; si falla, conservar el error y comentarlo aquí antes de iniciar. Adjuntar su salida y las pruebas al issue, junto con CPU, RAM y sistema operativo. Las pruebas usan grafos sintéticos y no cuentan como resultados FHCP.

### 2. Ejecutar y reanudar por sesiones

Primera sesión de hasta 60 min, más el proceso que ya esté activo. Linux:

```bash
systemd-inhibit --what=sleep:idle --mode=block --why="Evaluación experimental FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member KirbyStone69 --max-session-minutes 60
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member KirbyStone69 --max-session-minutes 60
```

Repetir **el mismo comando** para continuar desde los pendientes. El límite de sesión no reduce los 60 s de cada intento ni las 10 semillas. Código de salida 3 significa pausa con pendientes; código 0 significa que se recorrió toda la cola, incluso si hubo errores. No significa que todos los grafos se resolvieron.

Mantener el mismo equipo y entorno, un proceso a la vez, laptop conectada, terminal abierta y tapa abierta. Windows inhibe la suspensión por inactividad durante la ejecución; Linux usa `systemd-inhibit`. No apagar ni suspender manualmente. Si se interrumpe, reanudar sin borrar archivos ni repetir primarios. Los intentos interrumpidos quedan como incidencias; informar errores, timeouts y pausas por recursos.

Tras cada sesión comentar aquí: grafos con los 60 intentos ya conciliados, grafos distintos certificados, intentos realizados/pendientes, errores y ruta de resultados. Una sesión puede pausar a mitad de grafo: completarlo en las siguientes antes de darlo por terminado. El equipo revisará el total global; al alcanzar 60 resueltos, coordinar la parada y completar las combinaciones de algoritmos/semillas del grafo iniciado. No hay parada global automática.

### 3. Tablas, logs y entrega final en Drive

Los resultados quedan en `experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-KirbyStone69/`: `terminal.log`, `plan.json`, perfil de máquina, snapshot de fuentes, historial de sesiones, `attempts/` con rutas originales/RunRecords, stderr y auditorías, y `summary.md`, `summary.csv`, `summary.json`. Las tablas se actualizan cada 25 intentos y al terminar cada sesión. Conservar éxitos, agotamientos, errores y pendientes.

Con el ejecutador detenido, crear el ZIP fuera del directorio de resultados. Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-KirbyStone69 --output FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-KirbyStone69 --output FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

**Subir manualmente a [tu carpeta Eder en FHCP-evaluation](https://drive.google.com/drive/folders/1GO8g4-chyUJnl6u7ah-2Bjfq6mdfAd3A):**

1. `FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e.zip`, completo, sin quitar intentos ni logs.
2. `FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e.zip.sha256`, generado junto al ZIP.
3. Copias de `summary.md`, `summary.csv` y `summary.json` para consultar las tablas sin extraer el ZIP.

El comando `pack` crea los archivos locales; **no los sube automáticamente a Drive**. Subirlos a la carpeta personal indicada. Si se comparte una entrega parcial y después otra final, añadir un sufijo diferente al ZIP (por ejemplo `-final-20261115`) para conservar ambas; `pack` rechaza sobrescrituras. Conservar también el directorio local para reanudar o auditar.

Al entregar, comentar en este issue el enlace al ZIP final, SHA-256, grafos evaluados/resueltos/pendientes, errores y tiempo observado. Arturo verificará la recuperación e integridad y combinará las cinco entregas con el mismo plan para deduplicar los 60 grafos. No cerrar este issue solo porque acabó una sesión o se subió un archivo.

## Criteria

- [ ] Registrar commit, CPU, RAM, SO, instalación, pruebas y `check` satisfactorios antes del lote.
- [ ] Ejecutar únicamente los grafos asignados con las seis familias, 10 semillas y 60 s por intento en el mismo equipo; conservar el plan congelado.
- [ ] Documentar sesiones, grafos completados y pendientes, errores/timeouts/interrupciones, conservando todos los primarios sin reintentos ocultos.
- [ ] Certificar los ciclos con el validador independiente; distinguir grafos distintos resueltos de éxitos por intento y del presupuesto agotado.
- [ ] Subir ZIP + SHA-256 y las tres tablas finales a **FHCP-evaluation / Eder**, y enlazarlos aquí.
- [ ] Verificar recuperación/integridad e incorporar la entrega a la agregación conjunta. Acordar con Arturo el alcance final si quedan candidatos pendientes por haberse alcanzado el objetivo global.
- [ ] Enlazar la evidencia/PR de resultados aceptada y registrar las limitaciones de comparación entre equipos antes del cierre.

## Overview

**Evaluación experimental FHCP.** Ejecutar por sesiones los grafos asignados a @Arturo2430, conservar los resultados originales de los seis algoritmos y subir la entrega final a su carpeta de Drive.

- **Responsable:** @Arturo2430 · Junior Arturo Vázquez Leonel
- **Hito:** evaluación experimental posterior a M6; seguimiento separado de #71. Sin milestone nuevo.
- **Depende para inicio de:** instalación y comprobación del equipo con la revisión fijada.
- **Versión fijada:** commit `19ac5eaa46fbacc5a034dae6d14befbf171928db`. Usar esta revisión de código y el plan compartido durante toda la evaluación.
- **Plan compartido:** `experiments/configs/distributed-fhcp-10x60.json`; UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`. No regenerarlo ni editarlo.
- **Protocolo:** GA, SA, AS, ABC, DE y PSO; 10 semillas (1001–1010); hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones. Termina antes si encuentra un ciclo certificado. Cupo externo: 120 s por proceso, incluidos arranque y carga.
- **Cola asignada:** 220 grafos, 13,200 intentos si se agota. Cada grafo completo representa 60 intentos y hasta 60 min de búsqueda, más sobrecarga. Toda esta cola supone hasta 220 h de búsqueda; es un techo de presupuesto, no tiempo medido.
- **Objetivo del equipo:** 60 grafos **distintos resueltos y certificados entre todos**. La cola es una reserva: no se exige recorrerla completa si se alcanza el objetivo. Resolver el mismo grafo con varias semillas o algoritmos cuenta una sola vez.
- **Entrega final:** [FHCP-results / FHCP-evaluation / Arturo](https://drive.google.com/drive/folders/1C7I1EFX8XKfGWad7hfwDaBPZybBsqSKZ). Esta carpeta ya existe en el Drive institucional de Arturo y el equipo tiene permiso de edición.

### Grafos asignados

El ejecutador usa automáticamente esta lista, en este orden; no hay que introducir los IDs manualmente. No ejecutar los grafos de otro integrante.

`graph1`, `graph6`, `graph11`, `graph16`, `graph22`, `graph27`, `graph31`, `graph36`, `graph38`, `graph42`, `graph47`, `graph48`, `graph53`, `graph58`, `graph65`, `graph77`, `graph82`, `graph85`, `graph86`, `graph93`, `graph96`, `graph98`, `graph103`, `graph108`, `graph113`, `graph115`, `graph120`, `graph126`, `graph130`, `graph132`, `graph138`, `graph146`, `graph151`, `graph154`, `graph160`, `graph168`, `graph176`, `graph177`, `graph178`, `graph180`, `graph185`, `graph188`, `graph190`, `graph199`, `graph202`, `graph210`, `graph212`, `graph217`, `graph231`, `graph236`, `graph237`, `graph244`, `graph245`, `graph251`, `graph252`, `graph257`, `graph266`, `graph272`, `graph275`, `graph277`, `graph280`, `graph286`, `graph288`, `graph292`, `graph295`, `graph297`, `graph303`, `graph305`, `graph310`, `graph314`, `graph316`, `graph322`, `graph323`, `graph331`, `graph333`, `graph338`, `graph339`, `graph347`, `graph357`, `graph359`, `graph362`, `graph368`, `graph381`, `graph389`, `graph391`, `graph392`, `graph393`, `graph395`, `graph401`, `graph408`, `graph413`, `graph419`, `graph425`, `graph427`, `graph429`, `graph436`, `graph438`, `graph441`, `graph444`, `graph448`, `graph451`, `graph454`, `graph457`, `graph462`, `graph463`, `graph464`, `graph478`, `graph484`, `graph485`, `graph490`, `graph498`, `graph501`, `graph504`, `graph508`, `graph524`, `graph527`, `graph533`, `graph535`, `graph545`, `graph546`, `graph553`, `graph557`, `graph566`, `graph569`, `graph572`, `graph575`, `graph580`, `graph586`, `graph607`, `graph608`, `graph612`, `graph618`, `graph622`, `graph625`, `graph626`, `graph628`, `graph630`, `graph637`, `graph644`, `graph647`, `graph652`, `graph660`, `graph669`, `graph670`, `graph673`, `graph678`, `graph684`, `graph689`, `graph694`, `graph700`, `graph707`, `graph712`, `graph714`, `graph715`, `graph716`, `graph717`, `graph718`, `graph723`, `graph725`, `graph728`, `graph731`, `graph743`, `graph746`, `graph749`, `graph750`, `graph754`, `graph757`, `graph762`, `graph767`, `graph770`, `graph771`, `graph781`, `graph782`, `graph785`, `graph789`, `graph794`, `graph797`, `graph799`, `graph803`, `graph810`, `graph817`, `graph821`, `graph825`, `graph827`, `graph830`, `graph831`, `graph839`, `graph848`, `graph853`, `graph855`, `graph857`, `graph859`, `graph863`, `graph865`, `graph871`, `graph881`, `graph882`, `graph887`, `graph888`, `graph892`, `graph903`, `graph908`, `graph910`, `graph912`, `graph914`, `graph920`, `graph924`, `graph927`, `graph932`, `graph936`, `graph937`, `graph938`, `graph941`, `graph961`, `graph964`, `graph969`, `graph979`, `graph987`, `graph990`, `graph996`

### 1. Preparación

Instalar Git y **CPython 3.14.10 estándar, con GIL, x86_64**, según el [entorno documentado](https://github.com/ZapataFrame/FHCP-Challenge#entorno-de-desarrollo). Usar un checkout nuevo para preservar otros trabajos. Ejecutar cada comando por separado y detenerse ante errores.

Estos comandos Git sirven en Linux y PowerShell:

```text
git clone -c core.autocrlf=false https://github.com/ZapataFrame/FHCP-Challenge.git FHCP-evaluation-Arturo2430
cd FHCP-evaluation-Arturo2430
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
.venv/bin/python -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member Arturo2430
```

Windows PowerShell, con el lanzador `py` seleccionando CPython 3.14.10 estándar de 64 bits:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: pip==26.3
.\.venv\Scripts\python.exe -m pip --isolated install --only-binary=:all: -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -W error tests/test_distributed_campaign.py
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign check --plan experiments/configs/distributed-fhcp-10x60.json --member Arturo2430
```

`check` valida versiones, fuentes, catálogo y hashes de todos tus grafos, sin lanzar solvers; si falla, conservar el error y comentarlo aquí antes de iniciar. Adjuntar su salida y las pruebas al issue, junto con CPU, RAM y sistema operativo. Las pruebas usan grafos sintéticos y no cuentan como resultados FHCP.

### 2. Ejecutar y reanudar por sesiones

Primera sesión de hasta 60 min, más el proceso que ya esté activo. Linux:

```bash
systemd-inhibit --what=sleep:idle --mode=block --why="Evaluación experimental FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member Arturo2430 --max-session-minutes 60
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member Arturo2430 --max-session-minutes 60
```

Repetir **el mismo comando** para continuar desde los pendientes. El límite de sesión no reduce los 60 s de cada intento ni las 10 semillas. Código de salida 3 significa pausa con pendientes; código 0 significa que se recorrió toda la cola, incluso si hubo errores. No significa que todos los grafos se resolvieron.

Mantener el mismo equipo y entorno, un proceso a la vez, laptop conectada, terminal abierta y tapa abierta. Windows inhibe la suspensión por inactividad durante la ejecución; Linux usa `systemd-inhibit`. No apagar ni suspender manualmente. Si se interrumpe, reanudar sin borrar archivos ni repetir primarios. Los intentos interrumpidos quedan como incidencias; informar errores, timeouts y pausas por recursos.

Tras cada sesión comentar aquí: grafos con los 60 intentos ya conciliados, grafos distintos certificados, intentos realizados/pendientes, errores y ruta de resultados. Una sesión puede pausar a mitad de grafo: completarlo en las siguientes antes de darlo por terminado. El equipo revisará el total global; al alcanzar 60 resueltos, coordinar la parada y completar las combinaciones de algoritmos/semillas del grafo iniciado. No hay parada global automática.

### 3. Tablas, logs y entrega final en Drive

Los resultados quedan en `experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-Arturo2430/`: `terminal.log`, `plan.json`, perfil de máquina, snapshot de fuentes, historial de sesiones, `attempts/` con rutas originales/RunRecords, stderr y auditorías, y `summary.md`, `summary.csv`, `summary.json`. Las tablas se actualizan cada 25 intentos y al terminar cada sesión. Conservar éxitos, agotamientos, errores y pendientes.

Con el ejecutador detenido, crear el ZIP fuera del directorio de resultados. Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-Arturo2430 --output FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.cli.distributed_campaign pack --input experiments/results/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-Arturo2430 --output FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e.zip
```

**Subir manualmente a [tu carpeta Arturo en FHCP-evaluation](https://drive.google.com/drive/folders/1C7I1EFX8XKfGWad7hfwDaBPZybBsqSKZ):**

1. `FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e.zip`, completo, sin quitar intentos ni logs.
2. `FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e.zip.sha256`, generado junto al ZIP.
3. Copias de `summary.md`, `summary.csv` y `summary.json` para consultar las tablas sin extraer el ZIP.

El comando `pack` crea los archivos locales; **no los sube automáticamente a Drive**. Subirlos a la carpeta personal indicada. Si se comparte una entrega parcial y después otra final, añadir un sufijo diferente al ZIP (por ejemplo `-final-20261115`) para conservar ambas; `pack` rechaza sobrescrituras. Conservar también el directorio local para reanudar o auditar.

Al entregar, comentar en este issue el enlace al ZIP final, SHA-256, grafos evaluados/resueltos/pendientes, errores y tiempo observado. Arturo verificará la recuperación e integridad y combinará las cinco entregas con el mismo plan para deduplicar los 60 grafos. No cerrar este issue solo porque acabó una sesión o se subió un archivo.

## Criteria

- [ ] Registrar commit, CPU, RAM, SO, instalación, pruebas y `check` satisfactorios antes del lote.
- [ ] Ejecutar únicamente los grafos asignados con las seis familias, 10 semillas y 60 s por intento en el mismo equipo; conservar el plan congelado.
- [ ] Documentar sesiones, grafos completados y pendientes, errores/timeouts/interrupciones, conservando todos los primarios sin reintentos ocultos.
- [ ] Certificar los ciclos con el validador independiente; distinguir grafos distintos resueltos de éxitos por intento y del presupuesto agotado.
- [ ] Subir ZIP + SHA-256 y las tres tablas finales a **FHCP-evaluation / Arturo**, y enlazarlos aquí.
- [ ] Verificar recuperación/integridad e incorporar la entrega a la agregación conjunta. Acordar con Arturo el alcance final si quedan candidatos pendientes por haberse alcanzado el objetivo global.
- [ ] Enlazar la evidencia/PR de resultados aceptada y registrar las limitaciones de comparación entre equipos antes del cierre.

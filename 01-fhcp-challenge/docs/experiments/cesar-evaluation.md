# Evaluación FHCP de César: entrega parcial

> **Estado al cierre de #94 (17 de noviembre de 2026):** este corte ya fue recuperado y agregado con las cinco entregas. El alcance parcial fue aceptado por Arturo. [Resultados conjuntos y decisión de cierre](distributed-evaluation.md). Las referencias a pendientes dentro de las sesiones siguientes describen su estado histórico.

**Responsable:** César Euresti · @cesar-upv. **Seguimiento:** [issue #85](https://github.com/ZapataFrame/FHCP-Challenge/issues/85), sin milestone nuevo y separado de #71/M6.

La ejecución está detenida por solicitud del responsable. Se aceptó como entrega
individual el corte de 30 grafos con sus 60 registros conciliados y `graph153`
parcial; el issue #85 se cerró y el paquete se incorporó a la agregación de #94.

## Procedencia y entorno

- Revisión de ejecución: `19ac5eaa46fbacc5a034dae6d14befbf171928db`, checkout limpio y separado de esta rama documental. No se modificaron fuentes ni plan durante las sesiones.
- Plan original: [`distributed-fhcp-10x60.json`](../../experiments/configs/distributed-fhcp-10x60.json), UUID `45f464ae-50be-441b-b7ff-a261fba5028e` y digest canónico `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.
- Equipo: AMD Ryzen 7 7730U, 8 núcleos/16 hilos; 16,060,182,528 bytes de RAM (14.96 GiB); CachyOS Linux x86_64, kernel `7.3.3-1-cachyos`.
- CPython 3.14.10 estándar con GIL, 64 bits; NumPy 2.5.4; venv nuevo con pip 26.3 y requisitos fijados.
- GA, SA, AS, ABC, DE y PSO; semillas 1001–1010; hasta 60 s de solver por intento, sin límite de evaluaciones ni iteraciones, con cupo externo de 120 s incluidos arranque/carga. Un proceso a la vez y hilos nativos fijados a uno.

Las [salidas conservadas](evidence/cesar-evaluation-20261116/preparation-checks.txt)
registran 48 pruebas del coordinador aprobadas, tres del entorno aprobadas,
`pip check` sin conflictos y `check` correcto para los 195 grafos. No se ejecutó
la suite completa en esta preparación. Las pruebas usan búsqueda sintética y
no constituyen resultados científicos FHCP. Se conservan también el perfil,
instalación, preflight e historial de lanzamiento/parada en Drive.

## Corte medido

La [evidencia estructurada](evidence/cesar-evaluation-20261116/results.json)
conserva el alcance, sesiones, métricas, incidencias y hashes de los archivos entregados.

| Concepto | Registros |
| --- | ---: |
| Cola asignada | 195 grafos / 11,700 combinaciones |
| Intentos registrados | 1,853 |
| Éxitos certificados por intento | 90 |
| Agotamientos | 1,761 |
| Interrupciones conservadas como errores | 2 |
| Timeouts externos | 0 |
| Grafos distintos certificados | 3 |
| Combinaciones sin iniciar | 9,847 |

Los tres grafos resueltos son `graph18`, `graph72` y `graph150`. Los 90 éxitos
no equivalen a 90 grafos distintos. Los pendientes no se cuentan como intentos
fallidos y un agotamiento no demuestra ausencia de ciclo.

Los 30 grafos con 60 registros conciliados son:

```text
graph3, graph8, graph13, graph18, graph19, graph24, graph33, graph39,
graph44, graph50, graph55, graph61, graph62, graph67, graph71, graph72,
graph80, graph89, graph100, graph105, graph112, graph116, graph117,
graph121, graph125, graph133, graph141, graph148, graph149, graph150
```

`graph105` incluye una interrupción entre sus 60 registros; no se presenta como
60 búsquedas terminadas normalmente. `graph153` conserva 53/60 registros,
incluida la segunda interrupción, y siete combinaciones sin iniciar. Los otros
164 grafos no se iniciaron. Las incidencias no se reintentaron ni se descartaron.

## Sesiones e interrupciones

| Fin UTC | Intentos nuevos | Acumulados | Motivo conservado | Duración registrada (s) |
| --- | ---: | ---: | --- | ---: |
| 2026-11-15 00:29:00 | 60 | 60 | `session_limit` | 3,620.440137 |
| 2026-11-15 18:40:30 | 1,109 | 1,169 | `coordinator_error` | 63,951.107380 |
| 2026-11-16 06:01:46 | 684 | 1,853 | `interrupted` | 38,914.977880 |

La segunda sesión conserva `graph105-de-1005` como intento interrumpido:
`exit.json` declara `interrupted`, retorno 130, y stderr registra
`KeyboardInterrupt`. El historial del coordinador declara `coordinator_error`;
se preserva esa discrepancia sin inventar otra causa ni reemplazar archivos.
La última parada fue solicitada por el responsable y enviada como SIGINT al
coordinador; `graph153-de-1009` quedó interrumpido. Se comprobó el cierre de los
procesos antes de empaquetar.

El tiempo acumulado registrado por los coordinadores es **106,486.525398 s**,
aproximadamente **29 h 34 min 46.5 s**. Incluye búsqueda y sobrecarga dentro de
las sesiones; excluye pausas entre ellas y las auditorías previas a reanudar.
No es tiempo exclusivo de solver ni tiempo medio hasta resolver.

## Entrega en Drive

Destino: [FHCP-results / FHCP-evaluation / Cesar](https://drive.google.com/drive/folders/1sYY6HrJQUxUdfW4p6QDTnwCBs8hAOv1-).
El responsable confirmó la subida y aportó una
[captura del contenido](evidence/cesar-evaluation-20261116/drive-upload.png).
El enlace disponible es el de la carpeta; localizar el ZIP por este nombre exacto:

```text
FHCP-evaluation-cesar-upv-45f464ae-50be-441b-b7ff-a261fba5028e-partial-20261116T060613Z.zip
```

- Tamaño local: **11,086,810 bytes**; 11,163 archivos originales empaquetados.
- SHA-256: `cb25bbcddbd480b758f82dabd59eb27d97178d0a18beab2de47d2f3136800fca`.
- Acompañan `.zip.sha256`, `summary.md`, `summary.csv` y `summary.json`, sin descomprimir el ZIP ni eliminar errores.
- `supporting-evidence/` contiene preparación, perfiles, logs de sesiones y verificación; también se entregan `SHA256SUMS`, README y borrador de actualización del issue.

El ZIP conserva plan, perfil de máquina, snapshot de fuentes, historial de
sesiones, logs y todos los primarios/RunRecords, diagnósticos y auditorías.
Los originales locales permanecen disponibles para consulta y eventual
reanudación. La recuperación local usa el checkout fijado y su dataset; el ZIP
no incluye otra copia de las instancias ni el entorno virtual.

## Recuperación y verificación

Se comprobaron el CRC del ZIP y el SHA-256 de cada archivo contra los originales;
se extrajo a una carpeta temporal y se recalcularon las 1,853 auditorías y los
90 certificados. Las tres tablas se regeneraron idénticas byte a byte.
La [verificación](evidence/cesar-evaluation-20261116/verification.json) conserva
la procedencia y el resultado de esa recuperación.

Además, se ejecutó `combine` del commit fijado sobre una extracción nueva del
mismo ZIP local, sin lanzar solvers. Para reproducir tras descargarlo en un
checkout de la revisión fijada, usar una carpeta nueva de extracción y una
ruta de salida inexistente; `ZIP`, `RESTORED` y `CHECK` son rutas elegidas por quien recupera:

```bash
sha256sum -c "$ZIP.sha256"
.venv/bin/python -m zipfile -e "$ZIP" "$RESTORED"
.venv/bin/python -m src.cli.distributed_campaign combine \
  --plan experiments/configs/distributed-fhcp-10x60.json \
  --inputs "$RESTORED/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-cesar-upv" \
  --output "$CHECK"
```

El archivo `.zip.sha256` referencia el nombre del ZIP: ejecutar su comprobación
desde la carpeta donde estén juntos ZIP y checksum, conservando sus nombres.
`combine` informó `1853/60060`, 90 éxitos, tres grafos distintos y dos errores.
El denominador 60,060 pertenece al plan del equipo completo: los otros cuatro
miembros aparecen ausentes y pendientes; no se combinó esta entrega con la suya.

En #94 se recuperó el paquete de Drive, se comprobó su SHA-256 y se auditó
junto con las otras cuatro entregas; las celdas coinciden con el resumen original.
`graph153` conserva sus siete combinaciones pendientes, fuera del alcance aceptado.

## Limitaciones y alcance aceptado

Se trata de un corte de una cola asignada, detenido por decisión del responsable,
no de una selección representativa ni de una campaña completa sobre los 1001
grafos. Se conservan presupuestos, semillas, hardware y errores para interpretar
el corte. No se normalizan tiempos entre máquinas ni se atribuye superioridad
general a una familia.

Esta entrega aporta tres grafos distintos al total conjunto de 14. Su alcance
parcial está aceptado; #94 registra la recuperación, agregación y decisión de
cierre sin alcanzar la meta original de 60 ni completar por ello M6.

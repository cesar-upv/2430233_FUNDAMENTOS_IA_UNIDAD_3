# Evaluación distribuida de Eder · avances de ejecución

> **Estado al cierre de #94 (17 de noviembre de 2026):** este corte ya fue recuperado y agregado con las cinco entregas. El alcance parcial fue aceptado por Arturo. [Resultados conjuntos y decisión de cierre](distributed-evaluation.md). Las referencias a pendientes dentro de las sesiones siguientes describen su estado histórico.

**Responsable:** Eder Omar Zúñiga Zavala · @KirbyStone69.
**Seguimiento:** [issue #86](https://github.com/ZapataFrame/FHCP-Challenge/issues/86).

La sesión del 14 de noviembre de 2026 usó el commit
`19ac5eaa46fbacc5a034dae6d14befbf171928db` y el plan 10×60
`45f464ae-50be-441b-b7ff-a261fba5028e`, con SHA-256 canónico
`348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.

| Métrica | Valor |
| --- | ---: |
| Grafos evaluados con los 60 intentos conciliados | 1 (`graph4`) |
| Intentos conciliados | 60 de 11,700 |
| Intentos pendientes al cierre de sesión | 11,640 |
| Grafos distintos con ciclo certificado | 0 |
| Intentos agotados por límite del solver | 60 |
| Errores, timeouts externos e interrupciones | 0 |
| Mejor costo observado en `graph4` | 1 arista faltante |
| Duración de pared de la sesión | 1 h 00 min 28.55 s |

Se ejecutaron GA, SA, AS, ABC, DE y PSO con las semillas 1001–1010.
Cada proceso tuvo hasta 60 s de búsqueda y un límite externo de 120 s.
El ejecutador auditó los 60 resultados. Agotar el presupuesto deja la
búsqueda sin éxito certificado en esos intentos. La reanudación conserva
los 60 primarios y continúa en `graph9`.

## Entorno y verificaciones

- AMD Ryzen 5 4600G, 21.31 GiB de RAM física, Debian 13 x86_64,
  kernel `6.12.113+deb13-amd64`.
- CPython 3.14.10 con GIL, NumPy 2.5.4 y pip 26.3.
- `python -m pip check` sin incompatibilidades.
- `python -m pytest -q -W error tests/test_distributed_campaign.py` con 48 pruebas aprobadas.
- `distributed_campaign check` validó los 195 grafos asignados.
- La suma SHA-256 del ZIP coincidió y `unzip -tq` comprobó su integridad.

## Evidencia y alcance

El ZIP parcial `FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e-partial-20261115T002828Z.zip`,
su archivo `.sha256` y los tres resúmenes ya están en la carpeta de entrega
personal indicada en el issue #86.

SHA-256 del ZIP: `444aaa82a880d24e739370dc083661088cb51447018d743fef110d832febe232`.

La evaluación continúa en el mismo equipo. Los tiempos describen esta
máquina y la carga observada en esta sesión. La agregación del equipo
requiere mantener la procedencia por equipo al interpretar las duraciones.

## Segunda y tercera sesión

| Grafo | Intentos conciliados | Ciclos certificados por intento |
| --- | ---: | ---: |
| `graph4` | 60/60 | 0 |
| `graph9` | 60/60 | 0 |
| `graph14` | 60/60 | 9 |
| `graph20` | 6/60 | 0 |

Al cierre de la tercera sesión se conciliaron **186 de 11700 intentos**.
Quedaron **11514 pendientes**. Los nueve éxitos corresponden a ABC en
`graph14` y cuentan como **un grafo distinto resuelto**. Las semillas
certificadas fueron 1001, 1002, 1003, 1004, 1005, 1006, 1008, 1009, 1010.
Los otros 177 intentos agotaron el presupuesto y no hubo errores.
La tercera sesión duró 60 min 40.39 s de pared.

El [issue #86](https://github.com/ZapataFrame/FHCP-Challenge/issues/86) indica la
carpeta personal donde se archivaron los resúmenes de la sesión 3 y
`FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e-partial-20261115T035134Z.zip`. El SHA-256 del ZIP es `602f276f2d3ddb013c83d981848112d8c654d4055fa05096e013ef05bc451908`.
Se verificó el checksum, se extrajo el ZIP y el comando oficial `combine`
releyó y auditó los 186 intentos de la entrega individual. La agregación
con los otros integrantes sigue pendiente.

## Corte de entrega del 15 de noviembre

La ejecución se pausó a las 18:21, hora de Ciudad de México, después de
conciliar el intento de PSO con semilla 1008 en `graph106`. Al corte
quedaron **1,188 de 11,700 intentos registrados** y **10,512 pendientes**.
Hay 19 grafos con sus 60 intentos conciliados y 48 de 60 para `graph106`.

| Grafo certificado | Éxitos por algoritmo | Éxitos por intento |
| --- | --- | ---: |
| `graph14` | ABC 9/10 | 9 |
| `graph56` | ABC 1/10 | 1 |
| `graph79` | GA 10/10, SA 3/10, ABC 10/10, DE 10/10, PSO 10/10 | 43 |
| Total | 3 grafos distintos | 53 |

Hubo 1,134 agotamientos y un intento interrumpido anteriormente
(`graph74`, GA, semilla 1007). Se conservó su registro. La pausa de
entrega ocurrió entre intentos y no añadió otra interrupción de solver.

El paquete acumulado `FHCP-evaluation-KirbyStone69-45f464ae-50be-441b-b7ff-a261fba5028e-partial-20261115T235207Z.zip`,
su archivo `.sha256` y los tres resúmenes `summary-1188` están en la
carpeta de Drive indicada en el issue #86. El SHA-256 del ZIP es
`27be57458f2b653af83a3e7d1170af44bbac327ff88c0373965eb3d19ae9027d`.
El comando oficial `combine` recuperó los 1,188 intentos del ZIP y
reprodujo los conteos de errores, éxitos y grafos resueltos.

El corte individual aporta tres grafos a la meta del equipo.
La entrega fue aceptada y agregada en #94; se mantienen los 12 pendientes
de `graph106` fuera del alcance de esta entrega.

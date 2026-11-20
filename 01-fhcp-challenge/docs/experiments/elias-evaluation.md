# Evaluación distribuida FHCP de Elías

> **Estado al cierre de #94 (17 de noviembre de 2026):** este corte ya fue recuperado y agregado con las cinco entregas. El alcance parcial fue aceptado por Arturo. [Resultados conjuntos y decisión de cierre](distributed-evaluation.md). Las referencias a pendientes dentro de las sesiones siguientes describen su estado histórico.

**Responsable** Elías de Jesús Zúñiga de León · @ELIASDEJESUSZUNIGADELEON.

**Seguimiento** [Issue #87](https://github.com/ZapataFrame/FHCP-Challenge/issues/87).

## Revisión y entorno

La evaluación usa un checkout limpio fijado en
`19ac5eaa46fbacc5a034dae6d14befbf171928db` y el plan compartido
[`distributed-fhcp-10x60.json`](../../experiments/configs/distributed-fhcp-10x60.json).
El UUID es `45f464ae-50be-441b-b7ff-a261fba5028e` y el SHA-256 canónico es
`348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.

- AMD Ryzen 5 7535HS, 6 núcleos, 12 procesadores lógicos y 15.21 GiB de RAM.
- Windows 11 Home x86_64, compilación 26300.
- CPython 3.14.10 estándar con GIL, NumPy 2.5.4, pip 26.3 y pytest 9.2.0. Se
  instalaron las ruedas binarias de `requirements-dev.txt` en un entorno nuevo.

`pip check` reportó `No broken requirements found.`. El comando `check` verificó la
instalación, el plan y los hashes de los 195 grafos asignados. Las 48 pruebas
de `tests/test_distributed_campaign.py` pasaron con `-q -W error` y
`PYTHONUTF8=1`. La primera corrida registró dos fallos de lectura de texto con la
codificación local y un agotamiento del presupuesto sintético de 200 ms en GA.
Se conservó su salida y se repitieron las pruebas antes de empezar la evaluación.
[Registro de preparación](https://github.com/ZapataFrame/FHCP-Challenge/issues/87#issuecomment-6903156455).

## Protocolo

GA, SA, AS, ABC, DE y PSO usan las semillas 1001–1010. Cada intento dispone de
hasta 60 s de solver y 120 s por proceso, incluida la carga. El ejecutador admite
un intento a la vez y reanuda desde el primer pendiente. La cola de Elías
consta de 11,700 intentos, 60 por cada grafo asignado. Los registros de rutas,
errores, agotamientos e interrupciones se conservan en los originales.

La certificación se realiza con el validador independiente. Los éxitos de
varias semillas o algoritmos cuentan una sola vez para el objetivo de 60
grafos distintos del equipo. Agotar el presupuesto deja abierta la existencia
del ciclo. Los tiempos describen este equipo y su carga observada. La agregación
conserva el entorno de cada integrante para interpretar las duraciones.

El [procedimiento de ejecución y reanudación](distributed-campaign-issues/ELIASDEJESUSZUNIGADELEON.md)
se aplica en el checkout fijado.

## Primera sesión del 15 de noviembre de 2026

| Métrica | Resultado observado |
| --- | --- |
| Grafo con todos sus intentos conciliados | `graph5` |
| Intentos conciliados | 60 de 11,700, diez por algoritmo |
| Pendientes | 11,640 intentos en 194 grafos, desde `graph10` |
| Ciclos certificados | 0 por intento, 0 grafos distintos |
| Agotamientos por tiempo de solver | 60 |
| Errores, timeouts externos e interrupciones de intentos | 0 |
| Mejor costo | 1 arista faltante |
| Tiempo del primer inicio al último fin de proceso | 1 h 00 min 29.34 s |

Después de conciliar los 60 intentos y guardar las tres tablas, Windows rechazó
la ruta del archivo temporal que guarda el historial de la sesión. La ruta tenía
264 caracteres y el coordinador salió con código `2`. El ZIP incluye el error
original en `coordinator-close.log` y los tiempos derivados de los registros del
primer y último intento en `session-01-observation.json`. El archivo oficial de
historial de esa sesión quedó sin generar.

Se trasladó la salida a la carpeta hermana corta `ev87` dentro de `.tools`.
Los hashes de los 403 archivos originales coincidieron antes y después del
traslado. La ruta temporal prevista para guardar el historial quedó en 208
caracteres. Para reanudar desde el checkout fijado en este equipo, se usa la
salida trasladada y el mismo presupuesto:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -u -m src.cli.distributed_campaign run --plan experiments/configs/distributed-fhcp-10x60.json --member ELIASDEJESUSZUNIGADELEON --max-session-minutes 60 --output '..\ev87\distributed-45f464ae-50be-441b-b7ff-a261fba5028e-ELIASDEJESUSZUNIGADELEON'
```

La comprobación de la ruta trasladada volvió a auditar los 60 primarios e
identificó `graph10`, GA, semilla 1001 como el siguiente intento.

## Evidencia y recuperación

Se publicó el ZIP parcial completo, su checksum y `summary.md`, `summary.csv`
y `summary.json` en la carpeta institucional de Elías. [Carpeta de entrega](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

El ZIP pesa 492,051 bytes y su SHA-256 es
`038d43bcb09d259f45b1cf8ac3823d2e2330d0ef91d4365bd2f015eaa876fa92`.
Se comprobó la integridad de sus 404 entradas y se extrajo a un directorio
separado. `distributed_campaign combine` auditó los 60 intentos desde la copia
extraída y reprodujo todas las celdas del resumen individual. [ZIP parcial](https://drive.google.com/file/d/19KEPHrb7xzLRsRqYjReLMa8LXOkT7VFT/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1CILeJ_fz7M5DZNNlGWEthdIlpOvtwew9/view?usp=drivesdk).

## Segunda sesión del 15 de noviembre de 2026

El ejecutador reanudó en `graph10` desde la ruta corta y conservó los 60
primarios de `graph5`. El grafo `graph10` completó las 60 combinaciones previstas.

| Algoritmo | Intentos de `graph10` | Ciclos certificados |
| --- | ---: | ---: |
| GA | 10 | 2 |
| SA | 10 | 0 |
| AS | 10 | 0 |
| ABC | 10 | 10 |
| DE | 10 | 0 |
| PSO | 10 | 1 |

Los 13 éxitos por intento cuentan como un grafo distinto resuelto. Los otros
47 intentos de `graph10` agotaron el límite del solver.

La sesión concilió 71 intentos nuevos en 1 h 00 min 58.91 s, incluidos 11 de
`graph15`. Terminó con `session_limit`, código `3`, y guardó su historial en la
ruta corta. El acumulado es **131 de 11,700 intentos**, con **11,569 pendientes**.
Se completaron `graph5` y `graph10`. `graph15` queda en 11/60 y la reanudación
continúa con PSO, semilla 1002. Hubo 118 agotamientos del solver, cero errores de
intento, cero timeouts externos y cero interrupciones en el acumulado.

El ZIP acumulado pesa 866,667 bytes y su SHA-256 es
`37f2c3e3f4c4526ce98c28fd5a588d70e87ef76a83f68c89142c6c98c82f4dbd`.
Se verificaron el checksum y las 831 entradas del ZIP. Tras extraerlo,
`distributed_campaign combine` reprodujo las celdas del resumen y volvió a
auditar los 131 intentos, incluidos los 13 éxitos certificados. El checksum y
las tres tablas de la sesión se publicaron con el ZIP en la carpeta de Elías.
[ZIP de la segunda sesión](https://drive.google.com/file/d/1Il9wc2ZPyqVifaHgmYdsS5VkzVgvAD8r/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1FQWdTywzcOFRlOT2zuaAgGcXWPLhYqIZ/view?usp=drivesdk) · [Tablas en Drive](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

La entrega final queda pendiente de las próximas sesiones, el alcance acordado
con Arturo y la verificación conjunta de los cinco integrantes.

## Sesión 03 · 2026-11-15

Se conciliaron **60 intentos nuevos** en 1 h 00 min 30.16 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **191/11,700 intentos**, 3 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 178 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,509 intentos pendientes.

La reanudación continúa con `graph21`, PSO, semilla 1002. Avance parcial en `graph21` 11/60.

| Grafo iniciado | Intentos conciliados | Éxitos certificados |
| --- | ---: | ---: |
| `graph5` | 60 | 0 |
| `graph10` | 60 | 13 |
| `graph15` | 60 | 0 |
| `graph21` | 11 | 0 |

Se publicaron el ZIP, su checksum y las tres tablas del corte. SHA-256 `f10bd50113dabc43c37df0a10f6aaa8787d227ab039ccb0bbc97d56cef32bc30`. Verifiqué el checksum y las 1,192 entradas del ZIP. Después de extraerlo, `combine` volvió a auditar los 191 intentos y reprodujo el resumen. [ZIP acumulado](https://drive.google.com/file/d/1-WaW80uZ53fftDbbU3a5OmrSr0Kp6pXA/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1phqunijPJiUZ4xh6JN_ZR_25k1upGcnF/view?usp=drivesdk) · [Carpeta Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

## Sesión 04 · 2026-11-15

Se conciliaron **60 intentos nuevos** en 1 h 00 min 32.07 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **251/11,700 intentos**, 4 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 238 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,449 intentos pendientes.

La reanudación continúa con `graph26`, PSO, semilla 1002. Avance parcial en `graph26` 11/60.

| Grafo iniciado | Intentos conciliados | Éxitos certificados |
| --- | ---: | ---: |
| `graph5` | 60 | 0 |
| `graph10` | 60 | 13 |
| `graph15` | 60 | 0 |
| `graph21` | 60 | 0 |
| `graph26` | 11 | 0 |

Se publicaron el ZIP, su checksum y las tres tablas del corte. SHA-256 `d0bf395b5f25f3661f4321dec267e7102bb1717fcdf69d153ddb73822bd76751`. Verifiqué el checksum y las 1,553 entradas del ZIP. Después de extraerlo, `combine` volvió a auditar los 251 intentos y reprodujo el resumen. [ZIP acumulado](https://drive.google.com/file/d/1HGAlS3LVdA-12HRYE0rrqvbutkcXxCnK/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1gD3lusWzcd7OFRJem-hU1pvJK9KZRQBs/view?usp=drivesdk) · [Carpeta Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

## Sesión 05 · 2026-11-15

Se conciliaron **60 intentos nuevos** en 1 h 00 min 29.38 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **311/11,700 intentos**, 5 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 298 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,389 intentos pendientes.

La reanudación continúa con `graph30`, PSO, semilla 1002. Avance parcial en `graph30` 11/60.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph26` | 60 | 0 |
| `graph30` | 11 | 0 |

Se publicaron el ZIP, su checksum y las tres tablas del corte. SHA-256 `282c43043b77f19e0bf84914465d2c549599551a639dbac996415422e2fadfa3`. Verifiqué el checksum y las 1,914 entradas del ZIP. Después de extraerlo, `combine` volvió a auditar los 311 intentos y reprodujo el resumen. [ZIP acumulado](https://drive.google.com/file/d/1rPIE4yQwf1G2oCWInAD8VbFR6eLSNQfj/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1QWA8a9me2rXRwFJWwCYTBsTSc6o1jR35/view?usp=drivesdk) · [Carpeta Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

## Sesión 06 · 2026-11-15

Se conciliaron **60 intentos nuevos** en 1 h 00 min 29.13 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **371/11,700 intentos**, 6 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 358 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,329 intentos pendientes.

La reanudación continúa con `graph35`, PSO, semilla 1002. Avance parcial en `graph35` 11/60.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph30` | 60 | 0 |
| `graph35` | 11 | 0 |

Se publicaron el ZIP, su checksum y las tres tablas del corte. SHA-256 `a8b4200e2a5809a532c6da60ecfb05bc9d72bf35347c8836b9a0ef9e96e2ce9f`. Verifiqué el checksum y las 2,275 entradas del ZIP. Después de extraerlo, `combine` volvió a auditar los 371 intentos y reprodujo el resumen. [ZIP acumulado](https://drive.google.com/file/d/1qycssvi59uzG_T1Fyf4VZUYlF2Uaty-x/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1DhJWk0rFXezHW49Wbe91hL-y5T4lUJJb/view?usp=drivesdk) · [Carpeta Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

## Sesión 07 · 2026-11-15

Se conciliaron **19 intentos nuevos** en 0 h 19 min 09.53 s. El ejecutador registró `low_memory` y guardó el historial de la sesión.

Acumulado de **390/11,700 intentos**, 6 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 377 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,310 intentos pendientes.

La reanudación continúa con `graph35`, GA, semilla 1006. Avance parcial en `graph35` 30/60.

El ejecutador pausó entre intentos al detectar menos de 2 GiB de RAM disponible. Los intentos conciliados quedaron guardados.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph35` | 30 | 0 |

Se publicaron el ZIP, su checksum y las tres tablas del corte. SHA-256 `523407de2e23ab831da96314c23db377d6723ba47740c813820c2584aa622d81`. Verifiqué el checksum y las 2,390 entradas del ZIP. Después de extraerlo, `combine` volvió a auditar los 390 intentos y reprodujo el resumen. [ZIP acumulado](https://drive.google.com/file/d/1xpGZnRxuQIt4YZXmgh3NE0nd60-YRLEO/view?usp=drivesdk) · [SHA-256](https://drive.google.com/file/d/1A3YTLtEe8UrMez-QkrxQLjILIzSNmG8V/view?usp=drivesdk) · [Carpeta Elias](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).

## Sesión 08 · 2026-11-16

Se conciliaron **60 intentos nuevos** en 1 h 00 min 28.26 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **450/11,700 intentos**, 7 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 437 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,250 intentos pendientes.

La reanudación continúa con `graph41`, GA, semilla 1006. Avance parcial en `graph41` 30/60.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph35` | 60 | 0 |
| `graph41` | 30 | 0 |

Verifiqué las 2,751 entradas del ZIP y su SHA-256 `734651d303db80f10fb2b3b7c2e13395f9af7e8912a67ddb91c04834359f1c8d`. Después de extraerlo, `combine` volvió a auditar los 450 intentos y reprodujo el resumen. El ZIP, su checksum y las tres tablas quedaron guardados en el equipo.

## Sesión 09 · 2026-11-16

Se conciliaron **60 intentos nuevos** en 1 h 00 min 27.71 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **510/11,700 intentos**, 8 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 497 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,190 intentos pendientes.

La reanudación continúa con `graph46`, GA, semilla 1006. Avance parcial en `graph46` 30/60.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph41` | 60 | 0 |
| `graph46` | 30 | 0 |

Verifiqué las 3,112 entradas del ZIP y su SHA-256 `43cb6117e00ace29f16c5ab7ba547ef5ffa06b4eddd6915f53e292c1cb4e5231`. Después de extraerlo, `combine` volvió a auditar los 510 intentos y reprodujo el resumen. El ZIP, su checksum y las tres tablas quedaron guardados en el equipo.

## Sesión 10 · 2026-11-16

Se conciliaron **60 intentos nuevos** en 1 h 00 min 36.88 s. El ejecutador registró `session_limit` y guardó el historial de la sesión.

Acumulado de **570/11,700 intentos**, 9 grafos completos y 1 grafo distinto certificado. Se registran 13 éxitos por intento, 557 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones. El resto de la cola conserva 11,130 intentos pendientes.

La reanudación continúa con `graph52`, GA, semilla 1006. Avance parcial en `graph52` 30/60.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph46` | 60 | 0 |
| `graph52` | 30 | 0 |

Verifiqué las 3,473 entradas del ZIP y su SHA-256 `6065652d412e7159ac82e9d4700d818c632fc57899d1c63b27de04c44a73ad18`. Después de extraerlo, `combine` volvió a auditar los 570 intentos y reprodujo el resumen. El ZIP, su checksum y las tres tablas quedaron guardados en el equipo.

## Sesión 11 · 2026-11-16

Por solicitud de Elías, se detuvo la campaña al corte de 600 intentos completos. La sesión aportó **30 resultados** en 0 h 30 min 14.00 s, medidos desde el inicio de su primer intento hasta el final del último resultado del corte. El intento siguiente, `graph57-ga-1001`, arrancó antes de que llegara la señal de parada. Su registro parcial quedó en la carpeta original para que el ejecutador lo concilie si se reanuda la campaña.

Acumulado de **600/11,700 intentos**, 10 grafos completos y 1 grafo distinto certificado. El corte registra 13 éxitos por intento, 587 agotamientos del solver, 0 errores, 0 timeouts externos y 0 interrupciones entre sus registros auditados. El resto de la cola conserva 11,100 intentos pendientes.

El próximo registro del plan es `graph57`, GA, semilla 1001. Todos los grafos iniciados quedaron completos.

| Grafo de la sesión | Intentos acumulados | Éxitos certificados acumulados |
| --- | ---: | ---: |
| `graph52` | 60 | 0 |

Verifiqué las 3,654 entradas del ZIP y su SHA-256 `5d02eb32701b6999a3ee54948321dbbc32b4447440348c84c9720a63aade3721`. Después de extraerlo, `combine` volvió a auditar los 600 intentos y reprodujo el resumen. El ZIP, su checksum y las tres tablas quedaron guardados en el equipo.

## Entrega final del corte aceptado

El ZIP de 600 intentos, su SHA-256 y las tres tablas están en
[la carpeta de Elías](https://drive.google.com/drive/folders/1uNyBfrIoGtrQIRzPa-XLjbJPOGR2j7ut).
En #94 se recuperó el [ZIP](https://drive.google.com/file/d/1a7I_tBOMzz51mbZYSOk0jL5dQyn79NdQ/view),
se comprobó el checksum ya registrado y se agregaron los 600 primarios,
con 13 éxitos en graph10. El historial de sesiones y el intento posterior
fuera del paquete se describen en el informe conjunto.

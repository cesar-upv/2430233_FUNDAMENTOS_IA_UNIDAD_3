# Avance parcial de la evaluación FHCP · Arturo · 2026-11-16

> **Estado al cierre de #94 (17 de noviembre de 2026):** este corte ya fue recuperado y agregado con las cinco entregas. El alcance parcial fue aceptado por Arturo. [Resultados conjuntos y decisión de cierre](distributed-evaluation.md). Las referencias a pendientes dentro de las sesiones siguientes describen su estado histórico.

**Responsable:** Junior Arturo Vázquez Leonel · @Arturo2430.

Entrega del corte parcial del [issue #83](https://github.com/ZapataFrame/FHCP-Challenge/issues/83). El cierre de esta entrega individual no implica completar la cola ni alcanzar la meta global. La agregación y decisiones sobre los pendientes continúan en [#94](https://github.com/ZapataFrame/FHCP-Challenge/issues/94).

- Periodo de registros: primer intento 2026-11-14 17:27:25 CST; fin de sesión 2026-11-16 12:22:37 CST (America/Monterrey).
- Duración registrada por el coordinador: **39 h 17 min 17 s**; incluye búsqueda y coordinación de la sesión, no es tiempo medio hasta resolver.
- Plan UUID `45f464ae-50be-441b-b7ff-a261fba5028e`; SHA-256 `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.
- Seis familias, diez semillas (1001–1010), hasta 60 s de solver por intento; cupo externo 120 s.
- **2,417/13,200 intentos admitidos**, incluidos errores; **10,783 pendientes** de la cola personal.
- **40 grafos con sus 60 intentos conciliados**, 1 parcial y 179 sin iniciar.
- **4 grafos distintos certificados** en este equipo: graph6, graph27, graph31, graph96; **72 éxitos por intento**.
- Fin de la sesión: `interrupted`. Errores conservados: **3**.

## Avance por grafo iniciado

| Grafo | Intentos | Éxitos certificados | Pendientes | Errores |
|---|---:|---:|---:|---:|
| graph1 | 60/60 | 0 | 0 | 0 |
| graph6 | 60/60 | 20 | 0 | 0 |
| graph11 | 60/60 | 0 | 0 | 0 |
| graph16 | 60/60 | 0 | 0 | 0 |
| graph22 | 60/60 | 0 | 0 | 0 |
| graph27 | 60/60 | 6 | 0 | 0 |
| graph31 | 60/60 | 2 | 0 | 0 |
| graph36 | 60/60 | 0 | 0 | 0 |
| graph38 | 60/60 | 0 | 0 | 0 |
| graph42 | 60/60 | 0 | 0 | 0 |
| graph47 | 60/60 | 0 | 0 | 0 |
| graph48 | 60/60 | 0 | 0 | 0 |
| graph53 | 60/60 | 0 | 0 | 0 |
| graph58 | 60/60 | 0 | 0 | 0 |
| graph65 | 60/60 | 0 | 0 | 0 |
| graph77 | 60/60 | 0 | 0 | 0 |
| graph82 | 60/60 | 0 | 0 | 1 |
| graph85 | 60/60 | 0 | 0 | 0 |
| graph86 | 60/60 | 0 | 0 | 0 |
| graph93 | 60/60 | 0 | 0 | 0 |
| graph96 | 60/60 | 44 | 0 | 0 |
| graph98 | 60/60 | 0 | 0 | 0 |
| graph103 | 60/60 | 0 | 0 | 0 |
| graph108 | 60/60 | 0 | 0 | 0 |
| graph113 | 60/60 | 0 | 0 | 0 |
| graph115 | 60/60 | 0 | 0 | 0 |
| graph120 | 60/60 | 0 | 0 | 0 |
| graph126 | 60/60 | 0 | 0 | 1 |
| graph130 | 60/60 | 0 | 0 | 0 |
| graph132 | 60/60 | 0 | 0 | 0 |
| graph138 | 60/60 | 0 | 0 | 0 |
| graph146 | 60/60 | 0 | 0 | 0 |
| graph151 | 60/60 | 0 | 0 | 0 |
| graph154 | 60/60 | 0 | 0 | 0 |
| graph160 | 60/60 | 0 | 0 | 0 |
| graph168 | 60/60 | 0 | 0 | 0 |
| graph176 | 60/60 | 0 | 0 | 0 |
| graph177 | 60/60 | 0 | 0 | 0 |
| graph178 | 60/60 | 0 | 0 | 0 |
| graph180 | 60/60 | 0 | 0 | 0 |
| graph185 | 17/60 | 0 | 43 | 1 |

## Avance por algoritmo

Éxitos sobre intentos admitidos en este corte; incluye el grafo parcial y errores.

| Algoritmo | Intentos admitidos | Éxitos certificados | Errores |
|---|---:|---:|---:|
| GA | 403 | 15 | 0 |
| SA | 403 | 4 | 0 |
| AS | 403 | 4 | 0 |
| ABC | 403 | 26 | 0 |
| DE | 403 | 13 | 3 |
| PSO | 402 | 10 | 0 |

## Incidencias y continuación

- `graph82-de-1007`: `interrupted`, returncode `130`; se conserva en el denominador y no se repite automáticamente.
- `graph126-de-1009`: `interrupted`, returncode `130`; se conserva en el denominador y no se repite automáticamente.
- `graph185-de-1003`: `interrupted`, returncode `130`; se conserva en el denominador y no se repite automáticamente.
- Siguiente pendiente según el plan: `graph185`, `PSO`, semilla `1003`.

## Verificación y alcance

Se verificaron hashes del plan, fuentes, snapshot y artefactos guardados; se
recalcularon los costos y se validaron independientemente las rutas de los
intentos guardados. El resumen recalculado coincide con `summary.json` original.
No se lanzaron búsquedas ni se modificaron los resultados originales.

El paquete ZIP conserva los originales de cada intento y las tablas adjuntas
son una agregación de este corte. `verification.json` y `checkpoint.json` de la
entrega registran las comprobaciones y sesiones. Los errores e interrupciones siguen en el denominador; los pendientes no
son fallos. Agotar el presupuesto no demuestra que un grafo no sea hamiltoniano.

Estos resultados corresponden solo a Arturo. No acreditan el total del equipo
ni permiten conclusiones finales entre algoritmos mientras la evaluación siga
parcial. Esta entrega se publica en el repositorio. La agregación conjunta y el
tratamiento de la reserva pendiente se siguen en #94.

## Entorno y preparación

Se utilizó una laptop Victus con Intel Core i5-12450H y 33,293,533,184 bytes
de RAM física (31.01 GiB), CachyOS Linux 7.2.9-2-cachyos x86_64 y glibc 2.44.
CPython 3.14.10 estándar con GIL, NumPy 2.5.4; un proceso a la vez y
hilos nativos fijados a uno. La revisión experimental permaneció en
`19ac5eaa46fbacc5a034dae6d14befbf171928db`.

La preparación conservada acredita 48 pruebas del coordinador aprobadas,
`pip check`, validación `check` de los 220 grafos e inhibición de suspensión.
El preflight del primer intento registró alimentación conectada.

## Sesiones registradas

| Fin UTC | Intentos nuevos | Acumulados | Duración del coordinador (s) | Motivo |
| --- | ---: | ---: | ---: | --- |
| 2026-11-15T15:48:26.738209+00:00 | 1001 | 1001 | 58861.027 | interrupted |
| 2026-11-16T03:38:36.450119+00:00 | 672 | 1673 | 37812.530 | interrupted |
| 2026-11-16T18:22:37.311927+00:00 | 744 | 2417 | 44763.593 | interrupted |

## Paquete y recuperación

[Directorio de entrega](../../experiments/deliveries/issue-83-partial-2417/)
con ZIP, checksum, las tres tablas originales y evidencia estructurada.
El ZIP ocupa 14,872,923 bytes y contiene 14,547
archivos: plan, perfil de equipo, snapshot de fuentes, sesiones, terminal,
intentos, candidatos y auditorías. Los originales locales permanecen intactos.

SHA-256: `def1148bfd3b676f29f42634668dbb25147fbbc89397f8c89be3432b87958cbc`.

Se comprobó el CRC del ZIP y el SHA-256 de cada miembro contra el original.
Tras extraerlo a una carpeta independiente, `combine` del código fijado volvió
a auditar 2,417 intentos y sus certificados. Las 1,320 celdas de Arturo coinciden
con el resumen original. La ejecución de recuperación informó
`2417/60060; éxitos=72; grafos distintos resueltos=4; errores=3`: el denominador
60,060 es del plan del equipo; los otros cuatro integrantes están ausentes en
esta comprobación individual y no se agregaron sus resultados.

Desde el directorio de entrega, para recuperar en un checkout del código fijado
con el entorno y dataset preparados; elegir rutas de salida nuevas:

```bash
sha256sum -c FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e-partial-2417.zip.sha256
python -m zipfile -e FHCP-evaluation-Arturo2430-45f464ae-50be-441b-b7ff-a261fba5028e-partial-2417.zip /tmp/fhcp-arturo-restored
python -m src.cli.distributed_campaign combine \
  --plan experiments/configs/distributed-fhcp-10x60.json \
  --inputs /tmp/fhcp-arturo-restored/distributed-45f464ae-50be-441b-b7ff-a261fba5028e-Arturo2430 \
  --output /tmp/fhcp-arturo-recovery
```

Tras comprobar el checksum y extraer, ejecutar `combine` desde la raíz del
checkout fijado, conservando la ruta absoluta al directorio extraído.

## Limitaciones

El corte incluye 40 grafos con sus 60 combinaciones conciliadas y `graph185`
17/60. No constituye una muestra representativa del challenge. Tres intentos
interrumpidos permanecen en el denominador; no se repitieron automáticamente.
Los 43 intentos restantes de `graph185` y el resto de la cola se conservan como
pendientes para la decisión de alcance en #94. Las duraciones incluyen
coordinación dentro de sesiones y excluyen los descansos entre ellas; no se
normalizan entre equipos ni permiten concluir superioridad general.

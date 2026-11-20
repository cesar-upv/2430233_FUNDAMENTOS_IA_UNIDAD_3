# Agregación del corte final del issue #94

[Informe y reproducción](../../../docs/experiments/distributed-evaluation.md).
[Tablas consultables](tables.md).

`combined-evidence.zip` conserva las salidas oficiales exactas de `combine`:
plan, inventario, filas auditadas y `summary.json`, `summary.csv`, `summary.md`.
Su SHA-256 está junto al ZIP. Los originales de entrada se identifican
en `packages.json`, con URL y checksum.

`by-graph.csv` incluye los 1001 candidatos; `by-member.csv`, los cinco integrantes;
`by-algorithm.csv`, las seis familias por equipo y para todos los equipos, tanto
con todos los registros admitidos como con cobertura de grafos completos.
`attempts.csv` tiene una fila por intento y `totals.json` resume el alcance.

14 grafos distintos certificados; se esperaban aproximadamente 20 al cierre.
La meta original de 60 queda conservada en el plan. Esta entrega se acepta
con alcance parcial, sin nuevas búsquedas ni imputaciones de pendientes.

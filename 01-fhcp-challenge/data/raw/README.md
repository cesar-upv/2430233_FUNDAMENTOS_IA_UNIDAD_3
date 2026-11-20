# Dataset original

Archivos incorporados por el equipo el 2026-10-28, conservados sin modificar:

- `FHCPCS/`: 1001 instancias `.hcp` del FHCP Challenge Set.
- `FHCPCS_sols/`: 1001 archivos de soluciones `.hcp.tou`, con nombres correspondientes a las instancias.

Procedencia declarada en la cabecera de las instancias: FHCP Challenge Set, `http://fhcp.edu.au/fhcpcs`. El equipo proporcionó estos archivos localmente; los nueve grafos y nueve certificados de la [selección de M2](../../docs/decisions/dataset-selection.md) coinciden por SHA-256 con los miembros extraídos de los paquetes oficiales. No se verificó el resto del conjunto contra esa descarga. La página del conjunto está enlazada en el [README del proyecto](../../README.md#el-reto).

Se verificaron el inventario, la correspondencia de nombres y los tamaños para su incorporación a Git. La lectura completa de grafos y la validación independiente de los ciclos siguen pendientes en M3 de ROADMAP. Estos archivos no son resultados medidos de los algoritmos del proyecto.

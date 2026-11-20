---
name: fhcp-graphs
description: Load FHCP graph instances and validate Hamiltonian cycles. Use when implementing graph parsers, vertex mappings, cycle validators or graph fixtures.
---

# FHCP graphs

Leer `docs/sources/assignment.pdf` y los contratos de representación registrados en `docs/decisions/`. Las rutas de esta skill son relativas a la raíz del proyecto.

## Dataset ingestion

Consultar el formato oficial de la instancia seleccionada antes de escribir el parser; no asumir que todo archivo contiene una matriz de adyacencia. Registrar URL, fecha, checksum y formato junto a los datos descargados. Mantener originales en `data/raw/` y transformaciones en `data/processed/`.

Definir si los grafos admitidos son dirigidos, no dirigidos, simples o multigrafos según el dataset inspeccionado. No descartar silenciosamente bucles, duplicados ni encabezados desconocidos. Preservar un mapeo reversible entre etiquetas originales e índices internos y comprobar el número declarado de vértices y las aristas.

## Cycle validation

Acordar una representación canónica: una permutación de n vértices con cierre implícito, o una lista de n+1 elementos que repita el origen. Normalizar solo según ese contrato, sin aceptar ambas formas accidentalmente.

Validar independientemente del solver: tamaño, pertenencia al conjunto de vértices, ausencia de repetidos, cobertura completa, cada arista consecutiva y arista de cierre. Devolver validez y motivo del rechazo. No aceptar fitness cero sin esta comprobación.

Probar un ciclo conocido, ruta repetida, vértice desconocido, vértice faltante, arista interna ausente y cierre ausente. Añadir un grafo no hamiltoniano conocido para comprobar el validador, sin exigir que una heurística pruebe su inexistencia. Las convenciones para grafos vacíos o muy pequeños deben ser explícitas.

Entregar parser y validador con fixtures en `tests/fixtures/`, pruebas pertinentes y el contrato utilizado. No lanzar benchmarks para verificar únicamente parsing.

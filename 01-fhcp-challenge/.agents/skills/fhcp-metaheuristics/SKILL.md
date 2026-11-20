---
name: fhcp-metaheuristics
description: Implement or review GA, SA, ACO, Bee Colony, DE and PSO for Hamiltonian cycles. Use when changing search operators, route representations, fitness or solver termination.
---

# FHCP metaheuristics

Consultar `ROADMAP.md` y los contratos existentes en `docs/decisions/`. Trabajar en `src/algorithms/`; reutilizar las estructuras de `src/graphs/` y la validación de `src/evaluation/` según los contratos adoptados. Todas las rutas son relativas a la raíz del proyecto.

## Shared solver behavior

Establecer o respetar una interfaz con grafo, configuración, fuente de aleatoriedad y presupuesto explícitos. Retornar estado, mejor candidato, evaluación, tiempo y contadores disponibles. Distinguir solución validada, presupuesto agotado y error. No etiquetar agotamiento como inexistencia de ciclo.

Usar una semilla controlable por ejecución; evitar estado aleatorio global que mezcle experimentos. Revisar límites de tiempo y evaluaciones también dentro de bucles de construcción o reparación. Incluir esos costes en el presupuesto documentado.

El fitness debe guiar la búsqueda y tener interpretación explícita. Una opción a evaluar es contar aristas ausentes, incluida la de cierre, en una permutación; no imponerla si existe una decisión distinta justificada. Mantener la comprobación final separada del fitness.

## Algorithm-specific decisions

- GA es la base de control. Elegir cruza y mutación compatibles con permutaciones, o documentar y probar la reparación.
- SA necesita vecindad, regla de aceptación y calendario de temperatura definidos; comprobar estabilidad de la aceptación cerca de temperatura cero.
- ACO debe definir construcción, bloqueo de rutas parciales, evaporación y depósito de feromonas.
- Bee Colony requiere identificar la variante implementada y sus fases; no sustituirla por ACO bajo otro nombre.
- DE y PSO requieren una adaptación discreta explícita, por ejemplo una codificación o secuencia de intercambios justificada. No aplicar operaciones continuas a índices y redondear sin preservar la representación.

Empezar con fixtures y GA antes de la comparación completa. Probar que operadores preservan las invariantes y que una semilla reproduce resultados en condiciones fijas; no fijar tiempos exactos en pruebas. Validar los ciclos devueltos con el validador independiente y documentar cambios de parámetros que afecten comparaciones anteriores.

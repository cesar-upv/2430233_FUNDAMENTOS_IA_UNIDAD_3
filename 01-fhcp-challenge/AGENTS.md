# Project instructions

## Purpose and current state

Resolver y comparar metaheurísticas para ciclos hamiltonianos usando el FHCP Challenge Set. El enunciado está en `docs/sources/assignment.pdf`; el alcance resumido, en `README.md`; el estado de ejecución, en `ROADMAP.md`.

Este repositorio comienza como un esqueleto: no hay código ejecutable, entorno elegido ni resultados. No inventar comandos de instalación, pruebas o ejecución. Al establecerlos, documentar los comandos reales en README y comprobarlos.

## Working conventions

- Nombres de archivos, directorios e identificadores en inglés. Documentación académica y comunicación con el equipo en español. Preservar los nombres de los integrantes.
- Leer el hito relevante de ROADMAP y el código afectado antes de modificar. Actualizar su estado solo con evidencia. Registrar las verificaciones del cambio en el PR; conservar en el repositorio solo los comandos y las limitaciones necesarios para reproducir el proyecto y sus experimentos.
- Registrar decisiones que afecten contratos, stack o protocolo experimental en `docs/decisions/`, con contexto, elección y consecuencias. No exigir una decisión formal para cambios triviales.
- Mantener separado el dominio (`src/graphs`, `src/algorithms`, `src/evaluation`) de la interfaz (`src/cli`). Los algoritmos no deben depender de la CLI ni del informe.
- Conservar `.gitkeep` en carpetas vacías; retirarlo cuando haya contenido versionable. No mostrar esos marcadores en árboles de documentación.
- Antes de editar un checkout existente, revisar su estado y conservar cambios ajenos. No crear commits ni publicar salvo que se solicite.

## Commit convention

Usar Conventional Commits para todos los commits:

```text
type(scope): short summary

Optional body explaining what changed and why.
```

- Escribir el asunto en inglés, en imperativo y sin punto final; procurar un máximo de 72 caracteres.
- El scope es opcional y describe el área afectada, por ejemplo `graphs`, `algorithms`, `benchmark`, `docs` o `project`.
- Usar `feat` para funcionalidad nueva, `fix` para errores, `docs` para documentación, `test` para pruebas, `refactor` para reorganización sin cambio de comportamiento y `chore` para mantenimiento o estructura inicial. Usar `perf`, `build` o `ci` cuando correspondan.
- Para cambios incompatibles, añadir `!` después del tipo/scope o un pie `BREAKING CHANGE: ...`, explicando el impacto y la migración.
- Mantener cada commit centrado en un cambio coherente. Revisar `git diff --cached` y ejecutar `git diff --cached --check`, junto con las verificaciones pertinentes, antes de confirmar. No incluir secretos, temporales ni cambios ajenos a la tarea.

Ejemplos de formato (no implican funcionalidad implementada):

```text
chore(project): initialize FHCP challenge workspace
feat(graphs): add Hamiltonian cycle validation
fix(benchmark): include timeouts in success rate
docs(report): document experimental protocol
```

## Scientific invariants

Una permutación válida no demuestra que exista un ciclo: verificar aristas consecutivas y cierre con un validador independiente del fitness. Agotar el presupuesto de una heurística no demuestra que el grafo sea no hamiltoniano. No presentar estimaciones o ejemplos como resultados medidos.

Preservar datos originales en `data/raw/`, registrar procedencia y no sobrescribir resultados de ejecuciones anteriores. La evidencia experimental debe identificar instancia, algoritmo, configuración, semilla, presupuesto, entorno y versión de código.

## Local skills

Abrir solo la skill pertinente a la tarea. Las rutas siguientes son relativas a la raíz del proyecto:

| Task | Skill |
| --- | --- |
| Ingestar instancias y verificar ciclos | `.agents/skills/fhcp-graphs/SKILL.md` |
| Implementar o revisar metaheurísticas | `.agents/skills/fhcp-metaheuristics/SKILL.md` |
| Diseñar o ejecutar comparativas | `.agents/skills/fhcp-benchmark/SKILL.md` |
| Escribir y compilar el informe | `.agents/skills/fhcp-latex-report/SKILL.md` |

## GitHub issues and milestones

- Consultar issues, responsables, milestones y PR desde la interfaz web de GitHub o GitHub CLI (`gh`), según las herramientas disponibles. El flujo del equipo está en [CONTRIBUTING.md](CONTRIBUTING.md).
- Antes de trabajar, leer el issue completo y sus comentarios, confirmar responsable y milestone, revisar sus dependencias y los criterios de cierre del hito. No asumir que el resumen del roadmap sustituye el issue.
- Limitar cada PR al alcance y los criterios del issue. Si hace falta trabajo adicional ajeno a ese alcance, agruparlo en otro issue y otra PR, explicar sus razones y completar **Overview** y **Criteria** según las plantillas del repositorio.
- Asignar a la persona indicada por el equipo, no a una identidad inventada para el agente. Si cambia el alcance o falta acceso, comunicarlo y conservar el avance verificable.
- Mantener el issue abierto durante la implementación y revisión. Abrir una PR con `Closes #n` solo cuando cubra todos los criterios; usar `Refs #n` para avances parciales. Solicitar las revisiones indicadas y registrar comprobaciones y limitaciones en la PR.
- No cerrar un issue ni un milestone por haber abierto una PR. El cierre del issue se produce al integrar la entrega aceptada en `main`; el hito requiere verificar todos sus criterios y tareas. `Open`/`Closed` de un issue es distinto de `Status` en GitHub Projects.

## Verification and handoff

Verificar las propiedades afectadas por cada cambio. En lógica de grafos, cubrir entrada inválida, permutación, aristas y cierre; en operadores estocásticos, reproducibilidad y preservación de invariantes. No confundir validación estructural de estas skills con validación de su comportamiento.

Al cerrar una tarea, indicar qué cambió, qué se comprobó y qué sigue pendiente. Un hito científico requiere evidencia experimental; la existencia de carpetas o documentación no lo completa.

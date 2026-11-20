# Cómo contribuir

## 1. Elegir una tarea

Revisa el [roadmap](ROADMAP.md) y toma un issue existente. Para proponer otro, usa la [plantilla de issue](.github/ISSUE_TEMPLATE/task.md), completa **Overview** y **Criteria**, y asigna responsable y milestone.

## 2. Crear una rama

Usa `<type>/<issue>-<short-description>`, en inglés y con palabras separadas por guiones. Tipos habituales: `docs`, `feat`, `fix`, `test`, `refactor` y `chore`.

Ejemplo para documentar el tema del issue #1:

```bash
git switch main
git pull --ff-only
git switch -c docs/1-graph-theory
```

## 3. Preparar los cambios

Mantén cada commit centrado en una tarea. Escribe documentación en español y nombres de archivos e identificadores en inglés. Comprueba los cambios y revisa que `git config user.email` corresponda a tu cuenta del equipo.

Los commits siguen [Conventional Commits](AGENTS.md#commit-convention): `type(scope): short summary`, con el resumen en inglés e imperativo.

### Entregables de investigación

Para los issues #1–#6, usa la [plantilla Markdown](docs/templates/research-deliverable.md) y la [guía de citas y capturas](docs/research/README.md). Incluye las entradas del `.bib` compartido y las imágenes junto con el documento.

Siguiendo el ejemplo anterior:

```bash
git add docs/research/graph-theory.md docs/research/references.bib docs/research/evidence/
git diff --cached
git diff --cached --check
git commit -m "docs(research): document Hamiltonian cycle theory"
git push -u origin docs/1-graph-theory
```

## 4. Abrir una pull request

Abre la PR hacia `main` y completa la [plantilla del repositorio](.github/PULL_REQUEST_TEMPLATE.md): **Overview** para explicar el cambio y **Criteria** para comprobar la entrega. Indica qué verificaste; si es investigación, incluye las fuentes.

Vincula el issue con `Closes #1` si lo resuelve por completo o `Refs #1` si es un avance parcial. Asigna al responsable, solicita revisión y atiende los comentarios con nuevos commits en la misma rama. Actualiza el roadmap cuando cambie el estado de la tarea.

## Trabajar con GitHub CLI

El flujo del equipo es leer el issue completo y el hito, confirmar responsable y dependencias, preparar una rama, verificar la entrega y abrir una PR con la plantilla del repositorio para solicitar revisión. El issue permanece abierto hasta integrar la entrega aceptada en `main`; el hito se cierra al cumplir todos sus criterios. Puede hacerse desde la interfaz web de GitHub o con [GitHub CLI](https://cli.github.com/manual/), cuya documentación oficial explica cómo consultar y administrar issues, hitos y PR.

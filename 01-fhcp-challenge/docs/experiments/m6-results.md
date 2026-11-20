# Campaña M6 v3: resultados y recuperación

## Estado de la entrega

**Cómputo completo; respaldos publicados en Drive.** La campaña
`e390b61f-aae4-4248-ba71-4467920d7bac` ejecutó el plan aceptado con el commit
limpio `22994034acb6eb4232fb72489758b6092cb0c626`. La preparación v3 fue aceptada
por el responsable antes de medir, como consta en su decisión. La entrega se
presenta para revisión del #70, con los respaldos disponibles en
[FHCP-results](https://drive.google.com/drive/folders/1nRT-OhkU91qVaIR8cJDyFxrhinlCSLkZ).
El issue permanece abierto hasta integrar la entrega aceptada; el cierre global
de M6 requiere además el #71.

El [resumen medido](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/campaign-summary.md)
incluye resultados por instancia/familia, selección de parámetros, duración y
limitaciones. El [manifiesto](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/manifest.json)
enlaza las cinco fases con sus lotes y análisis originales.

| Fase | Procesos | Agotamiento de evaluaciones | Límite temporal cooperativo | Éxitos |
| --- | ---: | ---: | ---: | ---: |
| Comprobación inicial | 12 | 12 | 0 | 0 |
| Ajuste | 120 | 67 | 53 | 0 |
| Evaluación | 720 | 270 | 450 | 0 |
| Escala | 180 | 0 | 180 | 0 |
| Verificación de reproducibilidad | 12 | 12 | 0 | 0 |

Los 900 primarios de evaluación/escala tuvieron cero éxitos certificados, sin
errores de ejecución ni timeouts externos. Todos permanecen en sus denominadores.
Los seis pares de reproducibilidad coincidieron. La duración de pared fue
7 h 01 min 36 s, incluidas pausas; la suma de procesos fue 6 h 49 min 33 s.
No hay una familia ganadora por tasa de éxito y no se concluye no hamiltonicidad.

Se conservaron dos incidencias de swap en ajuste y dos de alimentación en
evaluación. No se sustituyeron sus intentos. El vaciado temporal de zram y su
reactivación se realizaron mientras la campaña estaba pausada; el siguiente
preflight conservado registra ambos contadores en 491. Las muestras no permiten
atribuir el intercambio a un proceso concreto ni cuantificar toda la interferencia.
La campaña usa nueve instancias seleccionadas; no representa los 1,001 grafos.

## Archivos de respaldo y disponibilidad

La [decisión de almacenamiento](../decisions/campaign-evidence-storage.md)
separa la evidencia versionada del respaldo externo. El
[índice original](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/archive-index-732914c2-7124-4bf1-bd13-b7ec6ce60a9e.json)
declara los cinco `.tar.gz`, sus rutas, hashes, cantidad de miembros y manifiestos.
[artifact-access.json](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/artifact-access.json)
registra `available`, el enlace de carpeta y los cinco enlaces individuales.
La carpeta y sus archivos permiten lectura con una cuenta `upv.edu.mx`.
Se comprobaron nombres y tamaños contra el inventario local. Los hashes SHA-256
del índice permiten verificar cada archivo al recuperar la evidencia.

Para recuperar los archivos, abrir la carpeta o el enlace individual desde
`artifact-access.json`, iniciar sesión con la cuenta institucional y usar la
opción de descarga de Drive. Conservar sus nombres originales y colocarlos
en las rutas de la receta siguiente.

## Recuperación sin ejecutar búsqueda

Usar un clon de la rama de esta entrega y el entorno fijado en el README. El
commit de ejecución `2299403` está en su historial. Para conservar los hashes al
clonar desde Windows, usar `git -c core.autocrlf=false clone ...`; el coordinador
y los comandos siguientes se verifican en Linux.

Después de descargar los cinco archivos, colocarlos con sus nombres originales en:

```text
experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/archives/
```

Restaurar los cinco lotes, sus registros, historiales y análisis:

```bash
.venv/bin/python -m src.cli.benchmark_archive restore experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/archive-index-732914c2-7124-4bf1-bd13-b7ec6ce60a9e.json
```

No ejecutar `benchmark_campaign run` para consultar resultados ni para regenerar
figuras: la campaña ya está completa. El respaldo restaura los bytes originales;
la regeneración siguiente crea un UUID de análisis nuevo y conserva el anterior.

## Regeneración de evaluación y escala

Después de restaurar los crudos:

```bash
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/67191556-cc8d-4612-9517-e9b4cd0a2340/manifest.json
.venv/bin/python -m src.cli.benchmark_analysis experiments/results/22560abf-18ec-4dab-87a9-8e1141f7ed05/manifest.json
```

Cada comando imprime el directorio nuevo con tablas CSV/JSON, procedencia por
intento y figuras PNG/SVG. Los análisis originales versionados son
`d3dcccf3-160d-412a-8d57-f7a0e101ec93` para evaluación y
`2953975a-1886-4c9a-8e89-23c76c2355fd` para escala. El manifiesto de campaña
identifica además los análisis de comprobación inicial, ajuste y verificación.

## Evidencia de verificación

- [Auditoría posterior](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/post-campaign-audit.json):
  1,044 registros, 10,575 hashes de artefactos/historiales y recálculo de aristas
  y cierre de los 1,014 candidatos disponibles; 30 intentos AS en graph1001 no
  terminaron candidato.
- [Pares de reproducibilidad](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/verification.json):
  seis pares coincidentes, sin exigir igualdad de tiempos.
- [Prueba local de recuperación](../../experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac/recovery-check.json):
  cinco lotes restaurados y 4,176 artefactos de sus 1,044 intentos comprobados.
  Se usaron copias locales de los archivos.

Las verificaciones de esta entrega se registran
en la PR. La comparación con publicaciones y el cierre global de M6 corresponden
al #71, y la redacción del informe LaTeX a M7.

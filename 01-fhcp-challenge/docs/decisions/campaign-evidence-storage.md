# Conservación de la evidencia de campaña M6 v3

## Contexto

La campaña `e390b61f-aae4-4248-ba71-4467920d7bac` terminó sus 1,044 procesos.
Los historiales completos, crudos y análisis ocupan varios GiB sin comprimir;
los cinco archivos originales producidos por `benchmark_archive pack` suman
315,259,579 bytes. El mayor archivo, de evaluación, ocupa aproximadamente
268 MiB. GitHub [bloquea archivos superiores a 100 MiB en Git normal](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

El responsable publicó los cinco archivos en la carpeta
[FHCP-results de Google Drive](https://drive.google.com/drive/folders/1nRT-OhkU91qVaIR8cJDyFxrhinlCSLkZ).
La carpeta y los archivos permiten lectura al dominio `upv.edu.mx`. Sus nombres
y tamaños coinciden con el inventario de los respaldos locales.

## Elección

- Versionar los manifiestos originales de campaña/lotes, entradas, congelación,
  selección, auditorías, reseñas de incidencias, tablas y figuras. Conservar sus
  rutas y bytes para mantener los hashes y la procedencia.
- Mantener los cinco `.tar.gz` originales fuera de Git, en Drive, con acceso
  para el equipo. No volver a comprimirlos ni renombrarlos.
- Versionar el índice SHA-256 original sin modificarlo. El archivo adicional
  `artifact-access.json` registra por separado el estado de publicación,
  nombres, tamaños, hashes del índice local y enlaces a cada archivo de Drive.
- Descargar después cada archivo en la ruta exacta declarada por el índice y
  usar la herramienta existente de restauración. El comando valida SHA-256 y
  rechaza sobrescrituras incompatibles.
- Conservar la prueba de recuperación y regeneración desde un clon limpio con
  copias locales del respaldo. El comando valida los hashes al restaurar.

Se consideran como alternativas Git LFS y adjuntos de una release; esta entrega
no configura esos servicios ni publica el respaldo allí. La herramienta de
restauración conserva su contrato y no incorpora credenciales ni una dependencia
para descargar Drive.

## Consecuencias

La PR puede consultarse sin descargar los crudos, pero una auditoría o
regeneración completa los requiere. Los enlaces permiten acceder al respaldo
externo y la PR presenta la entrega del #70 para revisión. El cierre del issue
corresponde a la integración aceptada en `main`. Se conservan los crudos locales,
los historiales y los intentos
que coincidieron con incidencias de swap o alimentación.

La receta de recuperación y el estado de entrega están en
[M6: resultados y recuperación](../experiments/m6-results.md).

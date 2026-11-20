---
name: fhcp-latex-report
description: Write the FHCP academic report and integrate a supplied LaTeX template with traceable experiment tables, figures and references. Use for report drafting, template integration and PDF verification.
---

# FHCP LaTeX report

Leer `docs/sources/assignment.pdf`, `ROADMAP.md` y la evidencia disponible en `experiments/results/`. Todas las rutas son relativas a la raíz del proyecto. Mantener el informe en español y nombres de archivos en inglés.

## Content and provenance

Cubrir definición de grafo y ciclo hamiltoniano, representación, fitness, algoritmos, protocolo experimental, tablas y gráficos de tasa de éxito y tiempo, contraste FHCP, conclusiones y limitaciones. Distinguir requisitos del enunciado, decisiones del equipo y resultados medidos.

Usar fuentes académicas y documentación primaria verificables para afirmaciones técnicas. Registrar bibliografía en `docs/latex/bibliography/`. No inventar DOI, citas, resultados o datos de los integrantes. Marcar información sustantiva ausente como `[PENDIENTE]`.

Reutilizar las agregaciones del benchmark para tablas y figuras; conservar la referencia a la ejecución y configuración que las produjo. No transcribir números manualmente si existe una exportación reproducible.

## Template integration

La plantilla todavía no fue proporcionada. Se puede preparar contenido en `docs/latex/sections/`, pero no inventar una plantilla institucional ni dar por terminada la maquetación. Cuando llegue, inspeccionar clase, motor, estructura y bibliografía antes de modificarla. Conservar sus archivos en `docs/latex/template/` y adaptar el punto de entrada a su organización real.

Guardar figuras y tablas en sus directorios correspondientes. Mantener temporales de compilación en `docs/latex/build/`, ignorado por Git. Documentar el comando real después de verificar el motor y las herramientas disponibles.

Compilar, comprobar referencias/citas sin resolver y errores de maquetación, renderizar el PDF e inspeccionar páginas, tablas y gráficos. Si falta compilador o plantilla, indicar exactamente qué quedó sin verificar. No considerar una compilación exitosa como sustituto de la revisión visual ni como validación científica.

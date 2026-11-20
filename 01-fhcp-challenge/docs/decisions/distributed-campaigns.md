# Evaluación experimental FHCP

> **Cierre posterior:** el [corte aceptado del #94](distributed-evaluation-cutoff.md) conserva este plan y limita la entrega a 7,383 intentos y 14 grafos resueltos. La expectativa aproximada de 20 se registró al cierre; la meta original de 60 no se alcanzó. Las decisiones de preparación siguientes mantienen su contexto histórico.

## Elección y alcance

El responsable solicita conservar los algoritmos actuales y buscar al menos
60 grafos distintos con ciclos certificados, por cualquier algoritmo. Se define
una cola de 1001 candidatos, incluidos los grafos medidos en la campaña de siete
horas, repartida entre integrantes. No es obligatorio agotar la cola. Se fija
**10 semillas (1001–1010), un intento por semilla/grafo/algoritmo y hasta
60 segundos de solver por intento**.
No se limita por evaluaciones. Un éxito certificado termina antes; agotamientos
y errores se conservan sin reintentar automáticamente. El cupo externo de
proceso es 120 s incluidos arranque/carga, para recuperar bloqueos.

Agotar toda la cola sería 60,060 intentos y hasta 3,603,600 segundos de búsqueda
(1001 horas acumuladas), más sobrecarga. Para el reparto solicitado (220 grafos
para Arturo, 196 para Zapata y 195 para los restantes), los techos de búsqueda
son 220 h, 196 h y 195 h, respectivamente, si se ejecuta cada cola entera.
Evaluar 60 grafos suma hasta 60 h acumuladas; conseguir 60 resueltos puede requerir
probar más de 60. No se presenta ese presupuesto como duración garantizada.

Se trabaja por sesiones y se combinan resultados para revisar el objetivo global.
El contador de grafos resueltos deduplica IDs, aunque varios algoritmos encuentren
ciclo en el mismo grafo. Es un objetivo global, no por integrante. No existe una
parada distribuida automática: los responsables coordinan el fin de las sesiones.
Se completan los seis algoritmos de cada grafo iniciado para evitar omitir métodos
porque otro ya resolvió. Los pendientes no son intentos fallidos. Se conservan todos los fallos de la
búsqueda y las 10 repeticiones de cada método, no solo los 60 grafos resueltos.

No se modifica ningún operador en `src/algorithms/`. Se usan los parámetros
resueltos de `search-enhanced-v3-presets.json`, congelados dentro del plan.
No se reutilizan como nuevos intentos los resultados M6 ni los exploratorios.

## Catálogo, reparto y versión

`fhcp-catalog.json` agrega un catálogo de los **1001 archivos originales**,
con SHA-256, tamaño, número de vértices y aristas obtenidos con el parser estricto
existente. Conserva la procedencia del archivo oficial del manifiesto original;
su construcción no lee tours. No sustituye `fhcp-instances.json`: las nueve
instancias y contratos históricos conservan su revisión. La CLI solo usa el
catálogo completo cuando se pasa `--catalog` explícitamente.

Cada grafo se asigna exactamente una vez. Su responsable ejecuta las seis
familias y todas las semillas en el mismo equipo. El reparto ordena por n+m. Sin cuotas, balancea conteos y suma n+m; con
`--member-graphs`, respeta la cuota explícita y balancea el remanente entre los
demás, eligiendo por fracción de cuota cubierta y carga aproximada por cuota.
El responsable pidió 220 grafos para su equipo; el remanente de 781 se divide
en 196/195/195/195. n+m es una aproximación para distribuir tamaños, no un modelo
validado de duración.

Una preparación central genera un único plan con UUID y digest canónico:
catálogo y hashes de los grafos, asignaciones, parámetros, semillas, presupuestos,
inventario SHA-256 de todas las fuentes y runtime Python/NumPy/GIL/arquitectura.
Los integrantes reciben **el mismo archivo**, no regeneran uno cada uno.
Los finales de línea de fuentes/catálogos se fijan a LF y los originales raw
se excluyen de conversión para conservar los hashes en Windows y Linux.

La ejecución comprueba fuente, runtime, catálogo y archivos asignados antes
de empezar; comprueba nuevamente la instalación antes de cada intento. Se
conservan el plan, snapshot de fuentes y perfil de máquina. La identidad del
equipo y del integrante se mantiene al reanudar. La evidencia CLI registra
además el commit y los cambios locales; los hashes de fuentes identifican el
código medido incluso antes de su publicación. La entrega al equipo requiere
una revisión publicada que contenga estos archivos.

## Ejecución, pausas y recuperación

Se ejecuta un proceso a la vez, con hilos nativos fijados a uno antes de importar
NumPy en el hijo. Se conservan afinidad observable, plataforma, recursos y
perfil de máquina. No se fuerza un CPU lógico común entre equipos diferentes.
Dos coordinadores del mismo entorno Python se excluyen mediante un bloqueo
del sistema operativo; esto no acredita aislamiento de otras aplicaciones.

Una reserva durable (`intent.json`) precede al lanzamiento. `stdout.json` es
el RunRecord original con la ruta, sin duplicar cada ruta en otra copia;
`stderr.log` conserva los diagnósticos. Se registran salida, duración del proceso,
muestras antes/después y `audit.json` independiente con hashes de artefactos.
El padre mata y espera al proceso si vence el cupo externo. Un Ctrl+C termina
el hijo y conserva el intento; se guardan resúmenes e historial de sesiones.

Al reanudar se revisan hashes y se recalculan las auditorías guardadas. Un
intento reservado sin salida final se conserva como interrumpido y **no se
repite automáticamente**. Se comprueba que no siga vivo su proceso antes de
auditarlo; una interrupción entre el lanzamiento y el registro del PID requiere
esperar el cupo externo. El archivo de bloqueo no se borra: el bloqueo del SO
se libera al salir o morir el coordinador. No eliminar directorios de intentos.

Se pausa antes del siguiente intento si se detecta desconexión de corriente,
menos de 2 GiB de RAM disponible o menos de 1 GiB de disco. Son umbrales de
pausa, no estimaciones del consumo máximo. Las observaciones desconocidas se
conservan como nulas. No se altera swap, gobernador, prioridades ni ajustes
persistentes de energía. `--max-attempts` y `--max-session-minutes` permiten
sesiones parciales sin cambiar el plan. El límite de sesión se comprueba antes
de admitir un proceso; el que ya empezó puede consumir su cupo externo.

Windows pide bloqueo temporal de suspensión por inactividad y lo restaura al
salir; Linux utiliza `systemd-inhibit` en la receta. La suspensión manual, el
apagado, cierre de tapa y cierre de terminal requieren la recuperación anterior.
La implementación Windows usa biblioteca estándar y no depende de `taskset`,
`/proc` ni rutas `.venv/bin`. La versión histórica 15×30 pasó sus 45 pruebas, incluida CLI real
con grafos sintéticos, en Ubuntu 24.04 y Windows Server 2025 en
[CI](https://github.com/ZapataFrame/FHCP-Challenge/actions/runs/43566640381).
Esto comprueba integración y recuperación; cada integrante debe verificar su
instalación y recursos antes de medir FHCP. No se acredita macOS.

## Certificación, agregación y entrega

La auditoría exige identidad, semilla, parámetros, presupuesto y hashes de
componentes coincidentes con el plan. Recalcula el costo y valida cada candidato
con `src/evaluation`; para contar un éxito exige además certificado dentro del
plazo en el RunRecord. Un timeout externo conserva el stdout parcial como error,
sin convertirlo en éxito. Los errores e interrupciones siguen en el denominador;
los intentos aún no admitidos quedan pendientes. Un costo positivo no demuestra
que el grafo carezca de ciclo.

Los resúmenes JSON/CSV/Markdown muestran por grafo y algoritmo intentados,
pendientes, éxitos sobre 10, errores, timeouts, costos mínimo/mediano disponibles
y duración media de proceso de todos los intentos con tiempo disponible.
Esta media incluye censura y errores y no es tiempo medio hasta resolver.
Los resúmenes se actualizan cada 25 intentos y al terminar o pausar una sesión.

La combinación vuelve a comprobar snapshots, artefactos y candidatos, rechaza
miembros duplicados o planes distintos y conserva los ausentes como pendientes.
`inputs.json` identifica perfiles e inventarios de auditorías y `attempts.jsonl`
conserva las filas efectivamente agregadas. No se normalizan tiempos entre
hardware diferente: las seis familias de un grafo comparten equipo, pero las
comparaciones globales requieren estratificar por equipo y tamaño.

El empaquetado produce un ZIP64 comprimido y su SHA-256, fuera del directorio de
origen, sin reemplazar un ZIP previo. Los crudos locales quedan fuera de Git.
`handoff` genera borradores de issue por integrante, con asignación y comandos,
sin publicar issues ni enviar mensajes. El seguimiento y la aceptación de cada
lote se realizan por separado del cierre histórico de M6. Los
[issues de esta evaluación](../experiments/distributed-campaign-issues/README.md)
enriquecen los borradores genéricos con la revisión congelada, instalación,
carpetas personales ya creadas en Drive y obligaciones de entrega final.
Cada integrante sube manualmente ZIP, SHA-256 y las tres tablas de resumen a
`FHCP-results/FHCP-evaluation/<integrante>`; conserva los crudos locales y enlaza
la entrega en su issue. Los originales M6 quedan en `M6-original-prueba-inicial`.

## Configuración vigente

El responsable fija 10 semillas y 60 s por intento, sin corte por evaluaciones.
Las 10,000 evaluaciones de campañas anteriores no forman parte de este plan.
El reparto reserva 220 grafos para Arturo y balancea el resto; el objetivo es
60 grafos distintos certificados entre todos los algoritmos. Se prepara un nuevo
UUID con estas condiciones; no se han iniciado intentos 10×60 en esta preparación.

## Cambio a 10 semillas y 60 segundos

El equipo observó que 30 segundos resultaban insuficientes y solicitó un minuto
por intento. Después redujo las repeticiones de 15 a 10. El plan vigente usa
semillas 1001–1010, hasta 60 segundos de solver y 120 segundos externos por
proceso: conserva un margen adicional de 60 segundos para arranque/carga y
recuperación de bloqueos. Los algoritmos y parámetros se conservan.

Se genera `distributed-fhcp-10x60.json` con otro UUID, digest y snapshot de
fuentes; se mantiene exactamente el reparto de grafos de la preparación anterior.
`distributed-fhcp-15x30.json` se conserva intacto como referencia histórica y
requiere su versión de fuentes anterior. No se cambia el presupuesto dentro de
una evaluación ya iniciada ni se importan sus intentos al plan nuevo.
Reanudar en un directorio de otro plan o combinar ambos debe rechazarse.

Cada grafo representa ahora 60 intentos y hasta una hora de búsqueda, más
sobrecarga. La cola completa suma 60,060 intentos y hasta 1001 horas de búsqueda;
evaluar 60 grafos suma hasta 60 horas acumuladas. Estos techos no acreditan
duración real ni que se alcancen 60 grafos resueltos. Los textos de `prepare` y
`handoff` calculan el presupuesto a partir del plan recibido, sin asumir 30 s.

Los cinco issues fijan la revisión publicada de código y el plan compartido
10×60. Cada equipo comprueba esa instalación antes de ejecutar; editar el texto
de una tarea no modifica el presupuesto del archivo de plan utilizado.

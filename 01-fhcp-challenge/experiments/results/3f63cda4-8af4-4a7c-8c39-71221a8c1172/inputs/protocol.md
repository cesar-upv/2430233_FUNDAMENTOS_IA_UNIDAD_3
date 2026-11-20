# Protocolo M6 v2: entorno real antes de la campaña (#70)

## Contexto y elección

Esta revisión extiende el [protocolo v1](benchmark-protocol.md), sin ejecutar aún
ajuste ni evaluación. El equipo disponible es Intel Core i5-1334U, no el Ryzen
7730U previsto. Se registra otro estrato y `protocol_id=fhcp-m6-v2` antes de medir,
con [configuración nueva](../../experiments/configs/benchmark-v2.json). Los archivos
v1, el humo aceptado y el preflight fallido se conservan sin reinterpretarlos.

Se conservan exactamente las nueve instancias, particiones, doce candidatos,
semillas, repeticiones, presupuestos, supervisor, denominadores, regla de selección,
esquemas, fórmulas y orden de fases de v1. El hash del nuevo protocol_id cambia
las identidades y el orden de ensayos de forma determinista, antes de observar
resultados. La alternativa de afirmar que el entorno anterior sigue disponible
sería incorrecta. Esperar otra máquina no aporta equivalencia con fuentes externas.
No se normalizan tiempos entre equipos ni se mezclan los humos con evaluación.

## Perfil y condiciones

- Intel Core i5-1334U x86_64, 16,430,284,800 bytes de RAM física, Linux CachyOS
  7.3.1-1-cachyos; CPU lógico **10**, sin hermano SMT según sysfs.
- CPython 3.14.10 estándar, NumPy 2.5.4, pip 26.3 y stack de
  `requirements-dev.txt`, que incluye las dependencias de análisis fijadas.
- Afinidad a CPU 10, un solver activo y las cuatro variables nativas a 1.
  Gobernador `powersave` constante, alimentación AC comprobada; registrar perfil
  completo, builds y versiones mediante el manifiesto. Frecuencia/turbo no se
  presentan como constantes físicas.
- Mínimo 4 GiB disponibles antes de cada proceso. Comprobar ausencia de actividad
  de intercambio en preflight mediante delta de `/proc/vmstat`; tener páginas en
  swap no equivale a actividad de intercambio actual. Conservar ambas muestras.
- No lanzar otros solvers, pruebas, builds ni análisis durante la búsqueda.
  El equipo tiene servicios de escritorio: registrar carga y competencia observable,
  sin afirmar aislamiento del sistema operativo. El CPU elegido no tiene hermano
  SMT. Una incidencia de energía, suspensión, intercambio o falta de recursos
  detiene antes de iniciar el siguiente intento, conserva el anterior y requiere
  revisar condiciones antes de reanudar. No elimina mediciones lentas.

La selección no utiliza tours oficiales. La congelación se materializa después de
los 120 primarios auditados y antes de evaluación/escala. Todos esos procesos usan
el mismo commit limpio y perfil. El coordinador de campaña guarda su progreso y
permite continuar ensayos pendientes, sin reintentar automáticamente los iniciados.
La verificación final conserva los seis pares y compara candidato, costo, estado
y contadores; los tiempos e identidades se excluyen.

## Consecuencias y viabilidad

El cupo sigue siendo 1,044 procesos y 28,260 segundos nominales de solver con plazo,
más verificación y sobrecargas; el supervisor suma 34.8 horas nominales. La estimación
de feromona AS en graph1001 sigue siendo 363,093,024 bytes. Se mantiene la reserva
prevista de dos días, al menos 10 GiB de disco para evidencia y el margen de RAM.
La reserva de disco aumenta respecto de v1: los historiales guardan manifiestos
completos por transición y crecen con el número de ensayos. Los archivos de cada
lote se preservarán además en archivos tar.gz con índice SHA-256 verificable,
sin sobrescribir las entradas originales. Son estimaciones; no resultados. La velocidad del Intel no se deduce de la del Ryzen.

La auditoría y exportación se ejecutan entre fases. Todos los intentos, preflights,
congelación, repeticiones, metadatos y análisis se publicarán bajo `experiments/results/`
mediante una entrega posterior de #70. Aceptar esta preparación no cierra #70 ni M6.

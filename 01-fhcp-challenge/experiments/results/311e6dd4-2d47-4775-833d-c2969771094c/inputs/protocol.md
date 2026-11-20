# Protocolo M6 v3: campaña en la laptop i5-12450H (#70)

## Contexto y estado

**Aceptada por el responsable en este chat el 12 de noviembre de 2026;
ejecución pendiente.** El responsable de #70,
Junior Arturo Vázquez Leonel · @Arturo2430, eligió esta laptop y autorizó registrar
la preparación en un commit local. Esta aceptación no implica integración en
`main` ni cierre del issue.
La revisión cambia el equipo de [v2](benchmark-protocol-v2.md); las reglas de
búsqueda y evidencia siguen el [protocolo base v1](benchmark-protocol.md).
La configuración es [benchmark-v3.json](../../experiments/configs/benchmark-v3.json).
Un commit limpio es requisito para iniciar la campaña.

El diagnóstico previo usó solamente graph1/graph2, candidatos c1, semilla 17 y
dos repeticiones, con 2,000 evaluaciones o 5 segundos por intento, en el commit
`9b11b7ea47266bcdf8705a208e51bb55d2a81d49`. Se declara este uso adicional de los
grafos de humo. No se emplearon grafos de ajuste/evaluación ni tours oficiales.
Las mediciones de diagnóstico no se incorporan a primarios de esta campaña.
No se seleccionan parámetros a partir de sus resultados.

La alternativa de reutilizar v2 atribuiría los ensayos a otro equipo. La PC
Ryzen con Windows requeriría además adaptar el coordinador, que depende de
Linux/POSIX. El cambio de equipo se registra antes de ajustar y evaluar.

## Elección y perfil

- `protocol_id=fhcp-m6-v3`. Nueva campaña y nuevos lotes, sin reanudar los UUID
  de v2. Los doce humos y dos primarios de ajuste anteriores se conservan como
  estrato parcial de otro equipo según el [traspaso](../experiments/m6-handoff.md).
- CPU: `12th Gen Intel(R) Core(TM) i5-12450H`, x86_64; RAM física reportada por
  Linux: **33,293,524,992 bytes**. Kernel **7.2.9-2-cachyos**.
- Afinidad al CPU lógico **2**, cuyo hermano SMT es **3**, conforme a sysfs.
  Se usa el mismo CPU que en el diagnóstico, sin elegir otro por resultados
  de búsqueda. No ejecutar trabajo adicional intencional en ese núcleo ni
  otras pruebas, builds o solvers mientras se mide. El escritorio y sus servicios
  permanecen presentes; no se afirma aislamiento ni inactividad garantizada del
  hermano SMT. El manifiesto conserva la carga observable del sistema.
- Gobernador **powersave** constante y alimentación AC durante toda la búsqueda.
  No se cambia el gobernador para acelerar algunos ensayos. Turbo, frecuencia y
  temperatura no se consideran constantes físicas ni se infieren del gobernador.
- CPython **3.14.10** estándar con GIL, NumPy **2.5.4**, pip **26.3** y los pines
  completos de `requirements-dev.txt`, incluidos los de análisis. Un solver
  activo y las cuatro variables de hilos nativos a **1**. El manifiesto registra
  builds, versiones, afinidad y evidencia de hilos; las variables solicitadas no
  sustituyen la comprobación de los hilos observados.
- Al menos **4 GiB disponibles** antes de cada proceso y **10 GiB de disco libre**.
  Preflight de energía, gobernador, suspensión y actividad de swap; páginas
  históricas en swap no equivalen a intercambio activo. Una incidencia conserva
  el intento y pausa antes del siguiente; no hay reintentos automáticos.

La nueva configuración conserva todos los campos de v2 salvo `protocol_id` y
los valores observados de `campaign_profile` para CPU, afinidad, RAM y kernel.
Mantiene las nueve instancias, particiones, doce candidatos, semillas, límites,
repeticiones, supervisor, regla de selección, denominadores, esquemas y fórmulas.
El nuevo ID cambia de forma determinista las identidades y el orden, antes de
observar ajuste o evaluación. La admisión conserva los hashes fijados de v1/v2
y añade el de v3; no permite editar silenciosamente presupuestos ni el perfil.
Los lotes guardan copias del protocolo v3 y del protocolo base v1.

## Preparación, ejecución y recuperación

La CLI mantiene su configuración predeterminada v2 por compatibilidad. Para esta
laptop hay que pasar **`--config experiments/configs/benchmark-v3.json`** de forma
explícita a `check` y `prepare`. `check` solo lee el perfil y toma dos muestras de
recursos: no crea lotes, no ejecuta búsqueda, no sustituye la revisión del
protocolo ni comprueba que el árbol esté limpio. `prepare` y `run` exigen un commit
limpio; el commit y el perfil registrados deben mantenerse en todas las fases.

Después de la aceptación y del commit, `prepare` genera la carpeta UUID nueva.
`run` coordina humo, ajuste completo, auditoría, congelación, evaluación, escala
y verificación. La congelación exige los 120 primarios auditados. Ni el humo
diagnóstico ni los intentos v2 se usan para elegir ganadoras.
Las instrucciones y comandos están en [README](../../README.md#campaña-en-esta-laptop-m6-v3).

El cómputo es local y no utiliza servicios de modelos. Puede ejecutarse en una
terminal externa al chat. Mantenerla abierta, la laptop ventilada, conectada y
sin suspensión. Si el coordinador pausa por una incidencia, conservar el log y
revisar la causa antes de reanudar con la misma carpeta y el mismo commit.
No iniciar otra campaña para ocultar una incidencia o sustituir primarios.

## Consecuencias y viabilidad

Se mantienen **1,044 procesos** y **28,260 segundos nominales de solver con plazo**,
más verificación y sobrecargas; el cupo nominal del supervisor es 34.8 horas.
Se reserva la ventana de dos días prevista, sin deducir duración total de grafos
grandes a partir del diagnóstico de grafos pequeños. La feromona AS en graph1001
sigue estimada en **363,093,024 bytes**; no es RSS máximo medido. El recurso real
debe comprobarse durante la campaña, sin recortar selección ni presupuestos.

Los archivos durables y el índice SHA-256 se producirán después de la auditoría
con `benchmark_archive`, preservando crudos e historiales. Otra máquina, kernel,
build o perfil requiere revisión previa y no completa silenciosamente celdas de
esta campaña. Esta preparación no completa #70 ni M6.

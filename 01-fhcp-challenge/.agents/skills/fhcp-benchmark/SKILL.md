---
name: fhcp-benchmark
description: Design and run reproducible FHCP solver comparisons, aggregate success rates and runtime, and compare published baselines. Use for experiment protocols, run manifests and result analysis.
---

# FHCP benchmark

Leer `ROADMAP.md`, las decisiones experimentales en `docs/decisions/` y los comandos realmente disponibles. Las rutas son relativas a la raíz del proyecto. Si aún no hay solvers ejecutables, elaborar el protocolo y señalar la ejecución como pendiente.

## Before running

Definir instancias, algoritmos, parámetros, repeticiones, lista de semillas, criterio de éxito y límites antes del lote. Separar ajuste de parámetros y evaluación final; identificar cualquier reutilización de instancias. Mantener constantes hardware y condiciones de ejecución cuando sea posible; no competir por CPU entre algoritmos y luego comparar tiempos como si fueran equivalentes.

Guardar configuraciones en `experiments/configs/`. Cada ejecución tendrá un identificador único bajo `experiments/results/`, con configuración efectiva, versión del código o snapshot identificable, cambios locales relevantes, runtime, hardware, checksum de instancia, semilla y presupuesto. Evitar sobrescribir ensayos anteriores.

## Evidence

Registrar estado, tiempo con reloj monótono, iteraciones/evaluaciones disponibles, candidato, resultado del validador y motivo de fallo. Definir qué incluye el tiempo: carga, búsqueda, validación y total. Una permutación o un buen fitness no bastan para declarar éxito.

Conservar todos los intentos, incluidos timeouts y errores. Calcular tasa de éxito con denominador explícito y reportar errores por separado. No presentar el promedio de tiempos solo de éxitos como tiempo general: distinguir tiempos de éxito, duración de intentos y censura por timeout. Mostrar variabilidad entre repeticiones y evitar conclusiones a partir de una sola corrida.

Generar tablas y figuras desde registros guardados, con unidades y cantidad de repeticiones. No introducir precisión, recall o F1 sin definir etiquetas, predicciones y universo de casos; un solver que no encuentra ciclo no constituye una prueba negativa.

## External comparison

Consultar referencias primarias del FHCP y registrar fuente, instancia, versión, hardware y presupuesto disponibles. Si las condiciones no son equivalentes, señalarlo y limitar el alcance de la comparación; no anunciar superioridad general.

Entregar protocolo, comandos ejecutados, registros y agregaciones trazables. Un smoke test acredita ejecución básica, no calidad científica ni rendimiento en el challenge completo.

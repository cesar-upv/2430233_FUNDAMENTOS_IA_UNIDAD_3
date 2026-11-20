# Cierre de la evaluación distribuida con el corte entregado

Fecha: 17 de noviembre de 2026. Seguimiento: #94. Estado: aceptado por Arturo.

## Contexto

El plan congelado `45f464ae-50be-441b-b7ff-a261fba5028e` reservaba 60,060
combinaciones sobre 1001 grafos y fijaba como meta global 60 grafos distintos
certificados. Las cinco entregas individuales son cortes parciales, aceptados
por Arturo y publicados mediante las PR #90–#93 y #95. La recuperación conjunta
certifica 14 grafos en 7,383 intentos, con 300 éxitos por intento y 12 incidencias.

Al solicitar el cierre de #94, Arturo indicó: «Cierra la entrega y documenta
que se esperaba unos 20». Se registra esa expectativa aproximada al cierre,
sin atribuirla al protocolo original ni convertirla en un resultado medido.

## Decisión

Aceptar y cerrar esta entrega con los cinco paquetes existentes. No iniciar
nuevas búsquedas, rellenar combinaciones ni reintentar incidencias. Se esperaban
aproximadamente 20 grafos resueltos; se certificaron 14. Tampoco se alcanzó la
meta original de 60. El plan y las semillas permanecen intactos.

Conservar `graph185` (17/60), `graph104` (5/60), `graph153` (53/60) y
`graph106` (48/60) como parciales. Incluir sus registros en los totales y
mantenerlos fuera de la comparación con cobertura balanceada de 121 grafos.
Las 52,677 combinaciones pendientes no se imputan como fallos y quedan fuera
del alcance aceptado, sin obligación de otra etapa de ejecución.

El inicio de `graph57-ga-1001` descrito por Elías no forma parte de su paquete
de 600 resultados ni de los totales conjuntos; se conserva con el responsable
como evidencia fuera del corte. No se presupone su resultado.

## Consecuencias

La entrega es parcial y descriptiva: 125 grafos iniciados en los paquetes,
121 con sus 60 combinaciones conciliadas, cuatro parciales y 876 sin iniciar.
La cobertura no es una muestra representativa del challenge. Se conservan
datos, errores, hardware y censura temporal. Los tiempos de máquinas distintas
no se normalizan y sus sumas no representan duración calendario del equipo.

Los ZIP originales se preservan, con URLs y SHA-256 en el manifiesto. El cierre
de #94 significa consolidación y aceptación de este alcance; no significa
haber resuelto 20 o 60 grafos ni cerrar automáticamente M6 o el informe final.
Una evaluación futura requerirá su propio alcance y seguimiento.

Resultados, limitaciones y reproducción:
[evaluación distribuida](../experiments/distributed-evaluation.md).

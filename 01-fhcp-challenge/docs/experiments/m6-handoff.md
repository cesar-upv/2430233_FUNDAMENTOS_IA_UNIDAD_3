# Traspaso de la campaña M6 (#70)

La campaña se detuvo a petición del usuario: el cómputo pesado o prolongado lo
realizará otro integrante. **No hay evaluación final ni configuraciones ganadoras.**
#70 y #71 permanecen pendientes; M6 sigue abierto.

## Entregas disponibles

- [PR #73](https://github.com/ZapataFrame/FHCP-Challenge/pull/73): ejecutor y humo oficial de #68, integrados.
- [PR #74](https://github.com/ZapataFrame/FHCP-Challenge/pull/74): auditoría, agregación y figuras de #69, integradas.
- [PR #75](https://github.com/ZapataFrame/FHCP-Challenge/pull/75): revisión previa del entorno v2 y orquestación de #70, integradas antes de medir.
- [Protocolo v2](../decisions/benchmark-protocol-v2.md) y [configuración](../../experiments/configs/benchmark-v2.json): conservan las decisiones de búsqueda de v1.
- [Manifiesto de campaña](../../experiments/results/2c45d216-217a-4a5e-9592-5bc0c1492359/manifest.json),
  [índice de traspaso y hashes](../../experiments/results/2c45d216-217a-4a5e-9592-5bc0c1492359/handoff.json).

La versión ejecutada fue el commit limpio
`2172363a308833e6efc61aa11bc8765ce7811e1e`, con CPython 3.14.10,
NumPy 2.5.4 y las dependencias fijadas de desarrollo/análisis. Se usó el Intel
i5-1334U, CPU lógico 10, sin hermano SMT, Linux 7.3.1-1-cachyos y gobernador
`powersave`, con alimentación AC. Los metadatos completos están en los manifiestos.

## Avance conservado

| Fase | Lote | Estado | Intentos realizados / previstos |
| --- | --- | --- | --- |
| Humo v2 | `9f647b78-40fe-454d-b920-423be2f9cdac` | Completo; 12 agotamientos normales | 12 / 12 |
| Ajuste v2 | `3f63cda4-8af4-4a7c-8c39-71221a8c1172` | Incompleto; 118 ensayos sin iniciar | 2 / 120 |
| Evaluación | Sin crear | Pendiente | 0 / 720 |
| Escala | Sin crear | Pendiente | 0 / 180 |
| Verificación | Sin crear | Pendiente | 0 / 12 intentos, seis pares |

Los dos primarios de ajuste fueron `as-c2`, graph58, semilla 307, y `de-c2`,
graph268, semilla 503. Ambos terminaron por límite temporal cooperativo. Después
de cada uno se detectó actividad de swap global y se pausó antes del siguiente.
No se borraron ni sustituyeron esos intentos. La atribución y duración de esa
interferencia no se conocen. La revisión de la primera incidencia se conserva
como diagnóstico; no acredita aislamiento ni calidad comparativa.

La congelación no se generó porque faltan 118 primarios de ajuste. Estos datos
parciales no permiten seleccionar ganadoras ni publicar una tasa final. El humo
v2 y sus análisis están conservados; no forman parte de la evaluación final.
Los crudos, entradas, diagnósticos e historiales parciales se versionan directamente:
son pocos archivos y no requieren comprimir ni ejecutar más búsqueda para leerlos.

## Continuación por el integrante responsable

1. Leer #70, sus dependencias y los protocolos v1/v2. Instalar las dependencias
   fijadas y disponer de tiempo y recursos: el plan completo tiene 1,044 procesos,
   28,260 s nominales de solver con plazo, más verificación y sobrecargas.
   Son estimaciones; reservar la ventana prevista, AC, RAM y disco.
2. Confirmar **antes de evaluar** el equipo que se utilizará. V2 fija este Intel,
   RAM, kernel, CPU y gobernador concretos. Si cambia el equipo o el perfil,
   proponer y revisar una versión nueva del protocolo/configuración y su admisión
   en el ejecutor. Mantener decisiones de búsqueda, partición y semillas, salvo
   otra revisión previa explícita. No modificar v2 para hacer pasar otro perfil.
3. En otro equipo, crear una campaña nueva bajo la revisión aceptada. Conservar
   estos intentos como estrato parcial anterior, sin mezclarlos con sus nuevos
   primarios, sin convertirlos en reintentos ni elegir configuraciones con ellos.
4. Solo si se conserva exactamente el perfil v2 y su commit limpio, es posible
   recuperar los tres directorios UUID versionados en un checkout aislado del
   commit de ejecución y reanudar la misma campaña. Las carpetas de evidencia deben
   excluirse localmente por sus rutas UUID exactas según el protocolo; no ocultar
   código ni configuraciones. El ejecutor rechaza otro commit/perfil.

Comando implementado de continuación **para ese checkout y perfil exactos**:

```bash
.venv/bin/python -m src.cli.benchmark_campaign run experiments/results/2c45d216-217a-4a5e-9592-5bc0c1492359
```

No se ejecutará aquí de nuevo. La siguiente persona debe revisar primero las
incidencias de swap y restaurar condiciones. El comando conserva los primarios
existentes y solo inicia pendientes. No hay reintentos automáticos. Un reinicio
con otro equipo requiere la revisión y campaña nuevas descritas arriba.

Después: completar y auditar los 120 primarios, congelar con sus hashes y regla
predefinida, ejecutar evaluación/escala y los seis pares de verificación. La
orquestación genera tablas y figuras entre fases. Publicar archivos durables y
su índice con el comando de archivo, recuperar y comprobar desde un clon,
abrir la entrega de resultados con `Closes #70` solo al cubrir todos sus criterios,
revisar antes del merge y continuar el contraste/cierre de #71.

La revisión previa de herramientas pasó 1,296 pruebas. Esa evidencia funcional
no sustituye los resultados científicos pendientes ni permite cerrar M6.

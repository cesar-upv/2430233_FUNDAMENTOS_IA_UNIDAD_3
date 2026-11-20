# Entrega parcial de Zapata · issue #84

Evidencia de los primeros **1,325 de 11,760 intentos previstos** del
[issue #84](https://github.com/ZapataFrame/FHCP-Challenge/issues/84).
Este corte no completa la cola ni el objetivo global. Fue aceptado como
entrega parcial; la recuperación conjunta y el cierre de alcance se registran
en [el informe de #94](../../../docs/experiments/distributed-evaluation.md).
No incluye la campaña histórica 15×30 ni la comparación exploratoria cancelada.

- Responsable: Diego Eduardo Zapata Aguilar · @ZapataFrame.
- Código de ejecución: `19ac5eaa46fbacc5a034dae6d14befbf171928db`.
- Plan: `experiments/configs/distributed-fhcp-10x60.json`.
- UUID: `45f464ae-50be-441b-b7ff-a261fba5028e`.
- SHA-256 canónico: `348df5525871354ff25a60b22ccb8da8d6aba9884de9a3a9b4026feafc0db250`.
- GA, SA, AS, ABC, DE y PSO; semillas 1001–1010; hasta 60 s de búsqueda
  y 120 s externos por proceso; sin límite de iteraciones/evaluaciones.
- Entorno: Intel Core i5-1334U, RAM física de 16,430,288,896 bytes,
  Linux CachyOS, CPython 3.14.10 estándar con GIL, x86_64, NumPy 2.5.4.
  El perfil exacto y las observaciones de recursos están en `machine.json`
  y en los registros originales dentro del ZIP.

## Estado del corte

| Medida | Cantidad |
| --- | ---: |
| Intentos conciliados | 1,325 |
| Éxitos certificados por intento | 72 |
| Agotamientos del presupuesto | 1,247 |
| Errores por interrupción | 6 |
| Intentos pendientes | 10,435 |
| Grafos con sus 60 intentos conciliados | 22 |
| Grafos con ejecución parcial | 1 |
| Grafos sin iniciar | 173 |
| Grafos distintos resueltos | 3 |

Se certificaron `graph2`, `graph23` y `graph90`. Los 22 grafos con todas las
combinaciones conciliadas son `graph2`, `graph7`, `graph12`, `graph17`,
`graph23`, `graph28`, `graph32`, `graph37`, `graph43`, `graph49`, `graph54`,
`graph60`, `graph66`, `graph70`, `graph76`, `graph78`, `graph83`, `graph87`,
`graph88`, `graph90`, `graph94` y `graph99`. Conciliar sus intentos incluye
los errores; no significa resolver esos grafos. `graph104` lleva 5/60.

Las seis incidencias se conservan sin reintentos ocultos:

| Intento | Motivo registrado |
| --- | --- |
| `graph7-as-1006` | `interrupted_without_exit` |
| `graph7-abc-1006` | `interrupted` |
| `graph7-pso-1008` | `interrupted_without_exit` |
| `graph12-abc-1007` | `interrupted` |
| `graph49-de-1001` | `interrupted` |
| `graph104-de-1001` | `interrupted` |

Hay siete registros de sesión. La última finalizó con `FIN: interrupted`.
Las duraciones de proceso disponibles suman 75,443.148 s (20.956 h);
incluyen arranque/carga y no representan tiempo puro de búsqueda ni tiempo
calendario total entre sesiones. Los agotamientos no demuestran ausencia
de ciclo. La meta de 60 grafos distintos es compartida por todo el equipo;
estos tres no permiten determinar el progreso global sin agregar las otras
entregas. No se normalizan tiempos entre equipos.

## Archivos y verificación

Se publican los cinco archivos solicitados: el ZIP original completo, su
`.sha256` y copias exactas de `summary.md`, `summary.csv` y `summary.json`.
El ZIP contiene 7,997 archivos: plan, perfil de máquina, snapshot de fuentes,
sesiones, log, tablas y todos los intentos con sus candidatos y auditorías.
Se conserva el directorio original para reanudar. Este paquete de entrega
es inmutable; una entrega posterior debe tener otro nombre.

El ZIP ocupa 7,581,253 bytes y su SHA-256 es:

```text
a56c43a7949c2633d6096ae8c6420c82beb0f4f7db9c5a9ab43404182c4415f0
```

Con el ejecutador detenido, se verificaron el snapshot contra el plan y los
hashes de cada intento, se recalcularon las auditorías con el validador
independiente y se regeneraron las tres tablas en un directorio temporal:
coinciden byte a byte con las publicadas. Se comprobó el CRC del ZIP,
su inventario completo y el SHA-256 de cada miembro contra el original.
No se lanzaron solvers para preparar esta entrega.

Para comprobar el archivo descargado, desde esta carpeta en Linux:

```bash
sha256sum -c FHCP-evaluation-ZapataFrame-45f464ae-50be-441b-b7ff-a261fba5028e-partial-1325.zip.sha256
```

## Ubicación y aceptación de la entrega

Arturo aceptó el repositorio como ubicación de este paquete, sin exigir una
segunda copia en Drive. En #94 se verificó el ZIP integrado, su checksum,
extracción y auditorías, y se combinó con las otras cuatro entregas. Los
pendientes de `graph104` y la reserva no ejecutada conservan su estado fuera
del alcance aceptado. El cierre individual de #84 y el de #94 no acreditan
cumplir la meta original de 60 grafos. Los ZIP y tablas originales permanecen
sin modificaciones.

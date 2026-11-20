# Auditoría y gráficos de M6 (#69)

## Contexto y elección

El protocolo fija denominadores, intentos y alcances temporales antes de medir.
El análisis debe regenerarse desde esos archivos, conservar contradicciones y
señalar campañas parciales. `src/evaluation/benchmark.py` audita y agrega sin
depender de la CLI; `src/cli/benchmark_analysis.py` coordina entradas y exportaciones.

Se elige Matplotlib 3.11.2 con backend Agg y exportación SVG/PNG. Evita requerir
un servidor gráfico y proporciona diagramas científicos exportables. Se fija el
stack en `requirements-analysis.txt`, separado de los requisitos del solver.
El entorno de desarrollo lo incluye para ejecutar también las pruebas de renderizado.
La alternativa de dibujar SVG a mano evitaría dependencias pero duplicaría ejes,
cuartiles y representación de distribuciones. Añadir pandas/seaborn no es necesario
para el volumen ni las fórmulas acordadas.

Referencias primarias consultadas: [backends de Matplotlib](https://matplotlib.org/stable/users/explain/figure/backends.html)
y [boxplot](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html).
La versión y compatibilidad se comprobaron instalando el archivo fijado y ejecutando
las pruebas con CPython 3.14.10/NumPy 2.5.4 en Linux.

## Contratos y consecuencias

Se consumen `fhcp-benchmark-config/1`, `fhcp-batch-manifest/1` y
`fhcp-run-record/1`. Se contrastan el plan completo, sus entradas e historial,
UUID, hashes, identidad, configuración, presupuesto, módulos, entorno y candidato.
Los conflictos estructurales, duplicados o inventarios distintos rechazan el
análisis. Un intento sin registro válido permanece como evidencia inválida, sin
convertirse en éxito ni desaparecer del denominador. Sin diagnóstico terminal
permanece pendiente. Se recalcula el costo y se recertifica cada éxito mediante
las aristas, sin consultar tours oficiales.

Cada generación crea `analyses/<uuid>/` nuevo dentro del lote, con `analysis.json`
versión `fhcp-benchmark-analysis/1`. Guarda versión/entorno del analizador, hashes
de entradas y salidas, comando, tablas de intentos y resumen CSV/JSON, duraciones,
contadores y figuras por instancia. No cambia el manifiesto ni registros crudos.
Una generación fallida puede dejar un directorio parcial sin `analysis.json`;
solo el manifiesto de análisis completo publica sus salidas verificadas.
Los hashes de gráficos se refieren a los archivos concretos; metadatos y versiones
de renderizado pueden cambiar sus bytes sin alterar las cifras.

Solo los primarios entran en agregaciones. Los reintentos y repeticiones de
verificación se conservan en la tabla de procedencia. La verificación completa
requiere ambos roles previstos. Las tasas de lotes incompletos son cotas inferiores
provisionales con N previsto y cobertura. La desviación binaria usa divisor N-1;
los cuartiles interpolan `(n-1)*q`. Los tiempos se expresan en segundos, con tamaños
de muestra y ausencias, sin sumar validación al solver ni imputar ceros. El tiempo
hasta éxito solo describe éxitos; errores, censura cooperativa y censura externa
con alcance de proceso se separan. No se estima supervivencia ni tiempo esperado
general. Precisión/recall/F1 son N/A conforme al protocolo.

Los gráficos separan instancias, ajuste/humo/evaluación y escala, y muestran N,
estructura documentada, dimensión y presupuesto. Cero éxitos no prueba ausencia
de ciclos. El humo permite comprobar el pipeline; los resultados de campaña
pertenecen al #70 y su contraste externo al #71.

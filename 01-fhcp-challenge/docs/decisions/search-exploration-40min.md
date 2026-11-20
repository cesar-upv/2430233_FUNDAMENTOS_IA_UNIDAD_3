# Prueba exploratoria de las mejoras en una ventana de 40 minutos

El responsable dispone de aproximadamente 40 minutos y solicita 10 semillas en
pocos grafos. Se fijan graph2 (70 vértices), graph48 (338) y graph74 (462), seis
familias y semillas 1001–1010: 180 intentos secuenciales en CPU 2. Las instancias
ya se utilizaron; esta prueba no es evaluación final independiente ni sustituye M6.

Se conservan los parámetros de `search-enhanced-v3-presets.json`, con presupuesto
común de 10 s de búsqueda o 1,000,000 evaluaciones. El límite externo es 12 s por
proceso, incluido arranque. El coordinador admite nuevos intentos hasta cerca de
38 minutos, reservando margen para guardar evidencia; el tiempo de solver nominal
acumulado máximo es 30 minutos. La duración real y los intentos pendientes se
registran, sin prometer que todos terminen dentro de una ventana de pared exacta.

Un timeout externo se registra como error censurado y conserva stdout/stderr;
puede carecer de candidato completo. Un éxito exige la bandera de certificación
dentro del presupuesto y validación independiente de la ruta. Se recalcula el costo
de cada candidato disponible. Errores permanecen en el denominador de 10 semillas
previstas y se reportan por separado; los intentos no iniciados quedan pendientes.
La tabla muestra mínimos y medianas de costos disponibles y número de candidatos
intentados; el CSV añade tiempo medio de proceso de todos los intentos, incluidos
censurados, sin interpretarlo como tiempo hasta encontrar una solución.

Cada invocación crea un UUID, conserva fuentes locales y hashes, configuración,
commit base, entorno por RunRecord, recursos antes/después y resultados originales.
El código puede tener cambios locales y su snapshot permite identificarlos; no
se requiere un commit ni se publica evidencia automáticamente. La inicialización
no usa certificados conocidos. No se modifica la configuración durante el lote.

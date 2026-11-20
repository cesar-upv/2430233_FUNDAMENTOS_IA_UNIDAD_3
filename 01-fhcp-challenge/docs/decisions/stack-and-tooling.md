# Stack y herramientas del entorno mínimo

**Estado:** propuesta para revisión del [issue #15](https://github.com/ZapataFrame/FHCP-Challenge/issues/15), M2, presentada en la [PR #24](https://github.com/ZapataFrame/FHCP-Challenge/pull/24). Linux comprobado y ejecución satisfactoria de Windows reportada por Elías; aceptación del equipo pendiente. Vigente al aceptarse e integrarse en `main`.

**Responsable:** Junior Arturo Vázquez Leonel · @Arturo2430. La comprobación manual en Windows corresponde a **ELIAS DE JESUS ZUÑIGA DE LEON**. Los resultados y las revisiones se registran en la PR vinculada; esta entrega no cierra M2.

## Contexto

M3–M6 necesitan un entorno común para desarrollar lectores, validadores, seis metaheurísticas y experimentos. Se prioriza una instalación pequeña, comprensible y reproducible por el equipo en Linux y Windows de 64 bits. El usuario eligió `venv` y `pip` y pidió comprobación manual de Windows, sin GitHub Actions.

Esta decisión prepara el entorno. No implementa parsers, fitness, validadores, solvers, CLI ni el contrato de resultados del #19. Tampoco presenta mediciones de rendimiento de algoritmos.

## Alternativas

Las valoraciones siguientes son decisiones del proyecto, no resultados de una comparativa experimental.

| Lenguaje | Ventajas para este trabajo | Costo o limitación | Decisión |
| --- | --- | --- | --- |
| Python con NumPy | Permite expresar las reglas de búsqueda de forma legible y disponer de arreglos numéricos con tipos explícitos. | Los bucles de Python pueden ser un cuello de botella; NumPy no acelera automáticamente las operaciones sobre grafos. | Elegido como base común. |
| C++ | Permite controlar almacenamiento y desarrollar bucles compilados. | Añade compilador, configuración de construcción y coordinación entre sistemas al entorno inicial. | Reservado para una optimización futura sustentada con perfiles. |
| Julia | Alternativa orientada al cálculo numérico. | Introduce otro lenguaje y gestor de paquetes; la compilación inicial requeriría un tratamiento explícito en las mediciones. | No se adopta para esta base. |

| Herramienta | Alternativa | Motivo de la elección |
| --- | --- | --- |
| `venv` + `pip` | uv, Conda | Preferencia explícita del usuario y pocos componentes para el entorno mínimo. `venv` aísla los paquetes del proyecto por defecto [S2]; las dependencias se declaran para `pip` [S6]. No se necesita otro gestor. |
| pytest | `unittest` | Se elige pytest para expresar comprobaciones, errores esperados y futuras tablas de casos de forma uniforme. `unittest` evitaría una dependencia de desarrollo, pero se prefiere una sola herramienta de pruebas para el equipo. La versión publicada se documenta en [S4]. |
| Archivos de requisitos con versiones exactas | Rangos abiertos, instalación sin versiones | Se fijan dependencias directas y transitivas del entorno objetivo para evitar que cada instalación resuelva versiones diferentes [S6]. |
| Comprobación manual de ambos sistemas | GitHub Actions | Acuerdo del usuario: Linux se verifica localmente y Elías ejecutará la receta de Windows. La revisión humana queda pendiente hasta recibir esa evidencia. |

## Elección y versiones

Se adopta **CPython 3.14.10 estándar, con GIL, de 64 bits**, y NumPy como única dependencia de ejecución. La publicación oficial identifica la versión de Python y distribuye fuentes e instalador Windows de 64 bits [S1]. Las versiones elegidas de NumPy, pytest y pip existen en sus páginas de publicación [S3–S5]; no se usa una etiqueta móvil como `latest`.

| Componente | Versión | Uso y registro |
| --- | --- | --- |
| CPython | 3.14.10 | Intérprete. `.python-version` registra la elección; **no instala ni selecciona Python por sí solo** con este flujo. |
| NumPy | 2.5.4 | Arreglos numéricos; `requirements.txt`. |
| pip | 26.3 | Instalador dentro del entorno virtual; paso explícito de preparación en README. |
| pytest | 9.2.0 | Ejecución de pruebas; `requirements-dev.txt`. |
| iniconfig | 2.3.1 | Dependencia transitiva de pytest. |
| packaging | 26.3 | Dependencia transitiva de pytest. |
| pluggy | 1.7.0 | Dependencia transitiva de pytest. |
| Pygments | 2.21.0 | Dependencia transitiva de pytest. |
| colorama | 0.4.6 | Dependencia transitiva de pytest **solo en Windows**, mediante marcador `sys_platform == "win32"`. |

Las dependencias transitivas se contrastaron con la declaración oficial de pytest 9.2.0 [S4]. Se fijan las que corresponden a Python 3.14; no se agregan dependencias para intérpretes anteriores. Cambiar una versión exige reinstalar en un entorno vacío, ejecutar las comprobaciones y revisar estos archivos juntos.

Se fija el parche 3.14.10 de la línea acordada porque es una publicación oficial de mantenimiento que incorpora correcciones de seguridad [S1], y se comprobó su instalación junto con las dependencias elegidas. NumPy 2.5.4 aporta los arreglos requeridos sin añadir otra biblioteca numérica; pytest 9.2.0 y pip 26.3 establecen una misma base de pruebas e instalación. La combinación se eligió por disponibilidad y comprobación conjunta en Linux, sin atribuirle ventajas de velocidad frente a otras versiones. El intérprete estándar con GIL reduce las variantes que el equipo debe comprobar; otras compilaciones exigirían una verificación separada.

Se instala desde PyPI con `--only-binary=:all:`: si no existe una wheel compatible, la instalación falla y se revisa el entorno, sin iniciar una compilación implícita. Los requisitos fijan **versiones**, no los bytes de los artefactos: no son un archivo de bloqueo con hashes, y las wheels de Windows y Linux pueden diferir. La reproducción de resultados científicos requerirá además configuración, semillas, presupuesto, plataforma y versión de código en M6.

No se incorporan SciPy, NetworkX, bibliotecas de metaheurísticas, herramientas gráficas ni generadores de informes. Cualquier dependencia adicional deberá justificarse en la tarea que la necesite.

## Compatibilidad con las decisiones aceptadas

Se conservan los contratos integrados de [grafo y ruta](graph-and-route-contracts.md) (#17, PR #22), [fitness](fitness.md) (#18, PR #23) y [selección de instancias](dataset-selection.md) (#16). Elegir Python no altera su semántica:

- El grafo seguirá siendo CSR con vecinos ordenados y compartido entre candidatos. `has_edge` mantiene su búsqueda en la fila más corta; no se supone costo constante ni se introduce una matriz de adyacencia.
- NumPy permite almacenamiento con `dtype=np.int32` explícito para los límites observados en el dataset. No se usa el ancho del entero por defecto del sistema como contrato. La representación pública concreta y sus adaptadores se implementarán en M3.
- Una vista con escritura deshabilitada rechaza asignaciones ordinarias [S7], pero no garantiza por sí sola toda la inmutabilidad del grafo: el propietario del buffer y otras vistas pueden modificar datos. M3 debe encapsular el almacenamiento y comprobar el contrato completo.
- Las rutas tienen `n` índices con cierre implícito; booleanos, reales y cadenas no se convierten silenciosamente a enteros. La conversión a un arreglo no sustituye a la validación de entrada.
- El costo cuenta conexiones faltantes, se minimiza y exige legalidad previa. El ciclo se certifica con un validador independiente. Agotar un presupuesto no demuestra inexistencia de ciclo.
- Se mantienen separados `src/graphs`, `src/algorithms`, `src/evaluation` y `src/cli`. El esquema y la API del solver se dejan al #19.

## Preparación y comprobación

Los comandos de uso están en [README](../../README.md#entorno-de-desarrollo). Se invoca directamente el Python del entorno virtual: no es necesario activar el entorno [S2] ni modificar políticas de ejecución de PowerShell.

`tests/test_environment.py` comprueba que la extensión numérica ejecuta operaciones, que el almacenamiento explícito de 32 bits conserva valores grandes y que una vista comparte memoria y rechaza asignaciones cuando se deshabilita su escritura. Son pruebas de integración del entorno; **no validan grafos ni certifican ciclos**. No se mide velocidad ni se fija un protocolo experimental.

La comprobación Linux usa dos entornos virtuales nuevos: el de desarrollo y otro temporal, con una segunda descarga sin caché. En ambos se ejecutan instalación, `pip check`, pytest y comparación de `pip freeze --all`. Los resultados concretos, comandos auxiliares y limitaciones del equipo se registran en la PR.

Elías [reportó la ejecución satisfactoria en Windows](https://github.com/ZapataFrame/FHCP-Challenge/pull/24#issuecomment-6744109184) sobre el commit `e0976ac8884f0ceac1ac55d2dbd706f1cdb68a81`: entorno nuevo, `pip check` sin incompatibilidades, tres pruebas aprobadas y los ocho pines exactos, incluido `colorama==0.4.6`. El comentario conserva la salida y el entorno informado, aceptados como evidencia de esta comprobación. Los cambios posteriores de esta entrega solo actualizan documentación y el seguimiento de la PR.

### Intérprete aislado utilizado en Linux

El Python del sistema no coincidía con la versión elegida. Para comprobarla se compiló la distribución oficial en un prefijo local `.tools/python-3.14.10`, sin reemplazar el intérprete del sistema. Se verificó el SHA-256 del archivo `Python-3.14.10.tar.xz` contra [S1]:

```text
de414a57119abef52784d8993e341d53aed635fc2b05c2607d9f98a2c5b72032
```

Después de descargar y extraer ese archivo, desde su directorio se ejecutó lo siguiente (`PROJECT_ROOT` representa la ruta absoluta del checkout):

```bash
./configure --prefix="$PROJECT_ROOT/.tools/python-3.14.10" --with-ensurepip=install
make -j4
make altinstall
```

Esta vía requiere compilador C, `make`, cabeceras y bibliotecas de desarrollo de CPython, incluidas las de SSL y compresión para instalar paquetes. Sus nombres de instalación dependen de la distribución; no se prescribe un comando de gestor del sistema sin comprobarlo. La preparación se comprobó en CachyOS x86_64; no constituye validación de todas las distribuciones Linux. El módulo opcional `_tkinter` no se construyó y no es necesario para este entorno sin interfaz gráfica.

Desde la raíz del checkout, para usar ese intérprete en los comandos del README:

```bash
export PATH="$PWD/.tools/python-3.14.10/bin:$PATH"
```

El prefijo `.tools/`, los entornos, las cachés y los logs de construcción no se versionan. No se deben mover ni copiar entornos virtuales entre equipos; se recrean desde los requisitos [S2].

## Consecuencias y límites

El equipo dispone de una base mínima para empezar M3 cuando esta decisión se acepte. Las versiones exactas facilitan comparar instalaciones, a cambio de mantener los pines al actualizar. No se promete rendimiento adecuado de los solvers sin mediciones; primero se perfilarán los cuellos de botella. Las posibles diferencias entre sistemas, compiladores y bibliotecas numéricas deberán registrarse en los experimentos.

El objetivo de esta propuesta es Windows x86_64 y Linux x86_64 con CPython estándar. macOS, ARM, Python de 32 bits, PyPy y compilaciones sin GIL quedan fuera de la comprobación de esta entrega. No hay integración continua. La PR está abierta para revisión y el issue #15 permanece abierto mientras falte la revisión del equipo; la aceptación e integración son requisitos adicionales al resultado de las pruebas.

## Fuentes oficiales y capturas

Consulta y captura: **9 de noviembre de 2026**. Se usan fuentes oficiales para versiones y comportamiento de herramientas; las alternativas y su elección son razonamiento de diseño del proyecto. Cada referencia tiene una captura real del navegador, sin reconstruir el contenido. El [manifiesto de evidencias](evidence/stack-and-tooling/sources.json) registra URL, pasaje, fecha y hash de la imagen. Las fuentes académicas de los algoritmos permanecen en los entregables de investigación.

| ID | Fuente y pasaje utilizado | Captura |
| --- | --- | --- |
| S1 | [Python 3.14.10](https://www.python.org/downloads/release/python-31410/): versión, descargas y SHA-256 de las fuentes. | [Imagen](evidence/stack-and-tooling/python-release.jpg) |
| S2 | [venv, Python 3.14](https://docs.python.org/3.14/library/venv.html): aislamiento predeterminado, uso sin activación y recreación del entorno. | [Aislamiento](evidence/stack-and-tooling/venv.jpg) · [Uso y recreación](evidence/stack-and-tooling/venv-usage.jpg) |
| S3 | [NumPy 2.5.4 en PyPI](https://pypi.org/project/numpy/2.5.4/): versión publicada y arreglos numéricos. | [Imagen](evidence/stack-and-tooling/numpy.jpg) |
| S4 | [pytest 9.2.0 en PyPI](https://pypi.org/project/pytest/9.2.0/): versión publicada; [pyproject.toml oficial de la etiqueta 9.2.0](https://github.com/pytest-dev/pytest/blob/9.2.0/pyproject.toml#L49-L57), declaración `dependencies`, para dependencias y marcadores. | [Versión](evidence/stack-and-tooling/pytest.jpg) · [Dependencias](evidence/stack-and-tooling/pytest-dependencies.jpg) |
| S5 | [pip 26.3 en PyPI](https://pypi.org/project/pip/26.3/): versión publicada. | [Imagen](evidence/stack-and-tooling/pip.jpg) |
| S6 | [pip: Requirements Files](https://pip.pypa.io/en/stable/user_guide/#requirements-files): instalación con `-r` y fijación de versiones para repetir instalaciones. | [Imagen](evidence/stack-and-tooling/pip-requirements.jpg) |
| S7 | [NumPy: ndarray.setflags](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.setflags.html): significado y restricciones de `WRITEABLE`. | [Imagen](evidence/stack-and-tooling/numpy-flags.jpg) |

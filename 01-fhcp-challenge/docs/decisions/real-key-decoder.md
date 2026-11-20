# Decodificador común de claves reales

## Contexto

El [issue #49](https://github.com/ZapataFrame/FHCP-Challenge/issues/49), a cargo
de César Euresti · @cesar-upv, concreta el [apartado 9 de la investigación
#2](../research/metaheuristics.md#9-decodificador-común-para-las-propuestas-de-y-pso).
[Gonçalves y Resende, §2, p. 2](https://optimization-online.org/wp-content/uploads/2009/10/2423.pdf)
separan las claves del decodificador y describen la obtención de una secuencia
ordenando claves y leyendo sus índices. Su informe trata algoritmos genéticos
de claves reales. Compartir esta representación entre DE y PSO, permitir
claves fuera de `[0,1]` y desempatar por índice son decisiones del proyecto.

La salida respeta la [ruta legal del #17](graph-and-route-contracts.md#contrato-de-la-ruta)
y los rechazos no finitos permiten cumplir el [contrato de ejecución
#19](solver-and-result-contracts.md). Las dependencias #17–#19 y la base común
de M4 están integradas en `main`.

## Elección y adaptación a Python

`decode_real_keys(n, keys)`, importable desde `src.algorithms`, devuelve una
tupla nueva de enteros Python, ordenada de forma ascendente por
`(keys[index], index)`. El dominio de salida es exactamente `0..n-1`, cada
índice aparece una vez y el cierre es implícito. No canonicaliza la ruta.
Por ejemplo, `[0.10, 0.40, 0.20, 0.30]` produce `(0,2,3,1)` y
`[0.5, -2, 0.5, 7, -2]` produce `(1,4,0,2,3)`.
Estos ejemplos son conceptuales, no resultados de solvers.

- `n` es explícito: entero Python o NumPy positivo, excluidos booleanos y
  duraciones, reutilizando el criterio del núcleo de grafos. El decodificador
  admite `n=1` y `n=2` como rutas legales del #17; `start_run` sigue exigiendo
  `n>=3` para buscar ciclos simples.
- `keys` debe ser una secuencia posicional o un `numpy.ndarray` unidimensional
  de longitud `n`. No se aceptan texto, bytes, iteradores, conjuntos o mapas.
  Los arreglos multidimensionales no se aplanan. En secuencias anidadas,
  cada elemento no escalar se rechaza por su tipo.
- Cada clave debe ser un entero Python/NumPy o un flotante Python/NumPy
  finito. Booleanos, complejos, duraciones, fechas, cadenas, `Decimal`,
  `Fraction` y arreglos escalares se rechazan sin conversión implícita.
  Los arreglos `object` se inspeccionan elemento por elemento con las mismas
  reglas. No se usa `asarray` para convertir la entrada, pues podría ocultar
  tipos originales inválidos.
- Se conserva el valor de cada clave, incluidos extremos finitos y precisión
  extendida. Para comparar flotantes se usa su razón entera exacta mediante
  `as_integer_ratio()` y `fractions.Fraction`; los enteros se copian como
  `int`. Esto evita empates artificiales al mezclar enteros grandes con
  flotantes NumPy o al reducir `longdouble` a `float`. La representación
  auxiliar no modifica las claves del llamador.
- Se admiten negativos y valores finitos fuera de `[0,1]`, sin recortar,
  normalizar ni reparar. `0.0` y `-0.0` empatan por valor; el índice resuelve
  su orden. Con empates totales se devuelve `tuple(range(n))`.

Se acepta también una vista NumPy no contigua o de solo lectura. La función
no escribe en la entrada y la tupla no comparte almacenamiento mutable con
ella. No usa RNG: repetir el mismo vector reproduce la misma ruta.

## Rechazos y propagación

`KeyDecodingError(ValueError)` expone `code` y `position`. Se comprueban, en
este orden, tamaño, contenedor/forma, longitud y elementos por posición
ascendente. Toda la validación termina antes de ordenar; no hay ruta parcial.

| Código | Rechazo | `position` |
| --- | --- | --- |
| `invalid_size` | `n` no es un entero positivo admitido. | `None` |
| `invalid_keys_type` | El vector no es un contenedor posicional admitido. | `None` |
| `invalid_shape` | Un arreglo NumPy tiene dimensión distinta de uno. | `None` |
| `invalid_length` | La longitud no coincide con `n`. | `None` |
| `invalid_key_type` | La primera clave de tipo no admitido. | Índice de la clave |
| `non_finite_state` | La primera clave NaN, `+inf` o `-inf`. | Índice de la clave |

Al integrar DE/PSO, el consumidor debe capturar `KeyDecodingError` antes de
llamar a `run.evaluate`. Para un `exc.code == "non_finite_state"`, debe
devolver `run.fail("non_finite_state", exc.code, str(exc), position=exc.position)`.
Así conserva el motivo de parada del #19 y la posición del fallo, sin
evaluar ni certificar un estado corrupto. Los demás códigos identifican
errores de entrada o de implementación que el consumidor contextualizará;
no equivalen a `non_finite_state` ni a agotamiento del presupuesto.
La prueba de propagación usa la API existente de `SolverRun`; no incorpora
un bucle DE/PSO ni un adaptador de ejecución adicional.

## Alternativas, consecuencias y límites

Se descarta redondear claves a índices: no garantiza unicidad ni cobertura.
Un `argsort` sin desempate declarado dejaría ambiguo el orden de claves
iguales. Convertir todo a `float64` simplificaría la ordenación, pero puede
perder precisión, fusionar claves distintas o desbordar claves finitas de
precisión extendida. Comparar razones exactas añade objetos y sobrecarga;
se prioriza conservar el orden numérico en todos los tipos admitidos.

La validación recorre `n` elementos y la ordenación requiere `O(n log n)`
comparaciones y `O(n)` valores auxiliares. El coste de cada comparación y
el tamaño de las razones dependen de la precisión de las claves; estas son
cotas analíticas de operaciones, no mediciones de tiempo o memoria.

Muchos vectores inducen la misma ruta: hay mesetas, y perturbaciones de
claves pueden no cambiar el candidato ni su costo. Recortar a `[0,1]`
podría crear más empates; el decodificador no impone esa política a los
futuros solvers. Las actualizaciones, inicialización, presupuestos y
memorias de DE/PSO pertenecen a sus issues respectivos.

La construcción solo garantiza una permutación. No recibe grafo ni consulta
fitness, validador, dataset o certificados. Sus pruebas contrastan orden,
dominio, unicidad, rechazos y aislamiento de alias con ejemplos sintéticos.
La existencia de aristas y del cierre se certifica después, de forma
independiente. Esta entrega no aporta evidencia de rendimiento de DE/PSO
ni completa M5. Los [comandos de reproducción](../../README.md#decodificador-de-claves-reales)
permiten comprobar el componente.

Las propiedades de la representación auxiliar se apoyan en la documentación
oficial de [Fraction](https://docs.python.org/3.14/library/fractions.html) y
la comprobación de finitud en
[`numpy.isfinite`](https://numpy.org/doc/stable/reference/generated/numpy.isfinite.html).

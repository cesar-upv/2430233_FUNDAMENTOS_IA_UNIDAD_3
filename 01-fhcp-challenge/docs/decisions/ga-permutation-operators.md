# Operadores de permutación del GA

## Contexto

El [issue #38](https://github.com/ZapataFrame/FHCP-Challenge/issues/38) implementa las primitivas de la [variante GA del #2](../research/metaheuristics.md#35-adaptación-propuesta-a-fhcp), sobre las [rutas legales del #17](graph-and-route-contracts.md#contrato-de-la-ruta). La descripción de intercambio y OX de [Cicirello, §§3–4](https://arxiv.org/html/2311.14595) fundamenta los operadores; aquí se concreta la lectura circular del segundo padre ya utilizada en el [ejemplo del proyecto](../research/search-space.md#51-ejemplo-propio-de-ox-con-padres-factibles).

## Elección

La API pública de `src.algorithms` devuelve tuplas nuevas de enteros Python con dominio `0..n-1` y cierre implícito. Admite secuencias posicionales y arreglos NumPy de enteros, incluso de solo lectura. Usa `check_route_legality` antes de operar y conserva sus códigos mediante `GraphError`. No repara entradas ilegales, modifica progenitores ni canonicaliza rutas. Los operadores exigen `n >= 3`, el mínimo del [contrato del solver](solver-and-result-contracts.md); tamaños menores producen `ValueError`.

| Función | Contrato |
| --- | --- |
| `initialize_route(n, rng)` | Construye **un candidato** mediante `rng.permutation(n)`. No fija origen ni orientación. |
| `order_crossover(parent_a, parent_b, *, rng=None, cuts=None)` | Construye **un hijo**; exige padres legales de igual longitud. Recibe exactamente una fuente de decisiones: RNG o cortes explícitos. |
| `swap_mutation(route, *, rng=None, positions=None)` | Construye una copia con dos posiciones distintas intercambiadas. Recibe exactamente una fuente de decisiones: RNG o posiciones explícitas en `0..n-1`, en cualquier orden. |

**OX:** los cortes son límites del intervalo semiabierto `[start, stop)`, con `0 <= start < stop <= n`. Se copia ese segmento del primer padre en sus posiciones originales. Se lee el segundo padre desde `stop % n`, con retorno circular, omitiendo los vértices del segmento. Se rellenan las posiciones libres desde `stop % n`, también circularmente. Se permiten segmentos de un elemento y el segmento completo; este último devuelve una copia del primer padre. Invertir los padres en otra llamada con los mismos cortes produce el hijo complementario.

Por ejemplo, para `a = [0,1,2,3,4,5,6,7]`, `b = [1,2,0,5,6,7,4,3]` y cortes `(2,5)`, el segmento es `[2,3,4]`. Los valores restantes del segundo padre, leídos circularmente desde la posición 5, son `7,1,0,5,6`; se colocan en las posiciones `5,6,7,0,1`. El resultado es `(5,6,2,3,4,7,1,0)`. Es un ejemplo del contrato, no un resultado experimental.

**Aleatoriedad:** el llamador inyecta el `numpy.random.Generator` del intento; conforme al #19, el solver podrá crearlo con `Generator(PCG64(seed))`. Ningún operador crea generadores, usa estado global ni recibe semillas. OX muestrea dos límites distintos entre `0..n` con `rng.choice(n + 1, size=2, replace=False)` y los ordena. Así todos los intervalos no vacíos pueden elegirse, incluidos los extremos. Intercambio muestrea dos posiciones con `rng.choice(n, size=2, replace=False)`. La inicialización y las decisiones consumen únicamente ese generador, en el orden de llamadas del consumidor.

Los cortes explícitos invertidos se rechazan; no se ordenan silenciosamente. Decisiones repetidas, fuera de rango o de tipos no enteros, así como la ausencia o combinación de fuentes, producen `ValueError`. Un RNG distinto de `numpy.random.Generator` produce `TypeError`; una ruta no posicional también sigue el `TypeError` del #17. Las entradas inválidas se rechazan antes de consumir aleatoriedad. La reproducción exige el mismo entorno y secuencia de llamadas, según el #19.

## Alternativas y consecuencias

Se conserva la lectura y escritura circulares desde el final del segmento, frente a recorrer el donante desde cero o rellenar desde la primera posición. Declarar ambos recorridos evita mezclar variantes bajo el nombre OX. Se prefieren copias y tuplas a mutación en sitio para proteger padres y alias; inicialización, OX e intercambio cuestan `O(n)` en tiempo y memoria, incluida la comprobación de legalidad y copia. El intercambio aislado sería constante en sitio.

No se implementan probabilidades de aplicación, selección, población ni bucle evolutivo. Tampoco se leen grafos, dataset o certificados. Las pruebas de operadores comprueban permutaciones; las aristas y el cierre siguen siendo responsabilidad de `validate_cycle`. Un hijo legal puede contener aristas ausentes, como en el contraejemplo del proyecto. Los [comandos de reproducción](../../README.md#operadores-de-permutación-del-ga) usan pruebas sintéticas, sin medir rendimiento ni completar M4.

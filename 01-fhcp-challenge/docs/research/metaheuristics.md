# Metaheurísticas para la búsqueda de ciclos hamiltonianos

## Identificación

- **Responsable:** Junior Arturo Vázquez Leonel · @Arturo2430.
- **Issue:** [#2 · Investigar las seis metaheurísticas del proyecto](https://github.com/ZapataFrame/FHCP-Challenge/issues/2).
- **Hito:** M1 — Research.
- **Dependencias de cierre declaradas:** ninguna.
- **Fecha de consulta y captura:** 2026-11-01.
- **Alcance:** investigación bibliográfica y propuestas de diseño para GA, SA, ACO, ABC, DE y PSO. Las variantes, contratos y parámetros definitivos deberán acordarse en M2. No se implementaron solvers ni se midió su desempeño.

## Desarrollo

### 1. Selección de fuentes y lectura del documento

Se priorizaron dos libros académicos consultables y un capítulo de un manual académico: *Essentials of Metaheuristics*, *Algorithms for Optimization* y *Handbook of Metaheuristics*. Se complementan con el informe original de ABC, una publicación de los autores de The Bees Algorithm para distinguir las variantes y el informe sobre claves reales ya utilizado por el equipo. Se buscaron los títulos y las expresiones «metaheuristics textbook», «artificial bee colony original report» y «Bees Algorithm» en sitios de autores, editoriales y repositorios universitarios. Es una revisión acotada, no una revisión sistemática exhaustiva.

Se contrastaron autores, edición, año y editorial o institución con las páginas preliminares y los registros oficiales enlazados en Referencias. En particular, la edición bibliográfica de Luke es la segunda de **2013**, pero se leyó su actualización en línea **2.4, enero de 2026**. De Kochenderfer y Wheeler se utilizó la **primera edición de 2019**, revisión del PDF `47fd495`, fechada en 2022; no la vista previa de la segunda edición anunciada para 2027. Los localizadores se refieren a las páginas impresas de esas copias. En TR06, que no lleva números impresos, se indica la página del archivo PDF.

Cada cita del desarrollo tiene páginas originales capturadas en el [anexo](#anexo-de-referencias). El [registro de procedencia](evidence/metaheuristics-sources.json) identifica URL de descarga, SHA-256 del PDF y correspondencia entre página impresa, página del archivo e imagen. Las capturas identificativas comprueban la publicación; las de contenido permiten revisar la afirmación citada. Se distingue en cada apartado la **base bibliográfica** de la **propuesta para FHCP** y de las **deducciones analíticas propias**.

### 2. Conceptos previos y condiciones comunes

#### 2.1 Qué se busca con una metaheurística

Optimizar consiste en elegir una solución que mejore un criterio: reducir un costo, aumentar una ganancia o cumplir una condición con el menor esfuerzo posible. En muchos problemas se puede evaluar una propuesta, pero resulta difícil encontrar directamente la mejor. Una **metaheurística** proporciona una estrategia general para generar, evaluar y modificar candidatos; las seis familias estudiadas incorporan aleatoriedad en alguna parte de ese proceso [@luke2013Metaheuristics2, p. 9].

Por ejemplo, al ajustar dos parámetros de una máquina, un candidato podría ser el par de valores `(velocidad, temperatura)` y la evaluación podría ser el consumo de energía. En una planificación, un candidato podría ser el orden de varias tareas. El algoritmo necesita una representación y una forma de evaluar propuestas; esos elementos dependen del problema. Luke presenta precisamente la inicialización, evaluación, copia y modificación como operaciones necesarias para construir una búsqueda [@luke2013Metaheuristics2, p. 17].

El siguiente glosario fija el significado operativo de los términos utilizados en esta investigación:

| Término | Significado para el lector |
| --- | --- |
| Candidato o solución candidata | Propuesta que el algoritmo puede representar y evaluar; todavía debe comprobarse que cumple las restricciones. |
| Espacio de búsqueda | Conjunto de candidatos entre los que puede buscar el método. |
| Función objetivo | Regla que asigna un valor al candidato. Hay que declarar si se minimiza o maximiza. |
| Fitness o aptitud | Valoración utilizada para orientar la búsqueda; puede obtenerse transformando la función objetivo. Un costo menor puede corresponder a una aptitud mayor. |
| Población | Conjunto de candidatos mantenidos al mismo tiempo. Cada uno puede representar una alternativa distinta. |
| Iteración o generación | Paso de actualización del método. En los algoritmos poblacionales, una generación suele involucrar varios candidatos. |
| Vecindad | Conjunto de propuestas accesibles mediante un tipo de modificación definido, como cambiar un parámetro o intercambiar dos tareas. |
| Óptimo local | Candidato que no tiene una alternativa estrictamente mejor en la vecindad considerada. Cambiar la vecindad puede cambiar qué candidatos tienen esta propiedad. |
| Óptimo global | Candidato con el mejor valor entre todos los candidatos admisibles del problema. Puede haber varios. |
| Exploración y explotación | Buscar alternativas variadas y concentrar esfuerzo en alternativas prometedoras, respectivamente. |
| Convergencia prematura | Concentración de la búsqueda antes de explorar suficientemente otras alternativas; una población muy parecida puede dejar de producir mejoras útiles. |

La detención puede ocurrir al alcanzar una meta conocida, agotar evaluaciones o tiempo, completar un número de iteraciones o acumular pasos sin mejora. Detenerse por falta de mejora no certifica por sí solo un óptimo global. En las propuestas de este documento, encontrar un ciclo hamiltoniano validado sí satisface el objetivo constructivo del proyecto.

Los ejemplos de los apartados de cada algoritmo son **ejemplos didácticos propios**, con valores elegidos para explicar una operación. No proceden de ejecuciones ni constituyen resultados experimentales. Primero se describe el método general y después su adaptación propuesta a FHCP.

#### 2.2 Panorama de los seis métodos

Esta tabla resume las explicaciones de los apartados de cada algoritmo; describe su organización, sin ordenar su desempeño.

| Método | Qué conserva entre pasos | Cómo produce nuevas propuestas |
| --- | --- | --- |
| GA | Población de individuos y mejor histórico. | Selección, cruce y mutación. |
| SA | Un estado actual y mejor histórico. | Movimientos de vecindad con aceptación regulada por temperatura. |
| ACO | Feromonas compartidas y mejores soluciones. | Construcción de candidatos mediante elecciones probabilísticas. |
| ABC | Fuentes, calidades y contadores de intentos sin mejora. | Búsqueda alrededor de fuentes y renovación mediante exploradoras. |
| DE | Población de vectores y sus evaluaciones. | Diferencias escaladas, cruce y comparación con el objetivo. |
| PSO | Posiciones, velocidades y mejores posiciones recordadas. | Movimiento guiado por inercia, memoria personal e información social. |

#### 2.3 Problema y condiciones de las propuestas para FHCP

Se parte de la [teoría de grafos del equipo](graph-theory.md) y de la [propuesta de representación](search-space.md): grafo finito, simple y no dirigido, con $n\ge3$; candidato como permutación $p=(p_0,\ldots,p_{n-1})$ de los índices $0,\ldots,n-1$, y cierre implícito. Son convenciones propuestas para M2, no contratos ya aprobados.

Para hacer comparables las explicaciones se utiliza el siguiente **costo ilustrativo propio**, pendiente de coordinación con el [issue #5 sobre fitness](https://github.com/ZapataFrame/FHCP-Challenge/issues/5):

$$
C(p)=\sum_{i=0}^{n-1}\mathbf{1}\!\left[\{p_i,p_{(i+1)\bmod n}\}\notin E\right].
$$

Se minimiza el número de pares cíclicos ausentes. Su dominio es exclusivamente el de permutaciones legales: una lista con duplicados, elementos fuera de rango o longitud incorrecta debe rechazarse antes de aplicar esta expresión. Sobre ese dominio, $C(p)=0$ equivale matemáticamente a cumplir las aristas y el cierre; aun así, el software deberá usar un **validador independiente del cálculo de costo** para certificar cada éxito y detectar errores de implementación. Esta expresión no se atribuye a los libros ni establece el fitness definitivo.

Todos los pseudocódigos siguientes son esquemas propios de adaptación, no transcripciones de los textos. `evaluate` decodifica cuando corresponde y calcula el costo; `inspect` conserva el mejor candidato evaluado y solicita validación independiente ante un costo cero. Un ciclo confirmado termina inmediatamente la búsqueda con éxito; una discrepancia del validador la termina con error. Deben invocarse también durante la inicialización y después de una exploración aleatoria.

`budget_available` comprueba el límite de evaluaciones, tiempo y pasos o generaciones. Se comprueba antes de cada evaluación y dentro de los bucles de construcción, decodificación y búsqueda local; estas operaciones forman parte del tiempo consumido. Un límite de tiempo tiene la granularidad de las operaciones que puedan interrumpirse y no garantiza detener una llamada externa indivisible en un instante exacto. Se distinguen solución validada, presupuesto agotado y error. El agotamiento no prueba inexistencia de un ciclo.

La inicialización también está sujeta al presupuesto. Si no se completa la población mínima requerida, se retorna el mejor candidato ya evaluado y el estado de agotamiento; no se inicia el bucle con individuos sin evaluar. Las configuraciones inválidas se rechazan antes de comenzar la búsqueda.

### 3. Algoritmo genético — GA

#### 3.1 Descripción y componentes

Un **algoritmo genético** (*Genetic Algorithm*, GA) busca soluciones mediante una población que cambia a lo largo de generaciones. Utiliza la terminología de la herencia: los candidatos son individuos, su representación es un cromosoma, sus componentes son genes y las nuevas propuestas son descendientes. Un cromosoma puede ser una cadena de bits o un vector de valores reales; su significado depende de cómo se codifique el problema [@kochenderferWheeler2019Optimization, p. 150].

La idea es favorecer la reproducción de candidatos con buena evaluación y generar nuevas combinaciones de sus componentes. El ciclo de evaluación, selección, cruce y mutación aparece en el algoritmo 20 de Luke [@luke2013Metaheuristics2, p. 37]. En este contexto, «reproducir» significa construir datos nuevos mediante operadores, no simular organismos completos.

| Componente | Función general |
| --- | --- |
| Población y cromosoma | Mantener varias propuestas y expresar sus decisiones en una estructura manipulable. |
| Selección | Elegir qué candidatos aportan información a los descendientes. |
| Cruce o recombinación | Combinar partes de dos o más padres. El operador depende de la representación. |
| Mutación | Introducir cambios aleatorios que aporten variación. |
| Reemplazo y elitismo | Decidir quién integra la siguiente generación; el elitismo reserva lugares a los mejores anteriores. |

#### 3.2 Funcionamiento general

1. Crear una población inicial y evaluar sus individuos.
2. Seleccionar padres según la regla elegida.
3. Aplicar cruce para producir descendientes y mutación para introducir variaciones.
4. Evaluar los descendientes y formar la siguiente generación mediante la política de reemplazo.
5. Repetir hasta alcanzar la condición de terminación, conservando el mejor candidato encontrado.

#### 3.3 Características y limitaciones

La búsqueda es poblacional y estocástica. Su representación puede adaptarse a decisiones binarias, parámetros numéricos u órdenes de elementos, pero cada caso necesita operadores compatibles. El tamaño de población controla cuántos candidatos se mantienen; las probabilidades de cruce y mutación controlan con qué frecuencia se aplican esas operaciones.

La selección por torneo elige el mejor de un grupo muestreado; su tamaño regula la presión de selección. El elitismo permite conservar buenos individuos, aunque también puede aumentar la convergencia prematura [@luke2013Metaheuristics2, pp. 45–46]. Como consecuencia de su estructura, una población mayor también exige más almacenamiento y evaluaciones por generación. La recombinación puede producir candidatos peores que sus padres o incompatibles con las restricciones si se define mal.

#### 3.4 Ejemplo didáctico

Supóngase que se desea **maximizar el número de unos** de una cadena de cuatro bits. Los padres `1010` y `0101` tienen aptitud 2. Un cruce después del segundo bit toma `10` del primer padre y `01` del segundo: produce `1001`, también con aptitud 2. Si una mutación cambia su segundo bit de 0 a 1, se obtiene `1101`, con aptitud 3.

El ejemplo ilustra el papel de los operadores y la evaluación: el cruce no mejoró la aptitud en este caso y una mutación concreta sí lo hizo. Otro cambio de bit podría empeorarla. Estas cadenas binarias no representan rutas FHCP.

#### 3.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** GA generacional sobre permutaciones, con torneo de minimización, cruce OX, mutación por intercambio y una cantidad configurable de élites. La selección usa costos ya guardados. Para OX se copia un segmento del primer padre y se completan los huecos recorriendo circularmente el segundo, omitiendo los vértices ya incluidos. Esta definición y el [contraejemplo de OX del equipo](search-space.md#51-ejemplo-propio-de-ox-con-padres-factibles) permiten razonar que conserva la permutación, pero puede introducir pares ausentes del grafo.

```text
P = initialize_and_evaluate_permutations(population_size)
inspect every evaluated individual
while budget_available and no validated cycle:
    Q = copies of elite_count best individuals of P
    while size(Q) < population_size and budget_available:
        a, b = tournaments(P, tournament_size)
        child = OX(a, b) with probability crossover_rate; otherwise copy(a)
        swap two positions of child with probability mutation_rate
        evaluate(child); inspect(child); append child to Q
    if Q is complete: P = Q
return the best evaluated candidate and the termination status
```

**Parámetros y riesgos.** Tamaño de población, torneo, probabilidades de cruce y mutación, número de élites y presupuesto. Definir si la mutación se aplica por individuo o por posición; aquí se propone por individuo. Mantener copias de los padres, limitar élites a menos que la población y resolver empates de forma explícita. Un cruce de corte y pegado ordinario puede duplicar vértices; OX evita ese defecto con un conjunto de usados. Elitismo y torneos grandes pueden reducir diversidad. Ninguno de estos operadores garantiza aristas válidas ni mejor rendimiento en FHCP.

### 4. Recocido simulado — SA

#### 4.1 Descripción y componentes

El **recocido simulado** (*Simulated Annealing*, SA) modifica una solución actual y decide si acepta cada nueva propuesta. Su nombre alude al recocido de un material mediante calentamiento y enfriamiento controlado. En el algoritmo, la **temperatura** es un parámetro numérico que regula la disposición a aceptar movimientos que empeoran el valor actual [@luke2013Metaheuristics2, pp. 25–26].

La intuición es permitir cambios menos selectivos al comienzo y volver la búsqueda más exigente conforme baja la temperatura. Aceptar temporalmente una propuesta peor permite abandonar un candidato del que no se puede mejorar mediante movimientos inmediatos, aunque no asegura encontrar después uno mejor.

| Componente | Función general |
| --- | --- |
| Estado actual | Candidato desde el cual se genera la siguiente propuesta. |
| Vecindad | Regla para modificar el estado, como variar un parámetro o intercambiar dos elementos. |
| Temperatura | Controlar la probabilidad de aceptar una propuesta peor. |
| Calendario de enfriamiento | Indicar cómo cambia la temperatura con las iteraciones. |
| Mejor histórico | Conservar la mejor propuesta evaluada aunque el estado actual empeore. |

#### 4.2 Funcionamiento general

1. Elegir y evaluar un estado inicial; fijar una temperatura inicial.
2. Generar un candidato vecino y calcular su diferencia de valor respecto del actual.
3. Aceptar mejoras y decidir probabilísticamente si se aceptan empeoramientos.
4. Actualizar el mejor histórico y reducir la temperatura según el calendario.
5. Repetir hasta cumplir la terminación.

#### 4.3 Características y limitaciones

SA mantiene una trayectoria de búsqueda basada en un estado actual. La temperatura inicial, el número de movimientos por nivel de temperatura y la velocidad de enfriamiento regulan su comportamiento. La escala de la función objetivo importa: un aumento de costo de 100 no produce la misma aceptación que un aumento de 1 con la misma temperatura.

El enfriamiento geométrico multiplica la temperatura por un factor entre cero y uno. Enfriar muy rápido puede limitar la exploración; algunos calendarios poseen garantías asintóticas bajo condiciones específicas, pero estas no aseguran éxito con un presupuesto finito [@kochenderferWheeler2019Optimization, p. 130]. La elección de una vecindad útil también resulta decisiva: el calendario no compensa automáticamente movimientos poco adecuados al problema.

#### 4.4 Ejemplo didáctico

Se minimiza un costo y el estado actual vale 8. Un vecino vale 10, por lo que el aumento es 2. Con la regla exponencial descrita por SA, una temperatura de 4 da una probabilidad de aceptación de $\exp(-2/4)\approx0.607$, alrededor del 60.7 %. Con temperatura 0.5, la probabilidad baja a $\exp(-2/0.5)\approx0.018$, alrededor del 1.8 %.

La misma propuesta peor puede aceptarse al principio y rechazarse con mayor frecuencia al final. Los porcentajes se calculan de la fórmula; no son tasas observadas en experimentos.

#### 4.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** Usar una permutación y una vecindad simétrica por intercambio de dos posiciones distintas. Una inversión de segmento es otra opción que deberá declararse si se estudia; mezclar ambas cambia el método. Para minimización, con $\Delta=C(q)-C(p)$ y $T>0$:

$$
P(\text{aceptar }q)=\begin{cases}1,&\Delta\le0,\\ \exp(-\Delta/T),&\Delta>0.\end{cases}
$$

```text
p = initialize_and_evaluate_permutation(); inspect(p)
T = initial_temperature
while budget_available and no validated cycle and T > minimum_temperature:
    repeat moves_per_temperature times, subject to budget_available:
        q = copy(p) with two distinct positions swapped
        evaluate(q); inspect(q)
        delta = C(q) - C(p)
        if delta <= 0 or log(U) < -delta/T, with U sampled in (0,1): p = q
    T = cooling_factor * T
return the best evaluated candidate, not necessarily the final current candidate
```

**Parámetros y riesgos.** Temperatura inicial, factor $0<\gamma<1$, temperatura mínima no negativa, movimientos por temperatura, vecindad y presupuesto. La rama de aceptación probabilística solo se evalúa si $\Delta>0$ y $T>0$; usar logaritmos evita calcular una exponencial muy pequeña. No dividir entre cero. Un costo discreto tiene mesetas, por lo que aceptar empates y conservar el mejor histórico son decisiones relevantes. El calendario debe ajustarse a la escala del fitness; cambiar el costo obliga a reconsiderarlo. Intercambios e inversiones conservan visita única, pero pueden romper aristas y cierre.

### 5. Colonia de hormigas — ACO

#### 5.1 Descripción y componentes

La **optimización por colonia de hormigas** (*Ant Colony Optimization*, ACO) es una familia de métodos en los que agentes artificiales construyen soluciones por etapas y comparten información mediante valores llamados **feromonas**. La inspiración es la comunicación indirecta de las hormigas mediante rastros. En el algoritmo, esos rastros son datos numéricos asociados a decisiones o componentes de una solución [@dorigoStuetzle2003Aco, p. 251].

Por ejemplo, para construir un recorrido, una hormiga artificial decide a qué ciudad pasar en cada paso. Su elección puede considerar una estimación del atractivo de la siguiente ciudad y lo aprendido de recorridos anteriores. Ant System (AS) combina esa información con probabilidades de elección y actualiza feromonas mediante evaporación y depósito [@dorigoStuetzle2003Aco, pp. 261–262].

| Componente | Función general |
| --- | --- |
| Hormiga artificial | Procedimiento que construye un candidato mediante decisiones sucesivas. |
| Feromona | Memoria numérica compartida que influye en futuras elecciones. |
| Información heurística | Estimación disponible del atractivo de una decisión, como una distancia favorable. |
| Evaporación | Reducir la influencia acumulada de decisiones anteriores. |
| Depósito | Reforzar componentes de acuerdo con la evaluación de las soluciones construidas. |

#### 5.2 Funcionamiento general

1. Inicializar los valores de feromona.
2. Hacer que varias hormigas construyan soluciones usando feromonas e información heurística.
3. Evaluar las soluciones completas.
4. Evaporar parte de las feromonas y realizar depósitos según la variante elegida.
5. Repetir el ciclo, conservando la mejor solución encontrada.

#### 5.3 Características y limitaciones

ACO se adapta a problemas donde una solución se puede construir mediante una secuencia de elecciones. Su memoria compartida relaciona lo construido en un ciclo con las probabilidades del siguiente. En AS, los parámetros $\alpha$ y $\beta$ ponderan feromonas e información heurística; la tasa de evaporación regula cuánto se conserva de la memoria [@dorigoStuetzle2003Aco, pp. 261–262].

Un refuerzo excesivamente concentrado puede llevar al estancamiento: muchas hormigas terminan construyendo las mismas soluciones. También hay que definir qué ocurre cuando una construcción queda bloqueada. ACO es el nombre de la familia; **Ant System** y **Ant Colony System** son variantes con reglas específicas, no nombres intercambiables.

#### 5.4 Ejemplo didáctico

Una hormiga debe elegir entre B y C. Ambas opciones tienen la misma información heurística y sus feromonas son 2 y 1. Si la influencia de la feromona es lineal, sus pesos relativos dan probabilidades $2/(2+1)=2/3$ para B y $1/3$ para C. La opción con más feromona resulta más probable, pero la otra sigue siendo elegible.

Con una evaporación de 0.2, el valor 2 se reduce a $(1-0.2)\cdot2=1.6$ antes de añadir depósitos. Para conocer la siguiente elección hay que considerar también esos depósitos y las demás opciones disponibles.

#### 5.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** Estudiar una adaptación de **Ant System con penalización de pares ausentes**. En vez de bloquear inmediatamente una construcción sobre el grafo incompleto, se permite elegir cualquier vértice no visitado. Para un conjunto restante $U$ y vértice actual $u$:

$$
P(v\mid u,U)=\frac{\tau_{uv}^{\alpha}\eta_{uv}^{\beta}}
{\sum_{w\in U}\tau_{uw}^{\alpha}\eta_{uw}^{\beta}},\quad
\eta_{uv}=\begin{cases}1,&\{u,v\}\in E,\\ \varepsilon,&\{u,v\}\notin E,\end{cases}
$$

con $0<\varepsilon<1$, feromona inicial positiva y $\alpha,\beta\ge0$. Esta heurística y el siguiente depósito son **propuestas propias**: el depósito de AS basado en longitud TSP no se traslada literalmente a un problema donde todos los ciclos completos tienen $n$ aristas.

```text
initialize positive symmetric pheromone tau on every pair of distinct vertices
while budget_available and no validated cycle:
    tours = empty
    for each ant, subject to budget_available:
        p = choose a start vertex; U = all other vertices
        while U is nonempty and budget_available:
            sample v from U using tau and eta; append v; remove v from U
        if p is complete and budget_available:
            evaluate(p); inspect(p); append p to tours
    if budget is exhausted: finish without updating pheromone
    evaporate tau by factor (1-rho), checking the time budget during the update
    for each completed evaluated p in tours:
        add Q/(1+C(p)) to each cyclic pair of p, including the closing pair
    bound tau within positive declared limits
```

**Parámetros y riesgos.** Número de hormigas, $\alpha$, $\beta$, $\rho\in(0,1)$, $Q>0$, $\varepsilon$, feromona inicial, cotas de feromona y presupuesto. Se actualiza cada par en ambos sentidos para conservar la simetría del grafo no dirigido. Se refuerzan pares de candidatos completos, incluso si algunos pares están ausentes; por ello se trata de una adaptación con restricciones suaves, no de un constructor que garantice factibilidad. No depositar por recorridos truncados al agotar el presupuesto. Debe evitarse desbordamiento o suma de pesos nula mediante cálculo estable y reglas explícitas.

Una alternativa es limitar $U$ a vecinos reales. Esa alternativa puede atascarse antes de cubrir todos los vértices o fallar en el cierre; necesitaría reinicio o retroceso acotados, cuyo costo también consume presupuesto. No sustituir silenciosamente una política por la otra. El predominio de feromonas puede concentrar todas las hormigas en recorridos similares; conservar una cota positiva mantiene opciones disponibles, sin demostrar que una ejecución finita encuentre un ciclo.

### 6. Colonia de abejas — variante ABC

#### 6.1 Descripción y componentes

La **colonia de abejas artificiales** (*Artificial Bee Colony*, ABC) organiza la búsqueda alrededor de **fuentes de alimento**, cada una de las cuales representa una solución candidata. La cantidad de néctar representa su calidad. Las abejas son funciones del algoritmo encargadas de mejorar fuentes conocidas, seleccionar dónde buscar y descubrir nuevas fuentes [@karaboga2005Abc, sección III, p. 6 del PDF].

La variante estudiada es ABC del informe TR06 de Karaboga. El nombre genérico «colonia de abejas» también puede aludir a otros métodos; por eso se mantiene la sigla de la variante y se describen sus fases.

| Componente | Función general |
| --- | --- |
| Fuente de alimento | Candidato y su calidad evaluada. |
| Abeja empleada | Buscar una alternativa en torno a una fuente conocida. |
| Abeja observadora | Seleccionar una fuente mediante la información de calidad compartida y continuar la búsqueda en ella. |
| Abeja exploradora | Generar una nueva fuente para renovar la búsqueda. |
| `limit` | Controlar el abandono de una fuente tras una cantidad declarada de intentos sin mejora. |

#### 6.2 Funcionamiento general

1. Crear fuentes iniciales y evaluar su calidad.
2. Aplicar la fase de empleadas para buscar mejoras en fuentes conocidas.
3. Calcular probabilidades de selección de fuentes a partir de sus calidades.
4. Aplicar la fase de observadoras, concentrando probabilísticamente esfuerzo en las fuentes seleccionadas.
5. Abandonar fuentes que cumplen la regla de estancamiento y generar nuevas mediante exploradoras.
6. Conservar la mejor fuente y repetir hasta detenerse.

Las fases y el abandono mediante `limit` se describen en el informe original [@karaboga2005Abc, sección III, pp. 6–7 del PDF].

#### 6.3 Características y limitaciones

ABC combina trabajo sobre candidatos existentes con renovación de candidatos. Hay que definir el número de fuentes, la cantidad de selecciones de observadoras, la vecindad y el umbral de abandono. Para minimizar un costo también debe declararse cómo convertirlo en una calidad que favorezca mejores fuentes. Renovar fuentes aporta diversidad, pero puede gastar evaluaciones si se hace con demasiada frecuencia.

**The Bees Algorithm (BA)** es otra variante: selecciona sitios prometedores y élites, asigna reclutas y controla el tamaño de sus vecindades [@yuce2013Bees, pp. 651–652]. Esas reglas no se incorporan automáticamente a ABC. La función que produce un vecino también debe adaptarse al tipo de candidato: modificar parámetros reales y reorganizar tareas requieren operaciones diferentes.

#### 6.4 Ejemplo didáctico

Supónganse tres fuentes con calidades positivas 6, 3 y 1. Si las observadoras eligen proporcionalmente a la calidad, las probabilidades son 0.6, 0.3 y 0.1. La primera fuente recibe más oportunidades de búsqueda en promedio; una selección concreta todavía puede elegir cualquiera de las tres.

Si una fuente acumula tres intentos fallidos y se ha fijado `limit = 3`, queda disponible para abandono según la política de exploradoras. Una fuente nueva deberá evaluarse: ser nueva no implica que sea mejor. Los números del ejemplo son calidades elegidas para ilustrar selección y abandono, no parámetros recomendados para FHCP.

#### 6.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** ABC sobre $S\ge2$ fuentes, cada una una permutación; $S$ empleadas y $S$ selecciones de observadoras por ciclo. Para minimizar el costo ilustrativo, transformar calidad a $w_i=1/(1+C(p_i))$ y seleccionar fuentes con probabilidad $w_i/\sum_jw_j$. Esta transformación y la vecindad discreta siguiente son propuestas propias; el informe original estudia optimización numérica.

`neighbor(p, partner)` elige una posición donde ambas rutas difieran, localiza en `p` el vértice que ocupa esa posición en `partner` y realiza un intercambio para colocarlo allí. Si las rutas coinciden, usa un intercambio aleatorio de posiciones distintas. Localizar un vértice cuesta $O(n)$ sin un índice inverso. Se preservan cobertura y unicidad; no se preservan las aristas.

```text
initialize and evaluate S food sources; trials = zero; inspect each source
while budget_available and no validated cycle:
    for each source i, subject to budget_available:
        choose another source k; propose neighbor(source[i], source[k])
        evaluate and inspect proposal
        if strictly better: replace source[i]; trials[i] = 0
        else: trials[i] += 1
    build probabilities from current source costs, frozen for this onlooker phase
    repeat S times, subject to budget_available:
        sample source i; choose partner k != i; propose a neighbor
        evaluate and inspect; apply the same replacement and trials rule
    if any trials[i] >= limit and budget_available:
        replace at most one expired source by a fresh random permutation
        evaluate and inspect it; reset its trials counter
return the best evaluated source preserved separately from abandoned sources
```

**Parámetros y riesgos.** Número de fuentes y observadoras, `limit`, vecindad, política de empates, máximo de exploradoras y presupuesto. Para el esquema anterior se propone una exploradora por ciclo y elegir la fuente con más intentos fallidos, desempatando por índice. Es una especificación para discusión, no una variante experimentalmente validada. El abandono puede eliminar una buena fuente, por lo que se conserva el mejor histórico aparte. Un `limit` pequeño favorece reinicios frecuentes; uno grande permite más intentos sin mejora. La selección proporcional puede concentrar el esfuerzo y la vecindad guiada por un socio no garantiza mejora.

### 7. Evolución diferencial — DE

#### 7.1 Descripción y componentes

La **evolución diferencial** (*Differential Evolution*, DE) es un método poblacional que genera propuestas numéricas utilizando **diferencias entre individuos**. En la variante aquí explicada, toma un vector como base, le suma una diferencia escalada de otros dos y combina el resultado con un candidato objetivo. Después compara la propuesta con ese objetivo para decidir cuál conserva [@kochenderferWheeler2019Optimization, p. 157].

El término «diferencial» se refiere aquí a restar vectores de candidatos. No exige calcular la derivada de la función objetivo. Si los candidatos contienen varias decisiones numéricas, cada coordenada corresponde a una de ellas.

| Componente | Función general |
| --- | --- |
| Individuo objetivo | Candidato de la población que podría ser reemplazado. |
| Vector base y diferencia | Material numérico con el que se construye un donante. |
| Factor diferencial $F$ | Multiplicar la diferencia y controlar su contribución al nuevo vector. |
| Cruce y tasa $CR$ | Combinar coordenadas del donante y del objetivo. |
| Selección de supervivencia | Conservar el candidato elegido al comparar objetivo y propuesta. |

#### 7.2 Funcionamiento general

1. Crear y evaluar una población de vectores numéricos.
2. Para cada objetivo, seleccionar los individuos requeridos por la variante.
3. Construir un donante mediante una diferencia escalada.
4. Cruzar donante y objetivo para producir una propuesta.
5. Evaluar la propuesta y compararla con el objetivo; repetir para continuar la evolución.

#### 7.3 Características y limitaciones

La población aporta tanto los candidatos como la información usada para generar cambios. La resta entre individuos incorpora la separación actual entre sus coordenadas; multiplicar por $F$ modifica esa contribución. En el cruce binomial se decide por coordenada y se obliga a tomar al menos una del donante, aunque esto no asegura un candidato numéricamente diferente [@kochenderferWheeler2019Optimization, p. 157].

El método básico se expresa sobre valores numéricos y no necesita gradientes. Deben definirse población, factor diferencial, tasa de cruce, selección de donantes y tratamiento de límites de las variables. Si los individuos se vuelven iguales, sus diferencias se anulan; si una propuesta sale del dominio permitido, hace falta una regla de manejo de límites. Aplicarlo a órdenes de tareas o rutas exige una codificación o unos operadores discretos explícitos.

#### 7.4 Ejemplo didáctico

Considérese minimizar $f(x)=(x-12)^2$. El individuo objetivo es 10 y se eligen otros tres valores: base 8, segundo 14 y tercero 4. Con $F=0.5$, el donante es $8+0.5(14-4)=13$. En una sola dimensión, la coordenada obligatoria del cruce hace que la propuesta sea 13.

El objetivo tiene costo $f(10)=4$ y la propuesta tiene costo $f(13)=1$; una regla que conserva la mejora sustituye 10 por 13. Esta operación explica el mecanismo; no implica que las siguientes propuestas continúen mejorando.

#### 7.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** **DE/rand/1/bin sobre claves reales**, utilizando el decodificador del apartado 9. Para el objetivo $x_i$, elegir índices distintos $a,b,c$, todos diferentes de $i$, lo que exige $P\ge4$:

$$
z=x_a+F(x_b-x_c),\qquad
u_j=\begin{cases}z_j,&r_j<CR\ \text{o}\ j=j_* ,\\x_{ij},&\text{en otro caso}.\end{cases}
$$

Se elige $j_*$ uniformemente entre las coordenadas y cada $r_j$ de forma independiente en $[0,1)$. Heredar una coordenada del donante no garantiza que cambie el vector ni el orden decodificado.

```text
initialize P key vectors; decode, evaluate and inspect each
while budget_available and no validated cycle:
    old = frozen population; next = copy(old)
    for each target i, subject to budget_available:
        choose distinct a,b,c excluding i; z = old[a] + F*(old[b]-old[c])
        u = binomial crossover(old[i], z, CR, one mandatory donor coordinate)
        decode(u); evaluate and inspect its route
        if f(u) < cached f(old[i]): next[i] = u
    population = next
return the best evaluated decoded candidate and its stored key vector
```

**Parámetros y riesgos.** Población, $F>0$, $CR\in[0,1]$, distribución inicial y presupuesto. Se propone reemplazo sincrónico con población congelada y conservación del objetivo ante empate; son elecciones explícitas, no una reproducción literal del código en sitio del libro. La diferencia entre claves no es una diferencia entre aristas: puede modificar muchas posiciones o ninguna. La contracción de la población y las mesetas pueden reducir cambios efectivos. Una variante basada en intercambios sería otro diseño que requeriría definir sus propias operaciones; aquí no se presenta como equivalente a la variante propuesta.

### 8. Enjambre de partículas — PSO

#### 8.1 Descripción y componentes

La **optimización por enjambre de partículas** (*Particle Swarm Optimization*, PSO) representa cada candidato como una partícula que se desplaza por un espacio numérico. Su **posición** contiene los valores propuestos para las variables y su **velocidad** determina cómo cambian. Cada partícula recuerda la mejor posición que ha visitado y utiliza información sobre una buena posición compartida por el enjambre o su vecindario [@kochenderferWheeler2019Optimization, pp. 158–159].

La idea intuitiva es combinar persistencia en el movimiento, experiencia propia e información social. Los términos aleatorios hacen que esa orientación no sea idéntica en cada actualización. «Velocidad» es un vector de cambios de variables; no tiene que representar una velocidad física.

| Componente | Función general |
| --- | --- |
| Posición | Candidato actual de la partícula. |
| Velocidad | Cambio numérico que se aplica para moverla. |
| Mejor personal | Memoria de la posición mejor evaluada por esa partícula. |
| Mejor social | Referencia compartida por el enjambre o por los vecinos definidos en la topología. |
| Inercia y atracciones | Ponderar cuánto influyen el movimiento anterior, la memoria personal y la referencia social. |

#### 8.2 Funcionamiento general

1. Inicializar posiciones y velocidades; evaluar las posiciones.
2. Guardar los mejores personales y la referencia social correspondiente.
3. Actualizar la velocidad con los términos de inercia y atracción.
4. Mover las partículas, evaluar sus posiciones y actualizar las memorias que mejoren.
5. Repetir hasta cumplir la condición de terminación.

El orden exacto entre mover y actualizar velocidad debe declararse; el libro utiliza primero el movimiento y la propuesta posterior de este documento el orden inverso. Ambos requieren que las memorias se actualicen a partir de evaluaciones, no solo por cercanía a otra partícula.

#### 8.3 Características y limitaciones

PSO mantiene candidatos y memoria de su experiencia. Sus parámetros incluyen tamaño de enjambre, inercia, atracción personal, atracción social y, si se usa, límite de velocidad. La topología determina quién comparte información con quién; en una topología global todos utilizan una referencia global. Luke distingue la mejor posición personal, la de los informantes y la mejor de todo el enjambre [@luke2013Metaheuristics2, p. 56].

Las ecuaciones numéricas no requieren gradientes, pero las posiciones deben representar variables en las que esas operaciones tengan sentido. Una atracción fuerte hacia la misma referencia puede concentrar el enjambre; una velocidad grande puede llevarlo fuera de los límites admisibles. Por la propia regla de movimiento, la posición siguiente puede tener peor costo que la actual: el mejor personal y el mejor global deben conservarse por separado [@kochenderferWheeler2019Optimization, pp. 158–159].

#### 8.4 Ejemplo didáctico

Una partícula está en $x=2$, tiene velocidad cero y recuerda un mejor personal $b=4$; el mejor compartido está en $g=6$. Para ilustrar el orden velocidad y después posición, sean $\omega=0.5$, $c_1=c_2=1$ y $r_1=r_2=0.5$. La nueva velocidad es $0.5\cdot0+0.5(4-2)+0.5(6-2)=3$; la nueva posición es $2+3=5$.

Si se minimiza $f(x)=(x-7)^2$, pasar de 2 a 5 reduce el costo de 25 a 4. Esto mejora la memoria personal, pero el mejor compartido en 6 todavía tiene costo 1. Las memorias se comparan usando la función objetivo, no el valor de la coordenada por sí solo.

#### 8.5 Adaptación propuesta a FHCP

**Propuesta para FHCP.** PSO global sobre claves reales, con el decodificador del apartado 9. Cada partícula guarda $x_i$, $v_i$ y una **copia** de las claves de su mejor posición personal $b_i$. La mejor global $g$ también se conserva por copia. Para esta propuesta se fija el orden velocidad y después posición:

$$
v_i^{t+1}=\omega v_i^t+c_1r_1\odot(b_i-x_i^t)+c_2r_2\odot(g-x_i^t),\qquad
x_i^{t+1}=x_i^t+v_i^{t+1}.
$$

Los vectores $r_1,r_2$ tienen muestras independientes por coordenada; $\odot$ representa el producto componente a componente. El orden indicado y la actualización sincrónica siguiente son elecciones de esta propuesta, no una transcripción de la implementación del libro, que mueve primero la posición.

```text
initialize positions and velocities; decode, evaluate and inspect positions
copy initial personal bests and global best
while budget_available and no validated cycle:
    freeze personal bests and global best for this iteration
    for each particle, subject to budget_available:
        update velocity from inertia, personal attraction and global attraction
        apply a declared velocity bound if the configuration enables one
        update keys; decode, evaluate and inspect the route
        record improvements for the next personal and global memories
    commit memory updates from the particles actually evaluated
return the best validated or best evaluated route and termination status
```

**Parámetros y riesgos.** Número de partículas, $\omega$, $c_1$, $c_2$, distribución inicial de claves y velocidades, cota de velocidad si se utiliza, topología y presupuesto. Aquí se propone topología global; otra topología debe declararse. Conservar memorias por referencia a arreglos mutables puede destruir el mejor histórico. Grandes velocidades pueden provocar desbordamiento; velocidades pequeñas y claves con el mismo orden pueden mantener la ruta sin cambios. Compartir un mismo mejor global puede reducir diversidad. Ninguna fórmula continua garantiza factibilidad hamiltoniana después de ordenar.

### 9. Decodificador común para las propuestas DE y PSO

**Base bibliográfica.** Gonçalves y Resende separan el vector de claves reales del decodificador y explican que ordenar las claves y leer sus índices produce una secuencia [@goncalvesResende2009RandomKeys, sección 2, p. 2]. Su informe trata algoritmos genéticos de claves reales; no constituye por sí mismo una validación de DE o PSO para FHCP.

**Construcción propia.** Asociar una clave real finita $x_v$ a cada vértice $v$, y definir:

$$
D(x)=\operatorname{argsort}_{v\in\{0,\ldots,n-1\}}(x_v,v),\qquad f(x)=C(D(x)).
$$

El desempate por índice hace determinista la ordenación. Cada índice aparece una sola vez, incluso si hay claves iguales; por tanto, $D(x)$ siempre es una permutación para entradas de longitud $n$ y valores finitos. Ejemplo propio: `x = [0.10, 0.40, 0.20, 0.30]` se decodifica como `[0,2,3,1]`. La existencia de sus aristas y del cierre depende del grafo y se comprueba aparte.

La ordenación por comparación cuesta $O(n\log n)$. Muchos vectores diferentes inducen el mismo orden; por ello el costo tiene mesetas y pequeñas variaciones reales pueden no modificar la ruta. Con claves inicialmente continuas casi seguramente no hay empates matemáticos, pero las representaciones finitas y las actualizaciones numéricas exigen resolverlos. No se suman ni redondean identificadores de vértices: las operaciones continuas afectan las claves y el decodificador devuelve índices legales.

El dominio propuesto admite claves finitas sin exigir una caja $[0,1]^n$ después de las actualizaciones. Deben fijarse en M2 los límites numéricos, la inicialización y la respuesta ante desbordamiento; un valor no finito se reporta como error. Recortar claves puede generar muchos empates y cambiar la búsqueda. Normalizar una ruta por rotación o inversión tampoco autoriza a alterar las claves, velocidades o memorias que la originaron.

### 10. Costo computacional y limitaciones de la comparación

Las fuentes respaldan las estructuras de los métodos en los apartados anteriores. Las siguientes cotas son **deducciones propias sobre los esquemas propuestos**, no cotas universales atribuidas a los libros ni tiempos medidos. Se cuentan copias y decodificación. Sea $E(n)$ el costo de evaluar una permutación; para el costo ilustrativo y consultas de arista constantes, $E(n)=O(n)$. Con otras estructuras o fitness, debe sustituirse esa hipótesis.

Se usa $P$ para individuos o partículas, $A$ para hormigas, $S$ para fuentes y $k$ para tamaño del torneo. En la fila de GA se supone selección de élites mediante ordenación de la población; en ABC, una distribución acumulada por fase y muestreo mediante búsqueda binaria. Se conserva el grafo una sola vez y su memoria se excluye de la columna auxiliar.

| Método propuesto | Unidad de trabajo | Tiempo de esa unidad | Memoria auxiliar | Operación que puede dominar |
| --- | --- | --- | --- | --- |
| GA | Generación completa | $O(P(n+k+E(n))+P\log P)$ | $O(Pn)$ | Copiar y cruzar rutas, evaluar y ordenar élites. |
| SA | Un movimiento | $O(n+E(n))$ | $O(n)$ | Copia de ruta y evaluación completa, aunque el intercambio en sitio cueste $O(1)$. |
| ACO con feromona densa | Ciclo de $A$ construcciones completas | $O(A(n^2+E(n))+n^2)$ | $O(n^2+An)$ | Recorrer todos los candidatos en cada paso y evaporar la matriz. |
| ABC | Ciclo de empleadas, observadoras y hasta una exploradora | $O(S(n+E(n))+S\log S)$ | $O(Sn)$ | Copias, búsqueda de posiciones, evaluaciones y selección de fuentes. |
| DE con claves | Generación completa | $O(P(n\log n+E(n)))$ | $O(Pn)$ | Ordenar claves de cada candidato y mantener población anterior y siguiente. |
| PSO con claves | Iteración completa | $O(P(n\log n+E(n)))$ | $O(Pn)$ | Ordenación y almacenamiento de posiciones, velocidades y mejores personales. |

**Justificación.** OX recorre rutas y usa marcas en $O(n)$; los torneos añaden $O(Pk)$ comparaciones de costos guardados. SA copia $n$ posiciones y evalúa una vez. ACO realiza $n$ elecciones que inspeccionan a lo sumo $n$ vértices por hormiga, más evaporación densa; el depósito recorre $n$ pares por ruta. ABC realiza un número proporcional a $S$ de propuestas y evaluaciones, y $S$ búsquedas binarias sobre probabilidades. DE y PSO actualizan $n$ claves y ordenan por comparación para cada candidato. La validación independiente de un posible éxito añade un recorrido y comprobación de unicidad; con las mismas hipótesis no aumenta estas cotas.

La inicialización de todas las poblaciones también consume evaluaciones. Las cotas omiten la carga del grafo, pero no justifican excluirla de los tiempos totales si el protocolo la incluye. Buscar toda una vecindad, añadir reparación de aristas, retroceso, normalización o búsqueda local modifica el costo y debe registrarse. Una matriz densa de feromonas puede resultar limitante antes que el tiempo de búsqueda; no se presupone que sea adecuada para las instancias más grandes.

Una generación de GA, una iteración de PSO y un movimiento de SA realizan cantidades distintas de trabajo. No deben compararse solo con el mismo número de iteraciones. El presupuesto común, las semillas y las configuraciones corresponden al protocolo futuro; las tasas de éxito y tiempos deberán proceder de ejecuciones guardadas, con cada éxito validado. Los estudios de funciones continuas o TSP no proporcionan una clasificación de rendimiento para FHCP.

### 11. Coordinación y decisiones pendientes para M2

| Tema | Propuesta de esta entrega | Coordinación necesaria |
| --- | --- | --- |
| Representación | Permutación común; claves como estado interno de DE y PSO. | [Representación del equipo](search-space.md): índices, cierre, etiquetas y normalización de simetrías. |
| Evaluación | Minimización del costo ilustrativo, separado de validación. | [Issue #5](https://github.com/ZapataFrame/FHCP-Challenge/issues/5): fitness, empates, evaluación incremental y mesetas. |
| Variantes | GA con OX; SA con intercambio; AS penalizado; ABC discreto; DE/rand/1/bin y PSO global con claves. | Revisar estas opciones antes de registrarlas como decisiones aprobadas. |
| Estado y terminación | Mejor evaluado, candidato validado, error y agotamiento separados. | Contrato común de solver y resultado, contadores y granularidad del presupuesto. |
| Aleatoriedad | Generador controlado por ejecución; desempates y orden de actualización declarados. | Reproducibilidad del stack y registro de parámetros y semilla. |
| Comparación | Contar evaluaciones, decodificación y trabajo auxiliar. | [Issue #6](https://github.com/ZapataFrame/FHCP-Challenge/issues/6) y protocolo posterior de benchmarking. |

Antes de implementar se deberán comprobar las propiedades de OX, intercambio, vecinos de ABC y decodificación; rechazo de valores no finitos; reproducción por semilla; límites dentro de bucles; y validación independiente de aristas y cierre. Son requisitos para trabajo futuro, no pruebas ejecutadas de algoritmos existentes.

## Conclusiones

Las seis familias permiten describir mecanismos distintos de exploración: recombinación y selección en GA, aceptación térmica en SA, construcción con memoria de feromonas en ACO, búsqueda y abandono de fuentes en ABC, diferencias poblacionales en DE y memoria personal y colectiva en PSO. Estas diferencias obligan a declarar variantes y parámetros para que una implementación sea reproducible.

GA y SA pueden operar directamente con permutaciones; ABC requiere una vecindad discreta identificada. ACO necesita decidir cómo tratar construcciones parciales y restricciones del grafo. Las propuestas de DE y PSO separan el estado numérico de la ruta mediante un decodificador que preserva visita única, pero genera mesetas y añade costo de ordenación. En todos los casos sigue siendo necesario comprobar las aristas consecutivas y el cierre.

La bibliografía permite fundamentar el diseño y sus límites; no establece qué método ganará en FHCP. Esta entrega deja propuestas revisables para M2. La elección final, la implementación, los parámetros y cualquier conclusión sobre desempeño permanecen pendientes.

## Referencias

[Bibliografía compartida](references.bib). Las primeras cinco entradas se incorporan en el bloque del issue #2; se reutiliza la entrada de Gonçalves y Resende del issue #3. Se presentan paráfrasis y esquemas propios, sin reproducir literalmente párrafos ni pseudocódigos.

- [@luke2013Metaheuristics2] Sean Luke, *Essentials of Metaheuristics*, 2.ª ed., Lulu, 2013, ISBN 978-1-300-54962-8. [Sitio del autor](https://people.cs.gmu.edu/~sean/book/metaheuristics/); [PDF consultado](http://people.cs.gmu.edu/~sean/book/metaheuristics/Essentials.pdf), versión en línea 2.4, enero de 2026. §§0.1, 2.1, 2.4, 3.2, 3.2.3, 3.3.1 y 3.5, pp. 9, 17, 25–26, 37, 45–46 y 56.
- [@kochenderferWheeler2019Optimization] Mykel J. Kochenderfer y Tim A. Wheeler, *Algorithms for Optimization*, 1.ª ed., The MIT Press, 2019, ISBN 978-0-262-03942-0. [Ficha editorial](https://mitpress.mit.edu/9780262039420/algorithms-for-optimization/); [sitio de los autores, descarga de la primera edición](https://algorithmsbook.com/optimization/). PDF revisión `47fd495`, 2022-05-22; §§8.3, 9.2.1, 9.3 y 9.4, pp. 130, 150 y 157–159.
- [@dorigoStuetzle2003Aco] Marco Dorigo y Thomas Stützle, “The Ant Colony Optimization Metaheuristic: Algorithms, Applications, and Advances”, en F. Glover y G. A. Kochenberger, eds., *Handbook of Metaheuristics*, vol. 57, Kluwer Academic Publishers, 2003. [DOI y ficha editorial](https://doi.org/10.1007/0-306-48056-5_9); [capítulo distribuido por el autor](https://iridia.ulb.ac.be/~mdorigo/Published_papers/2002/DorStu2002MetaHandBook.pdf), §4.2.1, pp. 261–262. La ficha editorial indica pp. 250–285; la copia del autor consta de 35 páginas y comienza en p. 251. Los localizadores usados se cotejaron en esa copia; el nombre del archivo con «2002» no cambia el año editorial 2003.
- [@karaboga2005Abc] Dervis Karaboga, *An Idea Based on Honey Bee Swarm for Numerical Optimization*, Technical Report TR06, Erciyes University, octubre de 2005. [Publicaciones del grupo](https://abc.erciyes.edu.tr/publ.htm); [informe original](https://abc.erciyes.edu.tr/pub/tr06_2005.pdf), §III, páginas 6–7 del PDF. No se asigna un DOI que no consta en el informe.
- [@yuce2013Bees] Baris Yuce, Michael S. Packianather, Ernesto Mastrocinque, Duc Truong Pham y Alfredo Lambiase, “Honey Bees Inspired Optimization Method: The Bees Algorithm”, *Insects*, 4(4), pp. 646–662, 2013. [DOI](https://doi.org/10.3390/insects4040646); [registro universitario](https://orca.cardiff.ac.uk/id/eprint/53653/); [PDF editorial](https://mdpi-res.com/d_attachment/insects/insects-04-00646/article_deploy/insects-04-00646.pdf), §4, pp. 651–652. Se utiliza para describir BA, cuyo creador participa como autor, y distinguirlo de ABC.
- [@goncalvesResende2009RandomKeys] José Fernando Gonçalves y Mauricio G. C. Resende, *Biased Random-Key Genetic Algorithms for Combinatorial Optimization*, AT&T Labs Research, 8 de octubre de 2009. [Informe consultado](https://optimization-online.org/wp-content/uploads/2009/10/2423.pdf), §2, p. 2. Se conserva la referencia existente a esta versión; no se confunde con el artículo de revista publicado en 2011.

## Anexo de referencias

Todas las capturas de este anexo se realizaron el **2026-11-01**. Son páginas completas rasterizadas a **200 ppp** mediante Poppler, sin recortes, anotaciones ni reconstrucciones del texto. El número de página PDF cuenta desde uno. Los PDF completos se usaron temporalmente para consulta; no se incorporan al repositorio. Se conservan únicamente las páginas identificativas y las que sustentan las citas.

### luke2013Metaheuristics2

- **Procedencia:** [PDF del autor](http://people.cs.gmu.edu/~sean/book/metaheuristics/Essentials.pdf).
- **Identificación:** portada, PDF 1; página editorial, PDF 2, con ISBN, recomendación de cita de 2013 y licencia CC BY-ND 3.0 US. La portada identifica la actualización en línea de enero de 2026.
- **Contenido citado:** introducción a metaheurísticas, p. 9 / PDF 11; operaciones de búsqueda, p. 17 / PDF 19; SA y metáfora del recocido, pp. 25–26 / PDF 27–28; GA, p. 37 / PDF 39; torneo, p. 45 / PDF 47; elitismo y riesgo de convergencia prematura, p. 46 / PDF 48; memorias personal, de informantes y global en PSO, p. 56 / PDF 58.

![Portada de Essentials of Metaheuristics, segunda edición, versión en línea 2.4](evidence/luke2013Metaheuristics2.png)

![Página editorial de Luke con ISBN, edición bibliográfica y licencia](evidence/luke2013Metaheuristics2-details.png)

![Luke, página 9: introducción a las metaheurísticas y optimización estocástica](evidence/luke2013Metaheuristics2-p009.png)

![Luke, página 17: inicialización, evaluación, copia y modificación de candidatos](evidence/luke2013Metaheuristics2-p017.png)

![Luke, página 25: aceptación térmica y esquema de SA](evidence/luke2013Metaheuristics2-p025.png)

![Luke, página 26: explicación de la metáfora del recocido](evidence/luke2013Metaheuristics2-p026.png)

![Luke, página 37: flujo del algoritmo genético](evidence/luke2013Metaheuristics2-p037.png)

![Luke, página 45: selección por torneo](evidence/luke2013Metaheuristics2-p045.png)

![Luke, página 46: elitismo y convergencia prematura](evidence/luke2013Metaheuristics2-p046.png)

![Luke, página 56: memorias de las partículas e información de sus vecinos](evidence/luke2013Metaheuristics2-p056.png)

### kochenderferWheeler2019Optimization

- **Procedencia:** primera edición enlazada desde [el sitio de los autores](https://algorithmsbook.com/optimization/), [PDF en su enlace de distribución](https://drive.google.com/file/d/1qYjI1igDuBg3x884JKZaCWuJkgdPylHN/view).
- **Identificación:** portada interior, PDF 3; copyright de 2019 y licencia CC BY-NC-ND 4.0, PDF 4. La revisión `47fd495` y su fecha de 2022 aparecen al pie de las páginas de contenido.
- **Contenido citado:** enfriamiento de SA y limitaciones, p. 130 / PDF 150; cromosomas binarios y reales en GA, p. 150 / PDF 170; DE, p. 157 / PDF 177; estado de PSO, p. 158 / PDF 178; ecuaciones y coeficientes de PSO, p. 159 / PDF 179.

![Portada interior de Algorithms for Optimization con autores y editorial](evidence/kochenderferWheeler2019Optimization.png)

![Copyright de 2019 y licencia de Algorithms for Optimization](evidence/kochenderferWheeler2019Optimization-details.png)

![Página 130: calendarios de enfriamiento y límites de SA](evidence/kochenderferWheeler2019Optimization-p130.png)

![Página 150: cromosomas binarios y reales e inicialización de GA](evidence/kochenderferWheeler2019Optimization-p150.png)

![Página 157: evolución diferencial y cruce con coordenada obligatoria](evidence/kochenderferWheeler2019Optimization-p157.png)

![Página 158: posición, velocidad y memoria personal en PSO](evidence/kochenderferWheeler2019Optimization-p158.png)

![Página 159: actualización y parámetros de PSO](evidence/kochenderferWheeler2019Optimization-p159.png)

### dorigoStuetzle2003Aco

- **Procedencia del contenido:** [capítulo del autor](https://iridia.ulb.ac.be/~mdorigo/Published_papers/2002/DorStu2002MetaHandBook.pdf).
- **Procedencia editorial:** [preliminares de Springer](https://link.springer.com/content/pdf/bfm:978-0-306-48056-0/1), PDF 3–4: título del libro, editores, Kluwer y copyright 2003.
- **Identificación del capítulo:** primera página, PDF 1, con título y autores.
- **Contenido citado:** §4.2.1, p. 261 / PDF 11, selección, evaporación y estancamiento; p. 262 / PDF 12, depósito y distinción entre variantes.

![Primera página del capítulo de Dorigo y Stützle](evidence/dorigoStuetzle2003Aco.png)

![Portada interior de Handbook of Metaheuristics con editores y editorial](evidence/dorigoStuetzle2003Aco-book.png)

![Página editorial del Handbook con ISBN y año 2003](evidence/dorigoStuetzle2003Aco-details.png)

![Página 261 del capítulo: construcción y actualización en Ant System](evidence/dorigoStuetzle2003Aco-p261.png)

![Página 262 del capítulo: depósito y variantes de Ant System](evidence/dorigoStuetzle2003Aco-p262.png)

### karaboga2005Abc

- **Procedencia:** [TR06 del grupo de Erciyes University](https://abc.erciyes.edu.tr/pub/tr06_2005.pdf).
- **Identificación:** PDF 1, con título, autor, institución y octubre de 2005.
- **Contenido citado:** §III, PDF 6–7, con grupos de abejas, fases y regla de abandono `limit`. Estas páginas no llevan número impreso.

![Primera página del informe original de ABC, TR06, octubre de 2005](evidence/karaboga2005Abc.png)

![Página PDF 6 de TR06: grupos y fases de ABC](evidence/karaboga2005Abc-p006.png)

![Página PDF 7 de TR06: abandono y parámetro limit](evidence/karaboga2005Abc-p007.png)

### yuce2013Bees

- **Procedencia:** [PDF editorial](https://mdpi-res.com/d_attachment/insects/insects-04-00646/article_deploy/insects-04-00646.pdf), cotejado con [ORCA, Cardiff University](https://orca.cardiff.ac.uk/id/eprint/53653/).
- **Identificación:** p. 646 / PDF 1, título, autores, revista, DOI y fecha de publicación del 6 de noviembre de 2013.
- **Contenido citado:** §4, p. 651 / PDF 6, selección de sitios y reclutamiento; p. 652 / PDF 7, parámetros de élites, reclutas y vecindad. El artículo se distribuye con licencia CC BY 3.0.

![Primera página del artículo de Yuce y colaboradores sobre The Bees Algorithm](evidence/yuce2013Bees.png)

![Página 651: fases y reclutamiento del Bees Algorithm](evidence/yuce2013Bees-p651.png)

![Página 652: parámetros de sitios, élites y vecindad del Bees Algorithm](evidence/yuce2013Bees-p652.png)

### goncalvesResende2009RandomKeys

- **Procedencia:** [informe en Optimization Online](https://optimization-online.org/wp-content/uploads/2009/10/2423.pdf). Se reutiliza su entrada bibliográfica, sin modificar las capturas previas del equipo.
- **Identificación:** p. 1 / PDF 1, título, autores, fecha de versión y carácter de informe técnico.
- **Contenido citado:** §2, p. 2 / PDF 2, separación entre claves y decodificador, ordenación de claves e índices como secuencia.

![Página 1 del informe de Gonçalves y Resende, versión de octubre de 2009](evidence/goncalvesResende2009RandomKeys-p001.png)

![Página 2 del informe: decodificación de claves reales mediante ordenación](evidence/goncalvesResende2009RandomKeys-p002.png)

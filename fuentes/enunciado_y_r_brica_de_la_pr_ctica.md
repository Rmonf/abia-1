# Práctica de Búsqueda Local (2026/2027 1Q)
**Algorismes Bàsics per la Intel·ligència Artificial (ABIA)**  
Departament de Ciències de la Computació - Grau en Intel·ligència Artificial - UPC (FIB)

---

## Capítulo 1: Organización, evaluación y entrega
Esta es la documentación de la práctica de búsqueda local, donde se incluyen:
* Los objetivos de aprendizaje correspondientes al temario de la asignatura.
* La descripción del problema a resolver, los elementos a implementar y los experimentos a realizar.
* El contenido obligatorio del informe final.
* La planificación semanal y dedicación estimada en horas.
* Documentación sobre diseño de experimentos y ajuste de *Simulated Annealing*.
* Rúbrica de evaluación de la práctica.

* **Grupos:** Preferentemente en grupos de tres personas.
* **Entorno:** Python utilizando las clases disponibles en la web del laboratorio y la librería AIMA.
* **Evaluación:** Se valora sobre todo la calidad del análisis de cada experimento, los comentarios y las conclusiones siguiendo la rúbrica.
* **Entrega:** Día 9 de noviembre en formato electrónico vía Racó (informe + código fuente). Entrevista presencial con el profesor de laboratorio entre los días 11 y 13 de noviembre.

---

## Capítulo 2: Objetivos de aprendizaje
El objetivo es resolver un problema mediante algoritmos de búsqueda local demostrándose capaz de:
* Razonar sobre los elementos necesarios para plantear el espacio de soluciones y cómo representarlos teniendo en cuenta las necesidades espacio-temporales.
* Determinar formas de generar una solución inicial, justificar las más adecuadas y probar varias alternativas empíricamente.
* Determinar los operadores de transformación posibles y qué combinación es adecuada considerando el factor de ramificación y la conectividad del espacio de búsqueda.
* Determinar y justificar las funciones heurísticas y compararlas empíricamente.
* Plantear un conjunto de experimentos que muestren la ejecución de **Hill Climbing** y **Simulated Annealing** en escenarios diferentes, comparando la intuición previa (hipótesis) con los resultados reales.
* Experimentar con los parámetros de **Simulated Annealing** ($k$, $\lambda$, iteraciones).
* Comparar el comportamiento de **Hill Climbing** y **Simulated Annealing** respecto a la calidad de sus soluciones y su coste temporal.

---

## Capítulo 3: Uso de herramientas de Inteligencia Artificial
De acuerdo con las recomendaciones del Comité de Ética en Publicaciones (COPE) y el Compromiso de integridad académica de la UPC, se recomienda incluir una declaración explícita de uso de herramientas de IA generativa que incorpore:
* Herramienta/s utilizada/s, indicando las versiones de software.
* Finalidad de su uso.
* Partes o secciones específicas en las que se han utilizado.
* Revisión y edición por parte de los autores del resultado generado.
* Declaración de responsabilidad como autores sobre los contenidos de la obra.

---

## Capítulo 4: El problema

### 4.1. Los elementos del problema
Resolveremos el problema para un único suministrador de electricidad que posee centrales de 3 tipos (**A, B, C**). Al generar una instancia, cada central recibe un valor fijo de producción dentro de su intervalo. Cuando está en marcha, produce ese valor completo aunque una parte no se utilice (se paga el coste de producir toda su capacidad especificada). Cuando está parada, únicamente se aplica el coste fijo en parada.

| Tipo | Producción | Coste fijo producción | Coste de producción | Coste fijo en parada |
| :--- | :--- | :--- | :--- | :--- |
| **A** | $250\text{ a }750\text{ MW}$ | $20\,000\text{ EUR}$ | $50 \cdot \text{Prod}\text{ EUR}$ | $15\,000\text{ EUR}$ |
| **B** | $100\text{ a }250\text{ MW}$ | $10\,000\text{ EUR}$ | $80 \cdot \text{Prod}\text{ EUR}$ | $5\,000\text{ EUR}$ |
| **C** | $10\text{ a }100\text{ MW}$ | $5\,000\text{ EUR}$ | $150 \cdot \text{Prod}\text{ EUR}$ | $1\,500\text{ EUR}$ |

*Costes expresados en euros por día.*

Los grandes consumidores se dividen en tres grupos según su consumo: extra grandes (**XG**), muy grandes (**MG**) y grandes (**G**). Tienen dos prioridades de contrato: **servicio garantizado** y **servicio no garantizado**. Si un cliente con contrato no garantizado no recibe suministro un día, recibe una indemnización en función del consumo de su contrato:

| Cliente | Consumo | Garantizado | No Garantizado | Indemnización |
| :--- | :--- | :--- | :--- | :--- |
| **XG** | $5\text{ a }20\text{ MW}$ | $400\text{ EUR/MW}$ | $300\text{ EUR/MW}$ | $50\text{ EUR/MW}$ |
| **MG** | $2\text{ a }5\text{ MW}$ | $500\text{ EUR/MW}$ | $400\text{ EUR/MW}$ | $50\text{ EUR/MW}$ |
| **G** | $1\text{ a }2\text{ MW}$ | $600\text{ EUR/MW}$ | $500\text{ EUR/MW}$ | $50\text{ EUR/MW}$ |

Cada central y cada cliente están ubicados en coordenadas enteras $(x, y)$ dentro de un área de $100 \times 100\text{ km}$. La distancia entre central y cliente es la euclidiana. El transporte de electricidad tiene una pérdida según la distancia:

| Distancia | Pérdida ($p$) |
| :--- | :--- |
| Hasta $10\text{ km}$ ($\le 10$) | $0\%$ ($0.0$) |
| Hasta $25\text{ km}$ ($\le 25$) | $10\%$ ($0.1$) |
| Hasta $50\text{ km}$ ($\le 50$) | $20\%$ ($0.2$) |
| Hasta $75\text{ km}$ ($\le 75$) | $40\%$ ($0.4$) |
| Más de $75\text{ km}$ ($> 75$) | $60\%$ ($0.6$) |

El porcentaje de pérdida se aplica a la potencia enviada desde la central. Para satisfacer una demanda $d$ con una pérdida $p$, debe asignarse desde la central una potencia efectiva de:
$$\text{Potencia asignada} = \frac{d}{1 - p}$$
*(Ejemplo: para suministrar $5\text{ MW}$ a $50\text{ km}$ con pérdida del $20\%$, se asignan $6.25\text{ MW}$ de la central, pero solo se cobran los $5\text{ MW}$ contratados).*

### 4.2. El problema
Para un día concreto, dada la lista de centrales y clientes, una solución determinará para cada central qué clientes tiene asignados con el objetivo de obtener el **máximo beneficio**.

### 4.3. Criterios de la solución
1. No se puede asignar a una central más demanda (ajustada por pérdidas) de la que puede producir.
2. Si una central está en marcha, genera toda su producción; la que no se asigna a algún cliente se pierde (pero se paga su coste de producción).
3. Un cliente solo se asigna a una central.
4. A los clientes se les sirve siempre completamente (no se puede servir parcialmente).
5. Todos los clientes que han contratado servicio garantizado han de ser servidos.
6. Se ha de maximizar la ganancia obtenida.

### 4.4. Las clases y funciones Python para los escenarios simulados
Se proporcionan 6 módulos base:
1. `power_plant.py`: Clase `PowerPlant` (tipo, producción en MW, coordenadas $x, y$).
2. `customer.py`: Clase `Customer` (tipo de consumo, demanda en MW, contrato garantizado/no garantizado, coordenadas $x, y$).
3. `power_plants.py`: Función `generate_power_plants(counts, seed)`.
4. `customers.py`: Función `generate_customers(count, type_proportions, guaranteed_proportion, seed)`.
5. `energy.py`: Funciones de consulta de tarifas, penalizaciones, costes de centrales y fracción de pérdida por distancia.
6. `demo_energy.py`: Ejemplo de generación de escenario y consultas económicas.

### 4.5. Tareas a realizar
1. Implementar la clase del estado permitiendo variar el número y proporciones de clientes y centrales.
2. Definir e implementar la representación del estado eficiente en espacio y tiempo para usar con AIMA.
3. Definir e implementar **dos estrategias** para generar la solución inicial. La búsqueda debe comenzar siempre desde una solución válida (todos los clientes garantizados servidos), salvo en el Experimento 5. Comprobar siempre la factibilidad de las instancias aleatorias y usar las mismas instancias al comparar estrategias y algoritmos.
4. Definir e implementar la función generadora de estados sucesores decidiendo el conjunto de operadores. **Debe implementarse de manera diferente para Hill Climbing (todos los sucesores) y Simulated Annealing (un único sucesor aleatorio)** para poder comparar sus tiempos de ejecución.
5. Definir e implementar la función heurística que implementa los criterios de calidad de 4.3.

### 4.6. Experimentos (Mínimo 10 repeticiones por experimento y cálculo de medias)
1. **Experimento 1 (Operadores):** Escenario base con centrales $(5, 10, 25)$ para tipos $(A, B, C)$, $1000$ clientes con proporciones $(0.25, 0.30, 0.45)$ para $(XG, MG, G)$ y $75\%$ garantizados. Usando **Hill Climbing** y una estrategia inicial fija, determinar qué conjunto de operadores da mejores resultados. Fijar estos operadores para el resto de experimentos.
2. **Experimento 2 (Solución inicial):** En el mismo escenario base y con **Hill Climbing** (usando los operadores del Exp. 1), determinar cuál de las dos estrategias de solución inicial da mejores resultados. Fijar la mejor para el resto de experimentos.
3. **Experimento 3 (Parámetros de Simulated Annealing):** Con el mismo escenario, heurística, operadores e inicialización escogidos, determinar los parámetros ($k$, $\lambda$, iteraciones) que dan mejor resultado para **Simulated Annealing**.
4. **Experimento 4 (Escalabilidad temporal):** Con **Hill Climbing**, estudiar cómo evoluciona el tiempo de ejecución manteniendo las proporciones del escenario inicial:
   * Para $40$ centrales fijas: comenzar con $250$ clientes e incrementar de $250$ en $250$ hasta ver la tendencia.
   * Para $1000$ clientes fijos: comenzar con $40$ centrales e incrementar de $40$ en $40$ hasta ver la tendencia.
5. **Experimento 5 (Penalización de garantizados desde estado vacío):** Añadir una penalización en la función heurística cuando no se sirva a un cliente garantizado, considerando todas las soluciones válidas y partiendo siempre de una **solución inicial vacía**. Experimentar con diferentes valores de penalización usando **Hill Climbing** y **Simulated Annealing**, determinando el rango de valores a partir del cual se obtiene siempre una solución válida (todos los garantizados servidos).
6. **Experimento 6 (Duplicar y triplicar centrales Tipo C):** Partiendo del escenario inicial, experimentar si duplicar ($50$) y triplicar ($75$) las centrales de tipo C hace que las centrales de tipo A y B se usen menos, usando **Hill Climbing** y **Simulated Annealing** con la heurística original, y observar el aumento de coste en tiempo.

---

## Capítulo 5: Guión de la práctica
Preguntas clave que debe responder el diseño:
* ¿Qué elementos intervienen en el problema?
* ¿Cuál es el espacio de búsqueda y qué tamaño tiene?
* ¿Qué es un estado inicial y qué condiciones cumple un estado final (`goal_test` siempre retorna `False` en búsqueda local)?
* ¿Qué operadores permiten modificar los estados y qué factor de ramificación tienen?
* Recordar que las funciones heurísticas en el informe se plantean para minimizarse (cambiar el signo al beneficio).

La documentación final debe incluir obligatoriamente:
* Descripción y justificación de la implementación del estado y tamaño del espacio de búsqueda.
* Descripción y justificación de los operadores elegidos y su factor de ramificación.
* Descripción y justificación de las estrategias de solución inicial.
* Descripción y justificación de las funciones heurísticas.
* Para cada experimento: condiciones, hipótesis previa (qué se esperaba), resultados obtenidos (medias, desviaciones, gráficas), comparaciones y conclusiones.
* Comparación entre Hill Climbing y Simulated Annealing.

---

## Capítulo 7: Experimentación y Simulated Annealing
* **Cómo NO presentar resultados:** Nunca incluir tablas gigantes con los resultados individuales de cada réplica sin resumir, ni gráficos de líneas conectando réplicas independientes (que no son series temporales), ni ejes truncados engañosos. Usar medias, desviaciones estándar y diagramas de caja (*boxplots*).
* **Parámetros de Simulated Annealing en AIMA:**
  * Temperatura en la iteración $T$: $F(T) = k \cdot e^{-\lambda T}$.
  * Probabilidad de aceptar un estado peor con diferencia de energía $\Delta E$: $P(\text{estado}) = e^{-\Delta E / F(T)}$.
  * Cuanto mayor es $k$, más tarda en comenzar a decrecer la probabilidad de aceptación. Cuanto mayor es $\lambda$, más rápido desciende.

---

## Capítulo 8: Rúbrica de evaluación (Nivel "Bien")
1. **Identificación del problema:** Descripción elaborada, identificación y análisis detallado de las características y elementos del estado, y justificación de por qué es un problema de búsqueda local.
2. **Estado del problema y representación:** Descripción/justificación detallada, representación adecuada y eficiente, y análisis matemático del tamaño del espacio de búsqueda.
3. **Representación y análisis de los operadores:** Descripción detallada (condiciones de aplicabilidad y efectos), análisis del factor de ramificación y explicación de la elección de operadores.
4. **Análisis de la función heurística:** Explicación de los factores que intervienen, justificación de las heurísticas escogidas, sus efectos en la búsqueda y las ponderaciones empleadas.
5. **Elección y generación del estado inicial:** Descripción de los algoritmos de solución inicial y justificación en términos de bondad de la solución y coste computacional de hallarla.
6. **Parte experimental:** Experimentos informativos con múltiples ejecuciones (mínimo 10), criterio uniforme de comparación (mismas semillas), uso de tablas resumidas, estadísticas y gráficos, comparando lo que se esperaba con lo obtenido en: solución inicial, operadores, función heurística/penalizaciones, ajuste sistemático de SA, comparación HC vs SA y preguntas de los escenarios propuestos.
7. **Calidad de la documentación:** Estructura lógica (planteamiento, desarrollo, resultados y conclusiones), claridad expositiva, ausencia de faltas ortográficas y gráficos claros con etiquetas y unidades.
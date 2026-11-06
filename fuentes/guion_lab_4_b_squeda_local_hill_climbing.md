# Laboratorio de GIA-ABIA — Sesión 4: Búsqueda local (Hill Climbing)

## Contenidos y Objetivos
* Entender los algoritmos de búsqueda local en un espacio de soluciones frente a la búsqueda de caminos en un espacio de estados.
* Formular un problema de optimización combinatoria (ejemplo: *Bin Packing*) en un espacio de soluciones.
* Comprender la diferencia entre copia superficial y copia independiente de estructuras mutables en el estado.
* Modelar el problema separando **Parámetros**, **Operadores**, **Estado** y **Clase Problem**, y conectarlo con `hill_climbing` de `aima.search`.

---

## 1. Búsqueda en el espacio de soluciones y Hill Climbing
En la búsqueda en un espacio de soluciones:
* **Nodo:** Representa una solución completa y válida del problema de optimización.
* **Arista:** Representa una modificación local (operador) que transforma una solución en otra solución vecina válida.
* **Inicio:** Se parte de una solución inicial válida y se intenta mejorar su valor según una función de evaluación.
* **Objetivo:** Interesa únicamente la configuración final encontrada; el camino seguido es irrelevante y no existe un estado objetivo prefijado (`goal_test` retorna siempre `False`).

### Esquema de `hill_climbing` en AIMA:
```python
def hill_climbing(problem):
    current = problem.initial
    while True:
        neighbor = max(problem.neighbors(current), key=problem.value)  # AIMA desempata al azar
        if problem.value(neighbor) <= problem.value(current):
            return current  # Ningún vecino mejora la solución actual
        current = neighbor
```
*Nota importante:* Cuando varios vecinos empatan con el valor máximo, el `hill_climbing` de AIMA elige uno al azar usando el módulo `random`. Para que los experimentos sean reproducibles, se debe fijar `random.seed(...)` antes de invocar el algoritmo.

---

## 2. Arquitectura de 4 módulos para Búsqueda Local con AIMA

### 2.1. Modelado de los parámetros de ejecución (`ProblemParameters`)
Separa los datos constantes de la instancia del problema (capacidades, demandas, costes) para compartirlos por referencia sin duplicarlos en cada estado sucesor:
```python
class ProblemParameters(object):
    def __init__(self, h_max: int, v_h: List[int], p_max: int, c_max: int):
        self.h_max = h_max
        self.v_h = v_h
        self.p_max = p_max
        self.c_max = c_max
```

### 2.2. Representación de los operadores (`Operators`)
Se define una clase base para los operadores y subclases para cada tipo de modificación local (por ejemplo, mover un elemento a otro contenedor o intercambiar dos elementos):
```python
class BinPackingOperator(object):
    pass

class MoveParcel(BinPackingOperator):
    def __init__(self, p_i: int, c_j: int, c_k: int):
        self.p_i = p_i
        self.c_j = c_j
        self.c_k = c_k

class SwapParcels(BinPackingOperator):
    def __init__(self, p_i: int, p_j: int):
        self.p_i = p_i
        self.p_j = p_j
```

### 2.3. Representación del estado (`StateRepresentation`) y cuidado con las copias
Al implementar el método `copy(self)` del estado, hay que asegurarse de copiar todas las listas o conjuntos internos mutables. Si se hace una copia superficial que comparte referencias a listas internas, modificar un sucesor corromperá el estado padre y los demás vecinos.
La clase `StateRepresentation` debe incluir:
* `copy(self) -> StateRepresentation`
* `generate_actions(self) -> Generator[Operator, None, None]`
* `apply_action(self, action: Operator) -> StateRepresentation`
* `heuristic(self) -> float` (definida como función de coste a **minimizar**).

### 2.4. Clase del problema: integración con AIMA (`Problem`)
**Atención:** AIMA **maximiza** `problem.value(state)`, mientras que nuestra función `state.heuristic()` está definida para **minimizarse**. Por tanto, `value` debe devolver `-state.heuristic()`:

```python
from aima.search import Problem

class BinPackingProblem(Problem):
    def __init__(self, initial_state: StateRepresentation):
        super().__init__(initial_state)

    def actions(self, state: StateRepresentation):
        return state.generate_actions()

    def result(self, state: StateRepresentation, action: BinPackingOperator) -> StateRepresentation:
        return state.apply_action(action)

    def value(self, state: StateRepresentation) -> float:
        # AIMA maximiza value, por lo que negamos la heurística
        return -state.heuristic()

    def goal_test(self, state: StateRepresentation) -> bool:
        return False  # La búsqueda local no tiene estado objetivo prefijado
```
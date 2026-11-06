# Laboratorio de GIA-ABIA — Sesión 5: Búsqueda local (Simulated Annealing)

## Contenidos y Objetivos
* Comprender por qué *Simulated Annealing* puede escapar de óptimos locales y mesetas al aceptar temporalmente soluciones peores con una probabilidad controlada por la temperatura $T$.
* Utilizar `simulated_annealing` y `exp_schedule(k, lam, limit)` de `aima.search`.
* Optimizar la generación de sucesores implementando `generate_one_action()` en el estado y el flag `use_one_action` en la clase `Problem` para no construir todo el vecindario en cada paso de *Simulated Annealing*.

---

## 1. Fundamentos de Simulated Annealing en AIMA
En cada iteración $t$, el algoritmo selecciona un vecino al azar $s' \in N(s)$ y calcula $\Delta V = V(s') - V(s)$:
* Si $\Delta V > 0$ (mejora el valor), acepta $s'$ siempre.
* Si $\Delta V \le 0$ (empeora o mantiene el valor), lo acepta con probabilidad:
  $$P(\text{aceptar } s' \mid s, T(t)) = e^{\Delta V / T(t)}$$

### Función de enfriamiento exponencial (`exp_schedule`)
En `aima.search`, la función `exp_schedule(k, lam, limit)` define la temperatura en la iteración $t$ como:
$$T(t) = \begin{cases} k \cdot e^{-\lambda t} & \text{si } t < \text{limit} \\ 0 & \text{si } t \ge \text{limit} \end{cases}$$
* **`k` (temperatura inicial):** Cuanto mayor sea respecto a los cambios habituales $|\Delta V|$ de la heurística, más probable será aceptar empeoramientos al principio.
* **`lam` ($\lambda$, velocidad de enfriamiento):** Un valor menor mantiene temperaturas altas durante más iteraciones; uno mayor enfría el sistema más rápido.
* **`limit` (límite de iteraciones):** Fija el número máximo de iteraciones antes de devolver $T=0$ y detener el algoritmo.

```python
from aima.search import simulated_annealing, exp_schedule

sa_state = simulated_annealing(
    problem,
    schedule=exp_schedule(k=1, lam=0.0005, limit=25000)
)
```

---

## 2. Optimización crítica de la generación de sucesores (`generate_one_action`)
La implementación de `simulated_annealing` en `aima/search.py` es la siguiente:
```python
def simulated_annealing(problem, schedule=exp_schedule()):
    current = Node(problem.initial)
    for t in range(sys.maxsize):
        T = schedule(t)
        if T == 0:
            return current.state
        neighbors = current.expand(problem)
        if not neighbors:
            return current.state
        next_choice = random.choice(neighbors)
        delta_e = problem.value(next_choice.state) - problem.value(current.state)
        if delta_e > 0 or probability(np.exp(delta_e / T)):
            current = next_choice
```

Si `problem.actions(state)` devuelve todos los operadores posibles (como necesita *Hill Climbing*), la llamada `current.expand(problem)` dentro del bucle de *Simulated Annealing* instanciará todos los miles de estados vecinos solo para elegir uno con `random.choice(neighbors)` y descartar el resto.

### Solución obligatoria para la práctica:
1. Añadir un método `generate_one_action(self)` en `StateRepresentation` que escoja aleatoriamente los parámetros de un único movimiento válido y haga un único `yield` de ese operador. Así `current.expand(problem)` construirá una lista de longitud 1 y `random.choice(neighbors)` será instantáneo.
2. Añadir el argumento booleano `use_one_action: bool = False` al constructor de la subclase de `Problem` para alternar limpiamente entre ambos algoritmos:

```python
class EnergyProblem(Problem):
    def __init__(self, initial_state: StateRepresentation, use_one_action: bool = False):
        super().__init__(initial_state)
        self.use_one_action = use_one_action

    def actions(self, state: StateRepresentation):
        if self.use_one_action:
            return state.generate_one_action()
        return state.generate_actions()
```
* Para **Hill Climbing**, se instancia el problema con `use_one_action=False`.
* Para **Simulated Annealing**, se instancia el problema con `use_one_action=True`.
# Laboratorio de GIA-ABIA — Sesión 2: Depuración, generadores y el estado como objeto

## Contenidos y Objetivos
* Utilizar un depurador (`pdb` o VS Code) para ejecutar código paso a paso e inspeccionar variables.
* Comprender la diferencia entre listas, iteradores, expresiones generadoras y funciones generadoras (`yield`), así como la evaluación bajo demanda para ahorrar memoria temporal en problemas con alto factor de ramificación.
* Representar los estados mediante objetos inmutables (o con copia explícita) implementando métodos de igualdad (`__eq__`) y hash (`__hash__`) consistentes.

---

## 1. Generadores en Python: ahorro de memoria en problemas de búsqueda
Un generador es un iterador que produce valores bajo demanda. En lugar de construir y devolver todos los valores a la vez en una lista en memoria, los genera uno a uno a medida que se solicitan.

### 1.1. Funciones generadoras con `yield`
Cuando la producción de cada acción válida requiere bucles anidados y comprobación de condiciones, se utiliza una función generadora mediante la palabra clave `yield`. Llamar a la función devuelve un objeto generador y cada paso del bucle consumidor reanuda la ejecución desde el último `yield`:

```python
from typing import Generator

def actions(self, current_state) -> Generator[Flip, None, None]:
    total_coins = len(current_state)
    for x in range(total_coins):
        yield Flip(x, (x + 1) % total_coins)
```

En problemas con factores de ramificación muy grandes (como ocurre en búsqueda local con decenas de miles de vecinos), usar generadores evita materializar simultáneamente listas gigantescas de objetos de acción si el consumidor los procesa incrementalmente.

---

## 2. Uso de objetos para representar estados
Las listas de Python son mutables y no son *hashables*. Para encapsular correctamente el estado de un problema en AIMA se recomienda:
1. **Evitar efectos laterales entre sucesores:** Ningún método debe mutar el estado original al generar sucesores; se debe crear una copia independiente mediante `.copy()` antes de aplicar los cambios de un operador.
2. **Reimplementar `__eq__` y `__hash__`:** Para que dos instancias distintas con la misma configuración interna se reconozcan como equivalentes.
3. **Encapsular las operaciones del dominio dentro de la clase del estado:** Métodos como `generate_actions(self)` y `apply_action(self, action)` deben pertenecer a la clase del estado para no exponer su estructura interna a la clase `Problem`.

### Patrón de implementación recomendado en el Laboratorio 2:
```python
from typing import Generator, List

class ImmutableCoinsState(object):
    def __init__(self, coins_state: List[str]):
        self.coins_state = coins_state

    def generate_actions(self) -> Generator[Flip, None, None]:
        total_coins = len(self.coins_state)
        return (Flip(x, (x + 1) % total_coins) for x in range(total_coins))

    def apply_action(self, next_action: Flip) -> "ImmutableCoinsState":
        # Copiar el estado antes de aplicar la acción
        new_state = self.coins_state.copy()
        new_state[next_action.pos_1] = self.flip_coin(self.coins_state[next_action.pos_1])
        new_state[next_action.pos_2] = self.flip_coin(self.coins_state[next_action.pos_2])
        return ImmutableCoinsState(new_state)

    def __eq__(self, other):
        return (
            isinstance(other, ImmutableCoinsState)
            and self.coins_state == other.coins_state
        )

    def __hash__(self):
        return hash(tuple(self.coins_state))

    def __repr__(self):
        return str.join("", self.coins_state)
```
# Laboratorio de GIA-ABIA — Sesión 3: Búsqueda heurística y experimentación

## Contenidos y Objetivos
* Comprender la implementación de funciones de evaluación y heurísticas en `aima`.
* Implementar el operador de comparación `<` (`__lt__`) en la clase del estado para resolver empates entre nodos sin errores de ejecución.
* Medir tiempos de ejecución de forma fiable mediante `timeit` con múltiples repeticiones.
* Visualizar e interpretar los resultados experimentales mediante diagramas de caja (*boxplots*) con `matplotlib`.

---

## 1. Operador de comparación para desempatar estados (`__lt__`)
En `aima`, la clase `Node` implementa `__lt__` delegando la comparación en los objetos `state` cuando dos nodos tienen exactamente el mismo valor de evaluación. Por tanto, nuestra clase de representación del estado debe implementar obligatoriamente `__lt__`. De lo contrario, se produce el error:
`TypeError: '<' not supported between instances of 'State' and 'State'`

Para obtener un comportamiento determinista entre ejecuciones, se recomienda comparar la representación canónica (lista o tupla) del estado:

```python
class StateRepresentation(object):
    def __lt__(self, other):
        if not isinstance(other, StateRepresentation):
            return NotImplemented
        return tuple(self.state_list) < tuple(other.state_list)
```

---

## 2. Experimentación: evaluación de algoritmos de búsqueda

### Principios básicos de experimentación
* **Repetición:** Ejecutar cada experimento al menos 10 o 15 veces y conservar todas las mediciones. Una única ejecución no es representativa.
* **Robustez estadística:** Presentar una medida central (media o mediana) junto con una medida de variabilidad (desviación estándar o rango intercuartílico).
* **Resolución:** Utilizar el temporizador de alta resolución de `timeit` y excluir operaciones de entrada/salida, impresión por pantalla o guardado de gráficas de la medición del tiempo.

### 2.1. Medición de tiempos con `timeit`
```python
from timeit import timeit

times = [timeit(lambda: search_algorithm(problem), number=1) for _ in range(10)]
```

### 2.2. Visualización de resultados con `matplotlib`
Principios básicos de visualización para el informe:
* **Claridad:** Identificar siempre los ejes (`xlabel`, `ylabel`), las unidades (p. ej., segundos, EUR) y el título (`title`).
* **Consistencia:** Usar las mismas escalas y unidades al comparar alternativas.
* **Reproducibilidad:** Generar las gráficas directamente desde el script en Python guardándolas en disco (`plt.savefig`).

```python
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

data_to_plot = [times_alg1, times_alg2]
labels = ['Algoritmo 1', 'Algoritmo 2']

plt.boxplot(data_to_plot, labels=labels)
plt.ylabel('Tiempo de ejecucion (segundos)')
plt.title('Comparacion de algoritmos mediante diagramas de caja')
plt.savefig('comparacion.png')
```
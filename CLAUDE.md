# CLAUDE.md — Práctica de Búsqueda Local (ABIA, GIA UPC)

## Contexto

Práctica 1 de ABIA (Algorismes Bàsics per a la IA, Grau en IA, UPC-FIB), curso 2026/27 1Q.
Problema: asignar clientes a centrales eléctricas para maximizar el beneficio diario, resuelto
con **Hill Climbing** y **Simulated Annealing** de la librería AIMA (`aima==2023.2.6`).

- Enunciado y rúbrica: `fuentes/enunciado_y_r_brica_de_la_pr_ctica.md`
- Guiones de laboratorio (patrones de código a seguir): `fuentes/guion_lab_*.md`
- Entrega: 9 de noviembre (informe + código). Entrevista con el profesor: 11–13 de noviembre.

**Prioridad absoluta: código funcional y fácil de explicar en la entrevista.** El autor tiene que
poder justificar cada línea. Ante la duda, lo simple y explícito gana a lo ingenioso u optimizado.
No añadir funcionalidades que el enunciado no pida.

## Estructura

| Fichero | Rol |
| --- | --- |
| `base/` | Módulos proporcionados por el profesorado (`power_plant`, `customer`, `power_plants`, `customers`, `energy`, `demo_energy`). **No modificar.** |
| `energy_problem_parameters.py` | Datos constantes de la instancia, precalculados (costes, ingresos, matriz `effective_demand[i][j]` = demanda ajustada por pérdidas). Compartido por todos los estados, nunca se copia. |
| `energy_state.py` | `StateRepresentation` + generadores de sucesores (HC: todos; SA: uno aleatorio) + `apply_action` con actualización incremental del beneficio + estrategias de solución inicial (aleatoria, greedy, vacía). |
| `energy_operators.py` | Clases de operador (acciones). |
| `energy_problem.py` | Subclase de `aima.search.Problem`. `value = -heuristic`, `goal_test` siempre `False`. |
| `run_experiments.py` | Punto de entrada; los 6 experimentos del apartado 4.6 del enunciado. |

## Ejecución

Entorno gestionado con `uv` (`pyproject.toml`, `uv.lock`, Python >= 3.11).

```bash
uv run python run_experiments.py        # todos los experimentos
uv run python run_experiments.py 3      # solo el experimento 3 (si existe la opción CLI)
```

Los módulos de `base/` se importan por nombre (`from customer import ...`), así que `base/`
tiene que estar en el path (lo añade el punto de entrada).

## Decisiones de diseño (hay que poder defenderlas)

- **Estado:** `assignment[i]` = central del cliente `i` o `-1` si no se sirve. Además se mantienen
  `plant_used_mw`, `plant_customer_count` y `profit` para evaluar en O(1) por movimiento.
- **Heurística:** `heuristic() = -profit` (se minimiza, como pide el enunciado). El beneficio
  incluye ingresos, indemnizaciones de no garantizados no servidos y costes de centrales en
  marcha/paradas. En el Experimento 5 se añade una penalización por MW de garantizado no servido.
- **Operadores:** mover/asignar un cliente a una central con capacidad libre, y desasignar
  (solo no garantizados, salvo en el Exp. 5).
- **Soluciones iniciales:** aleatoria válida (solo garantizados, centrales al azar) y greedy
  (garantizados primero en la central más cercana ya encendida; luego no garantizados solo en
  centrales ya encendidas). Estado vacío solo en el Exp. 5.
- **Reproducibilidad:** mismas semillas para comparar estrategias; `random.seed(s)` justo antes de
  cada ejecución de HC/SA (AIMA desempata y elige vecinos con `random`).

## Hechos conocidos del comportamiento

- **Meseta:** casi todos los movimientos tienen delta de beneficio 0 (mover un cliente entre dos
  centrales encendidas no cambia nada; apagar una central exige varios pasos neutros). El
  `hill_climbing` de AIMA para ante la falta de mejora estricta, así que **HC desde el greedy no
  avanza** (semilla 2: 835 342 € → 835 342 €). Desde la aleatoria sí mejora, pero acaba por debajo
  del greedy. Es un resultado a explicar en el informe, no un bug.
- **Swap no aporta con esta heurística:** intercambiar dos clientes asignados nunca cambia el
  beneficio, así que HC nunca lo acepta.
- **Factibilidad:** las semillas se filtran con el greedy. Que el greedy falle no prueba que la
  instancia sea infactible (en el escenario base falla en ~17 de las 39 primeras semillas). En el
  informe se describe como "factible según el greedy".

## Convenciones

- Comentarios y docstrings en español, breves; explicar el *porqué*, no el *qué*.
- Seguir los patrones de los guiones de laboratorio (nombres `StateRepresentation`,
  `generate_actions`, `generate_one_action`, `apply_action`, `heuristic`).
- Nada de dependencias nuevas. No tocar `base/`.
- No commitear `__pycache__/`, PNG generados ni scripts de prueba temporales.
- Un commit por cambio lógico, con mensaje en español que diga qué y por qué.
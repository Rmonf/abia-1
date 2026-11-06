"""
Representación del estado, constructores de solución inicial, generadores de acciones
y función heurística. Sigue el patrón de las Sesiones 2, 4 y 5 de laboratorio.
"""

import random
from random import Random
from typing import Generator, List, Optional
from energy_problem_parameters import EnergyProblemParameters
from energy_operators import EnergyOperator, AssignOrMoveCustomer


class StateRepresentation(object):
    """
    Representa una asignación de clientes a centrales eléctricas:
    - `assignment[i]` = índice de la central (0..M-1) a la que está asignado el cliente `i`,
      o -1 si el cliente `i` no recibe suministro.
    - `plant_used_mw[j]` = MW totales comprometidos en la central `j` (incluyendo pérdidas).
    - `plant_customer_count[j]` = número de clientes asignados a la central `j`.
    - `profit` = beneficio económico neto actual en EUR/día (mantenido incrementalmente).
    """

    def __init__(
        self,
        params: EnergyProblemParameters,
        assignment: List[int],
        plant_used_mw: Optional[List[float]] = None,
        plant_customer_count: Optional[List[int]] = None,
        profit: Optional[float] = None,
    ):
        self.params = params
        self.assignment = assignment

        if plant_used_mw is None:
            # Estado nuevo: se calcula todo desde la asignación
            self.plant_used_mw = [0.0] * params.n_plants
            self.plant_customer_count = [0] * params.n_plants
            for i, p_idx in enumerate(assignment):
                if p_idx != -1:
                    self.plant_used_mw[p_idx] += params.effective_demand[i][p_idx]
                    self.plant_customer_count[p_idx] += 1
            self.profit = self._compute_full_profit()
        else:
            # Copia: los valores ya vienen calculados
            self.plant_used_mw = plant_used_mw
            self.plant_customer_count = plant_customer_count
            self.profit = profit

    def _compute_full_profit(self) -> float:
        """Calcula el beneficio diario exacto desde cero según los criterios de 4.3."""
        p = self.params
        total = 0.0
        for i, p_idx in enumerate(self.assignment):
            if p_idx != -1:
                total += p.customer_served_revenue[i]
            else:
                total -= p.customer_unserved_penalty[i]

        for j in range(p.n_plants):
            if self.plant_customer_count[j] > 0:
                total -= p.plant_running_total_cost[j]
            else:
                total -= p.plant_stopped_cost[j]
        return total

    def copy(self) -> "StateRepresentation":
        """Copia independiente del estado (Sesión 4: evitar copias superficiales compartidas)."""
        return StateRepresentation(
            params=self.params,
            assignment=self.assignment.copy(),
            plant_used_mw=self.plant_used_mw.copy(),
            plant_customer_count=self.plant_customer_count.copy(),
            profit=self.profit,
        )

    def _fits(self, i: int, j: int) -> bool:
        """¿Cabe la demanda efectiva del cliente `i` en la capacidad libre de la central `j`?"""
        p = self.params
        return self.plant_used_mw[j] + p.effective_demand[i][j] <= p.plant_capacity[j] + 1e-9

    def _can_unassign(self, i: int) -> bool:
        """Se puede dejar sin servicio a `i` si está asignado y el problema lo permite."""
        p = self.params
        if not p.enable_unassign or self.assignment[i] == -1:
            return False
        return p.allow_unserved_guaranteed or not p.is_guaranteed[i]

    def generate_actions(self) -> Generator[EnergyOperator, None, None]:
        """
        Generador bajo demanda con `yield` para Hill Climbing (Sesión 2 y 4).
        Produce todas las acciones válidas desde el estado actual.
        """
        for i in range(self.params.n_customers):
            curr_p = self.assignment[i]
            # Mover o asignar a cualquier otra central con capacidad libre suficiente
            for j in range(self.params.n_plants):
                if j != curr_p and self._fits(i, j):
                    yield AssignOrMoveCustomer(i, curr_p, j)
            # Desasignar (dejar sin servicio)
            if self._can_unassign(i):
                yield AssignOrMoveCustomer(i, curr_p, -1)

    def generate_one_action(self) -> Generator[EnergyOperator, None, None]:
        """
        Generador de UN ÚNICO sucesor aleatorio para Simulated Annealing (Sesión 5).
        Se elige un cliente y un destino al azar (-1 = desasignar) y se reintenta hasta que
        el movimiento sea válido. En las instancias de la práctica siempre hay alguno (hay
        centrales con capacidad libre), así que el bucle termina en pocos intentos.
        Usa el `random` global para que `random.seed(s)` haga reproducible la ejecución.
        """
        while True:
            i = random.randrange(self.params.n_customers)
            j = random.randrange(-1, self.params.n_plants)
            curr_p = self.assignment[i]
            if j == -1:
                valid = self._can_unassign(i)
            else:
                valid = j != curr_p and self._fits(i, j)
            if valid:
                yield AssignOrMoveCustomer(i, curr_p, j)
                return

    def apply_action(self, action: AssignOrMoveCustomer) -> "StateRepresentation":
        """
        Crea un nuevo estado aplicando `action` y actualiza el beneficio en O(1).
        """
        new_state = self.copy()
        p = self.params

        i = action.c_i
        old_p = action.old_p
        new_p = action.new_p

        # 1. Quitar de old_p si estaba asignado
        if old_p != -1:
            new_state.plant_used_mw[old_p] -= p.effective_demand[i][old_p]
            new_state.plant_customer_count[old_p] -= 1
            if new_state.plant_customer_count[old_p] == 0:
                new_state.plant_used_mw[old_p] = 0.0
                # La central pasa de estar en marcha a estar parada: ahorramos coste
                new_state.profit += p.plant_activation_delta_cost[old_p]

        # 2. Poner en new_p si no es -1
        if new_p != -1:
            if new_state.plant_customer_count[new_p] == 0:
                # La central estaba parada y se pone en marcha
                new_state.profit -= p.plant_activation_delta_cost[new_p]
            new_state.plant_used_mw[new_p] += p.effective_demand[i][new_p]
            new_state.plant_customer_count[new_p] += 1

        # 3. Cambio en ingresos/penalizaciones del cliente
        if old_p == -1 and new_p != -1:
            new_state.profit += p.customer_service_gain[i]
        elif old_p != -1 and new_p == -1:
            new_state.profit -= p.customer_service_gain[i]

        new_state.assignment[i] = new_p

        return new_state

    def heuristic(self) -> float:
        """
        Heurística a MINIMIZAR (como exige el enunciado y el Lab 4).
        Equivale a -beneficio. Cuanto menor sea heuristic(), mayor es el beneficio.
        """
        return -self.profit

    def count_unserved_guaranteed(self) -> int:
        """Cuenta cuántos clientes garantizados están sin asignar (para verificar validez)."""
        return sum(
            1
            for i, p_idx in enumerate(self.assignment)
            if self.params.is_guaranteed[i] and p_idx == -1
        )

    def active_plants_by_type(self) -> List[int]:
        """Devuelve cuántas centrales de cada tipo (A, B, C) están en marcha."""
        counts = [0, 0, 0]
        for j, cnt in enumerate(self.plant_customer_count):
            if cnt > 0:
                counts[self.params.plants[j].plant_type] += 1
        return counts

    def __lt__(self, other: "StateRepresentation") -> bool:
        # AIMA define Node.__lt__ comparando los estados; HC y SA no lo usan, pero así un
        # Node con este estado se puede ordenar (p. ej. en una cola de prioridad) sin fallar.
        return self.assignment < other.assignment

    def __repr__(self) -> str:
        active = sum(1 for c in self.plant_customer_count if c > 0)
        served = sum(1 for a in self.assignment if a != -1)
        return (
            f"State(profit={self.profit:.2f} EUR, heuristic={self.heuristic():.2f}, "
            f"served={served}/{self.params.n_customers}, active_plants={active}/{self.params.n_plants})"
        )


# ==============================================================================
# ESTRATEGIAS DE GENERACIÓN DE LA SOLUCIÓN INICIAL (Apartado 4.5.3)
# ==============================================================================


def _guaranteed_by_demand(params: EnergyProblemParameters) -> List[int]:
    """Garantizados de mayor a menor demanda: colocar primero los grandes evita que al
    final no quepan en ninguna central."""
    guaranteed = [i for i in range(params.n_customers) if params.is_guaranteed[i]]
    guaranteed.sort(key=lambda i: params.customer_demand[i], reverse=True)
    return guaranteed


def _first_plant_that_fits(
    params: EnergyProblemParameters, i: int, candidates: List[int], used_mw: List[float]
) -> int:
    """Primera central de `candidates` con capacidad libre para el cliente `i`, o -1."""
    for j in candidates:
        if used_mw[j] + params.effective_demand[i][j] <= params.plant_capacity[j] + 1e-9:
            return j
    return -1


def generate_initial_state_random(
    params: EnergyProblemParameters,
    seed: int = 0,
) -> StateRepresentation:
    """
    Estrategia 1 (Aleatoria Válida):
    Asigna cada cliente GARANTIZADO (de mayor a menor demanda) a una central al azar con
    capacidad libre. Los no garantizados quedan sin servir: es una solución válida pero
    de baja calidad, para contrastar con el Greedy.
    """
    rng = Random(seed)
    assignment = [-1] * params.n_customers
    used_mw = [0.0] * params.n_plants

    plant_indices = list(range(params.n_plants))
    for i in _guaranteed_by_demand(params):
        rng.shuffle(plant_indices)
        j = _first_plant_that_fits(params, i, plant_indices, used_mw)
        if j == -1:
            raise ValueError("Instancia infactible: no se pudo asignar un cliente garantizado.")
        assignment[i] = j
        used_mw[j] += params.effective_demand[i][j]

    return StateRepresentation(params, assignment)


def generate_initial_state_greedy(
    params: EnergyProblemParameters,
) -> StateRepresentation:
    """
    Estrategia 2 (Voraz / Greedy Válida):
    1. Cada cliente GARANTIZADO (de mayor a menor demanda) va a la central más cercana
       (menor pérdida) que ya esté encendida y tenga hueco; si no hay ninguna, a la más
       cercana con hueco aunque haya que encenderla.
    2. Cada cliente NO GARANTIZADO (de mayor a menor ganancia) va a la central encendida
       más cercana con hueco; si no hay, se queda sin servir (no se encienden centrales
       solo para ellos).
    """
    assignment = [-1] * params.n_customers
    used_mw = [0.0] * params.n_plants
    cust_count = [0] * params.n_plants

    def active_by_distance(i: int) -> List[int]:
        return [j for j in params.plants_by_distance[i] if cust_count[j] > 0]

    def place(i: int, j: int) -> None:
        assignment[i] = j
        used_mw[j] += params.effective_demand[i][j]
        cust_count[j] += 1

    # Paso 1: garantizados
    for i in _guaranteed_by_demand(params):
        j = _first_plant_that_fits(params, i, active_by_distance(i), used_mw)
        if j == -1:
            j = _first_plant_that_fits(params, i, params.plants_by_distance[i], used_mw)
        if j == -1:
            raise ValueError("Instancia infactible: no se pudo asignar un cliente garantizado en Greedy.")
        place(i, j)

    # Paso 2: no garantizados, solo en centrales ya en marcha
    non_guaranteed = [i for i in range(params.n_customers) if not params.is_guaranteed[i]]
    non_guaranteed.sort(key=lambda i: params.customer_service_gain[i], reverse=True)
    for i in non_guaranteed:
        j = _first_plant_that_fits(params, i, active_by_distance(i), used_mw)
        if j != -1:
            place(i, j)

    return StateRepresentation(params, assignment)


def generate_initial_state_empty(
    params: EnergyProblemParameters,
) -> StateRepresentation:
    """
    Estrategia Vacía (Exclusiva para el Experimento 5):
    Ningún cliente está asignado inicialmente y todas las centrales están paradas.
    """
    return StateRepresentation(params, [-1] * params.n_customers)
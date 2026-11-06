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

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, StateRepresentation)
            and self.assignment == other.assignment
        )

    def __hash__(self) -> int:
        return hash(tuple(self.assignment))

    def __lt__(self, other: "StateRepresentation") -> bool:
        if not isinstance(other, StateRepresentation):
            return NotImplemented
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


def generate_initial_state_random(
    params: EnergyProblemParameters,
    seed: int = 0,
) -> StateRepresentation:
    """
    Estrategia 1 (Aleatoria Válida):
    Asigna primero todos los clientes GARANTIZADOS (ordenados de mayor a menor demanda
    para asegurar factibilidad si la instancia es ajustada) a una central elegida al azar
    que tenga capacidad disponible. Los clientes no garantizados quedan inicialmente sin
    asignar (o se asignan aleatoriamente si se desea; dejarlos sin asignar permite una
    solución inicial válida más rápida y de menor calidad para contrastar con Greedy).
    """
    rng = Random(seed)
    assignment = [-1] * params.n_customers
    used_mw = [0.0] * params.n_plants

    guaranteed_indices = [
        i for i in range(params.n_customers) if params.is_guaranteed[i]
    ]
    # Ordenar por demanda descendente evita bloqueos artificiales de empaquetado
    guaranteed_indices.sort(key=lambda i: params.customer_demand[i], reverse=True)

    plant_indices = list(range(params.n_plants))
    for i in guaranteed_indices:
        rng.shuffle(plant_indices)
        placed = False
        for j in plant_indices:
            eff_d = params.effective_demand[i][j]
            if used_mw[j] + eff_d <= params.plant_capacity[j] + 1e-9:
                assignment[i] = j
                used_mw[j] += eff_d
                placed = True
                break
        if not placed:
            raise ValueError(
                "Instancia infactible: no se pudo asignar un cliente garantizado."
            )

    return StateRepresentation(
        params=params,
        assignment=assignment,
    )


def generate_initial_state_greedy(
    params: EnergyProblemParameters,
) -> StateRepresentation:
    """
    Estrategia 2 (Voraz / Greedy Válida):
    1. Asigna primero todos los clientes GARANTIZADOS (de mayor a menor demanda)
       a la central con menor pérdida por distancia que ya esté encendida (o si ninguna
       encendida tiene hueco, a la central más eficiente y cercana).
    2. Después recorre los clientes NO GARANTIZADOS y los asigna solo si pueden entrar
       en una central que YA esté en marcha (sin encender nuevas centrales caras) o si
       su ingreso compensa encenderla.
    """
    assignment = [-1] * params.n_customers
    used_mw = [0.0] * params.n_plants
    cust_count = [0] * params.n_plants

    guaranteed_indices = [
        i for i in range(params.n_customers) if params.is_guaranteed[i]
    ]
    guaranteed_indices.sort(key=lambda i: params.customer_demand[i], reverse=True)

    for i in guaranteed_indices:
        placed = False
        # Priorizar centrales ya encendidas con menor pérdida
        for j in params.plants_by_distance[i]:
            if cust_count[j] > 0:
                eff_d = params.effective_demand[i][j]
                if used_mw[j] + eff_d <= params.plant_capacity[j] + 1e-9:
                    assignment[i] = j
                    used_mw[j] += eff_d
                    cust_count[j] += 1
                    placed = True
                    break
        # Si no cabe en ninguna encendida, abrir la central disponible con menor pérdida
        if not placed:
            for j in params.plants_by_distance[i]:
                eff_d = params.effective_demand[i][j]
                if used_mw[j] + eff_d <= params.plant_capacity[j] + 1e-9:
                    assignment[i] = j
                    used_mw[j] += eff_d
                    cust_count[j] += 1
                    placed = True
                    break
        if not placed:
            raise ValueError(
                "Instancia infactible: no se pudo asignar un cliente garantizado en Greedy."
            )

    # Paso 2: Asignar clientes NO garantizados a centrales que YA están en marcha
    non_guaranteed_indices = [
        i for i in range(params.n_customers) if not params.is_guaranteed[i]
    ]
    non_guaranteed_indices.sort(
        key=lambda i: params.customer_service_gain[i], reverse=True
    )

    for i in non_guaranteed_indices:
        for j in params.plants_by_distance[i]:
            if cust_count[j] > 0:
                eff_d = params.effective_demand[i][j]
                if used_mw[j] + eff_d <= params.plant_capacity[j] + 1e-9:
                    assignment[i] = j
                    used_mw[j] += eff_d
                    cust_count[j] += 1
                    break

    return StateRepresentation(
        params=params,
        assignment=assignment,
    )


def generate_initial_state_empty(
    params: EnergyProblemParameters,
) -> StateRepresentation:
    """
    Estrategia Vacía (Exclusiva para el Experimento 5):
    Ningún cliente está asignado inicialmente y todas las centrales están paradas.
    """
    assignment = [-1] * params.n_customers
    return StateRepresentation(
        params=params,
        assignment=assignment,
    )
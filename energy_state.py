"""
Representación del estado, constructores de solución inicial, generadores de acciones
y función heurística. Sigue el patrón de las Sesiones 2, 4 y 5 de laboratorio.
"""

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
        enable_move: bool = True,
        enable_unassign: bool = True,
        allow_unserved_guaranteed: bool = False,
    ):
        self.params = params
        self.assignment = assignment
        self.enable_move = enable_move
        self.enable_unassign = enable_unassign
        self.allow_unserved_guaranteed = allow_unserved_guaranteed

        if plant_used_mw is None or plant_customer_count is None or profit is None:
            self.plant_used_mw = [0.0] * params.n_plants
            self.plant_customer_count = [0] * params.n_plants
            for i, p_idx in enumerate(assignment):
                if p_idx != -1:
                    self.plant_used_mw[p_idx] += params.effective_demand[i][p_idx]
                    self.plant_customer_count[p_idx] += 1
            self.profit = self._compute_full_profit()
        else:
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
            enable_move=self.enable_move,
            enable_unassign=self.enable_unassign,
            allow_unserved_guaranteed=self.allow_unserved_guaranteed,
        )

    def generate_actions(self) -> Generator[EnergyOperator, None, None]:
        """
        Generador bajo demanda con `yield` para Hill Climbing (Sesión 2 y 4).
        Produce todas las acciones válidas desde el estado actual.
        """
        p = self.params
        assign = self.assignment
        used = self.plant_used_mw
        cap = p.plant_capacity
        eff = p.effective_demand
        is_guar = p.is_guaranteed
        n_plants = p.n_plants
        n_cust = p.n_customers

        # 1. Operador de Asignar / Mover a otra central / Desasignar
        if self.enable_move:
            for i in range(n_cust):
                curr_p = assign[i]
                eff_i = eff[i]
                # Mover o asignar a cualquier central con capacidad disponible suficiente
                for j in range(n_plants):
                    if j != curr_p and used[j] + eff_i[j] <= cap[j] + 1e-9:
                        yield AssignOrMoveCustomer(i, curr_p, j)

                # Desasignar cliente si está asignado y la restricción lo permite
                if self.enable_unassign and curr_p != -1:
                    if self.allow_unserved_guaranteed or not is_guar[i]:
                        yield AssignOrMoveCustomer(i, curr_p, -1)

    def generate_one_action(
        self, rng: Optional[Random] = None
    ) -> Generator[EnergyOperator, None, None]:
        """
        Generador de UN ÚNICO sucesor aleatorio para Simulated Annealing (Sesión 5).
        Evita instanciar todos los estados vecinos en cada paso de SA.
        """
        import random as py_random

        r = rng if rng is not None else py_random
        p = self.params
        assign = self.assignment
        used = self.plant_used_mw
        cap = p.plant_capacity
        eff = p.effective_demand
        is_guar = p.is_guaranteed
        n_plants = p.n_plants
        n_cust = p.n_customers

        # Intentamos muestrear directamente un movimiento válido al azar (O(1) promedio)
        for _ in range(60):
            i = r.randrange(n_cust)
            curr_p = assign[i]
            can_unassign = self.enable_unassign and (
                curr_p != -1 and (self.allow_unserved_guaranteed or not is_guar[i])
            )
            # Elegir destino entre las centrales (0..n_plants-1) o -1 si se puede desasignar
            if can_unassign and r.random() < (1.0 / (n_plants + 1)):
                yield AssignOrMoveCustomer(i, curr_p, -1)
                return
            else:
                j = r.randrange(n_plants)
                if j != curr_p and used[j] + eff[i][j] <= cap[j] + 1e-9:
                    yield AssignOrMoveCustomer(i, curr_p, j)
                    return

        # Respaldo: si tras los intentos rápidos no salió uno válido, tomamos de la lista
        valid_actions = list(self.generate_actions())
        if valid_actions:
            yield r.choice(valid_actions)

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
    enable_move: bool = True,
    enable_unassign: bool = True,
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
        enable_move=enable_move,
        enable_unassign=enable_unassign,
        allow_unserved_guaranteed=False,
    )


def generate_initial_state_greedy(
    params: EnergyProblemParameters,
    enable_move: bool = True,
    enable_unassign: bool = True,
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
        enable_move=enable_move,
        enable_unassign=enable_unassign,
        allow_unserved_guaranteed=False,
    )


def generate_initial_state_empty(
    params: EnergyProblemParameters,
    enable_move: bool = True,
    enable_unassign: bool = True,
) -> StateRepresentation:
    """
    Estrategia Vacía (Exclusiva para el Experimento 5):
    Ningún cliente está asignado inicialmente y todas las centrales están paradas.
    """
    assignment = [-1] * params.n_customers
    return StateRepresentation(
        params=params,
        assignment=assignment,
        enable_move=enable_move,
        enable_unassign=enable_unassign,
        allow_unserved_guaranteed=True,
    )
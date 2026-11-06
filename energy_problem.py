"""
Integración del problema de asignación de energía con la clase Problem de AIMA.
Sigue el patrón exacto de las Sesiones 4 y 5 de laboratorio.
"""

from typing import Generator
from aima.search import Problem
from energy_operators import EnergyOperator
from energy_state import StateRepresentation


class EnergyProblem(Problem):
    def __init__(
        self, initial_state: StateRepresentation, use_one_action: bool = False
    ):
        super().__init__(initial_state)
        # En la Sesión 5 se introduce `use_one_action`:
        # False -> genera todos los sucesores (para Hill Climbing)
        # True  -> genera un único sucesor aleatorio (para Simulated Annealing)
        self.use_one_action = use_one_action

    def actions(
        self, state: StateRepresentation
    ) -> Generator[EnergyOperator, None, None]:
        if self.use_one_action:
            return state.generate_one_action()
        return state.generate_actions()

    def result(
        self, state: StateRepresentation, action: EnergyOperator
    ) -> StateRepresentation:
        return state.apply_action(action)

    def value(self, state: StateRepresentation) -> float:
        # AIMA maximiza `value`, y `state.heuristic()` devuelve -profit (a minimizar).
        return -state.heuristic()

    def goal_test(self, state: StateRepresentation) -> bool:
        # En búsqueda local no existe estado final conocido a priori (Sesión 4).
        return False
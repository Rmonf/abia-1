"""
Operadores de búsqueda local para el problema de asignación de energía.
Sigue el patrón de bin_packing_operators.py de la Sesión 4 de laboratorio.
"""


class EnergyOperator(object):
    pass


class AssignOrMoveCustomer(EnergyOperator):
    """
    Mueve al cliente `c_i` desde su asignación actual (`old_p`, que puede ser -1 si no estaba
    asignado) hacia `new_p` (que puede ser una central 0..M-1, o -1 para desasignarlo).
    """

    def __init__(self, c_i: int, old_p: int, new_p: int):
        self.c_i = c_i
        self.old_p = old_p
        self.new_p = new_p

    def __repr__(self) -> str:
        return f"AssignOrMoveCustomer(customer={self.c_i}, from={self.old_p}, to={self.new_p})"


# No hay operador de intercambio (swap) entre dos clientes asignados: con esta heurística
# nunca cambia el beneficio (ambos siguen servidos y ambas centrales siguen en marcha), así
# que Hill Climbing jamás lo acepta y solo multiplicaría el factor de ramificación.

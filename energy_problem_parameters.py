"""
Parámetros constantes de una instancia del problema de asignación de energía.
Sigue el patrón ProblemParameters de la Sesión 4 de laboratorio.
"""

from math import hypot
from typing import List
from customer import Customer, GUARANTEED
from power_plant import PowerPlant
from energy import (
    get_guaranteed_tariff,
    get_non_guaranteed_tariff,
    get_non_service_penalty,
    get_production_cost_per_mw,
    get_running_cost,
    get_stopped_cost,
    get_loss_fraction,
)


class EnergyProblemParameters(object):
    def __init__(
        self,
        plants: List[PowerPlant],
        customers: List[Customer],
        unserved_guaranteed_penalty_per_mw: float = 0.0,
    ):
        self.plants = plants
        self.customers = customers
        self.n_plants = len(plants)
        self.n_customers = len(customers)
        # Usado en el Experimento 5 (penalización por no servir a un garantizado)
        self.unserved_guaranteed_penalty_per_mw = unserved_guaranteed_penalty_per_mw

        # Propiedades rápidas de centrales
        self.plant_capacity = [p.production_mw for p in plants]
        self.plant_running_total_cost = [
            get_running_cost(p.plant_type)
            + get_production_cost_per_mw(p.plant_type) * p.production_mw
            for p in plants
        ]
        self.plant_stopped_cost = [get_stopped_cost(p.plant_type) for p in plants]
        # Coste neto de encender una central que estaba parada:
        # (Coste fijo marcha + Coste prod total) - Coste parada
        self.plant_activation_delta_cost = [
            self.plant_running_total_cost[j] - self.plant_stopped_cost[j]
            for j in range(self.n_plants)
        ]

        # Propiedades rápidas de clientes
        self.is_guaranteed = [c.contract_type == GUARANTEED for c in customers]
        self.customer_demand = [c.demand_mw for c in customers]

        # Ingreso si se sirve al cliente vs coste/penalización si NO se sirve
        self.customer_served_revenue = []
        self.customer_unserved_penalty = []
        for c in customers:
            if c.contract_type == GUARANTEED:
                rev = c.demand_mw * get_guaranteed_tariff(c.customer_type)
                pen = c.demand_mw * self.unserved_guaranteed_penalty_per_mw
            else:
                rev = c.demand_mw * get_non_guaranteed_tariff(c.customer_type)
                pen = c.demand_mw * get_non_service_penalty(c.customer_type)
            self.customer_served_revenue.append(rev)
            self.customer_unserved_penalty.append(pen)

        # Ganancia neta al pasar un cliente de NO servido (-1) a servido en alguna central
        # (se ingresa la tarifa y se ahorra pagar la indemnización/penalización)
        self.customer_service_gain = [
            self.customer_served_revenue[i] + self.customer_unserved_penalty[i]
            for i in range(self.n_customers)
        ]

        # Matriz precalculada: effective_demand[i][j] = d_i / (1 - loss(i, j))
        self.effective_demand: List[List[float]] = []
        for i, c in enumerate(customers):
            row = []
            cx, cy, d = c.x, c.y, c.demand_mw
            for j, p in enumerate(plants):
                dist = hypot(cx - p.x, cy - p.y)
                loss = get_loss_fraction(dist)
                row.append(d / (1.0 - loss))
            self.effective_demand.append(row)

        # centrales ordenadas por menor pérdida (distancia) para cada cliente (útil en Greedy)
        self.plants_by_distance: List[List[int]] = [
            sorted(range(self.n_plants), key=lambda j: self.effective_demand[i][j])
            for i in range(self.n_customers)
        ]

    def set_guaranteed_penalty(self, penalty_per_mw: float) -> None:
        """Actualiza la penalización por MW para clientes garantizados no servidos (Exp. 5)."""
        self.unserved_guaranteed_penalty_per_mw = penalty_per_mw
        for i, c in enumerate(self.customers):
            if c.contract_type == GUARANTEED:
                self.customer_unserved_penalty[i] = c.demand_mw * penalty_per_mw
                self.customer_service_gain[i] = (
                    self.customer_served_revenue[i] + self.customer_unserved_penalty[i]
                )
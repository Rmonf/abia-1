"""
Script principal para ejecutar los 6 experimentos obligatorios de la práctica.
Ejecutar con: python run_experiments.py        (todos)
              python run_experiments.py N      (solo el experimento N, 1..6)
"""

import os
import random
import statistics
import sys
from timeit import default_timer as timer
from typing import List, Tuple

import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

# Los módulos del profesorado están en base/ y se importan por nombre (from customer import ...)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "base"))

from aima.search import hill_climbing, simulated_annealing, exp_schedule
from power_plants import generate_power_plants
from customers import generate_customers
from energy_problem_parameters import EnergyProblemParameters
from energy_state import (
    StateRepresentation,
    generate_initial_state_random,
    generate_initial_state_greedy,
    generate_initial_state_empty,
)
from energy_problem import EnergyProblem

# Escenario base del enunciado (Apartado 4.6.1)
BASE_PLANTS = (5, 10, 25)
BASE_CUSTOMERS = 1000
BASE_CUST_PROPS = (0.25, 0.30, 0.45)
BASE_GUARANTEED_PROP = 0.75
REPLICAS = 10
RANDOM_REPS = 5  # ejecuciones de la solución aleatoria por semilla en el Exp. 2
# Parámetros de SA si se lanzan los Exp. 5 o 6 sin el 3: la mejor terna obtenida en el Exp. 3
DEFAULT_SA = (5000.0, 0.0002, 40000)


def build_params(
    seed: int,
    plant_counts: Tuple[int, int, int] = BASE_PLANTS,
    n_customers: int = BASE_CUSTOMERS,
    **kwargs,
) -> EnergyProblemParameters:
    """Genera la instancia de una semilla. `kwargs` se pasan a EnergyProblemParameters."""
    plants = generate_power_plants(plant_counts, seed=seed)
    customers = generate_customers(
        n_customers, BASE_CUST_PROPS, BASE_GUARANTEED_PROP, seed=seed
    )
    return EnergyProblemParameters(plants, customers, **kwargs)


def get_feasible_seeds(
    n_needed: int = REPLICAS,
    plant_counts: Tuple[int, int, int] = BASE_PLANTS,
    n_customers: int = BASE_CUSTOMERS,
    random_reps: int = 0,
) -> List[int]:
    """
    Busca `n_needed` semillas cuyas instancias generadas aleatoriamente sean factibles
    según el greedy (que consiga colocar a todos los garantizados). Que el greedy falle
    no demuestra que la instancia sea infactible.
    Con `random_reps` > 0 se exige además que la solución aleatoria sea válida en esas
    réplicas (semillas candidate*100 + rep), como se usan en el Exp. 2.
    """
    seeds = []
    candidate = 1
    while len(seeds) < n_needed:
        params = build_params(candidate, plant_counts, n_customers)
        try:
            generate_initial_state_greedy(params)
            for rep in range(random_reps):
                generate_initial_state_random(params, seed=candidate * 100 + rep)
            seeds.append(candidate)
        except ValueError:
            pass
        candidate += 1
    return seeds


def run_hc(initial_state: StateRepresentation) -> Tuple[StateRepresentation, float]:
    """Ejecuta Hill Climbing midiendo el tiempo de cómputo."""
    problem = EnergyProblem(initial_state, use_one_action=False)
    t0 = timer()
    final_state = hill_climbing(problem)
    t1 = timer()
    return final_state, (t1 - t0)


def run_sa(
    initial_state: StateRepresentation, k: float, lam: float, limit: int
) -> Tuple[StateRepresentation, float]:
    """Ejecuta Simulated Annealing con generador unitario midiendo el tiempo."""
    problem = EnergyProblem(initial_state, use_one_action=True)
    sched = exp_schedule(k=k, lam=lam, limit=limit)
    t0 = timer()
    final_state = simulated_annealing(problem, schedule=sched)
    t1 = timer()
    return final_state, (t1 - t0)


# ==============================================================================
# EXPERIMENTO 1: Elección del conjunto de operadores
# ==============================================================================
def experiment_1(seeds: List[int]) -> None:
    print("\n=== EXPERIMENTO 1: Conjuntos de Operadores (Hill Climbing) ===")
    configs = [
        ("Solo Mover/Asignar", False),
        ("Mover + Desasignar", True),
    ]
    profits_by_cfg = {name: [] for name, _ in configs}
    times_by_cfg = {name: [] for name, _ in configs}

    for s in seeds:
        for name, unass in configs:
            params = build_params(s, enable_unassign=unass)
            random.seed(s)
            init_state = generate_initial_state_greedy(params)
            final_state, elapsed = run_hc(init_state)
            profits_by_cfg[name].append(final_state.profit)
            times_by_cfg[name].append(elapsed)

    for name, _ in configs:
        p_mean = statistics.mean(profits_by_cfg[name])
        p_std = statistics.stdev(profits_by_cfg[name])
        t_mean = statistics.mean(times_by_cfg[name])
        t_std = statistics.stdev(times_by_cfg[name])
        print(
            f"  {name:28s} -> Beneficio: {p_mean:10.2f} (±{p_std:7.2f}) EUR | "
            f"Tiempo: {t_mean:6.3f} (±{t_std:5.3f}) s"
        )

    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [profits_by_cfg[name] for name, _ in configs],
        tick_labels=[name for name, _ in configs],
    )
    plt.ylabel("Beneficio diario (EUR)")
    plt.title("Experimento 1: Beneficio según conjunto de operadores (HC)")
    plt.tight_layout()
    plt.savefig("exp1_operadores.png")
    plt.close()


# ==============================================================================
# EXPERIMENTO 2: Estrategia de generación de la solución inicial
# ==============================================================================
def experiment_2() -> None:
    print("\n=== EXPERIMENTO 2: Estrategias de Solución Inicial (Hill Climbing) ===")
    # La aleatoria falla en algunas semillas que el greedy acepta (p. ej. la 9), así que
    # se comparan ambas estrategias solo en semillas donde funcionan las dos.
    seeds = get_feasible_seeds(REPLICAS, random_reps=RANDOM_REPS)
    print(f"  Semillas (válidas para greedy y aleatoria): {seeds}")
    strategies = ["Aleatoria Válida", "Voraz (Greedy)"]
    init_profits = {k: [] for k in strategies}
    final_profits = {k: [] for k in strategies}
    times = {k: [] for k in strategies}

    for s in seeds:
        params = build_params(s)

        # 1. Aleatoria: RANDOM_REPS ejecuciones por semilla, porque depende del azar
        rand_init_p, rand_final_p, rand_t = [], [], []
        for rep in range(RANDOM_REPS):
            random.seed(s * 100 + rep)
            st_rand = generate_initial_state_random(params, seed=s * 100 + rep)
            rand_init_p.append(st_rand.profit)
            fin_rand, t_rand = run_hc(st_rand)
            rand_final_p.append(fin_rand.profit)
            rand_t.append(t_rand)

        init_profits["Aleatoria Válida"].append(statistics.mean(rand_init_p))
        final_profits["Aleatoria Válida"].append(statistics.mean(rand_final_p))
        times["Aleatoria Válida"].append(statistics.mean(rand_t))

        # 2. Greedy
        random.seed(s)
        st_greedy = generate_initial_state_greedy(params)
        init_profits["Voraz (Greedy)"].append(st_greedy.profit)
        fin_greedy, t_greedy = run_hc(st_greedy)
        final_profits["Voraz (Greedy)"].append(fin_greedy.profit)
        times["Voraz (Greedy)"].append(t_greedy)

    for k in strategies:
        print(
            f"  {k:18s} -> Inicial: {statistics.mean(init_profits[k]):10.2f} EUR | "
            f"Final: {statistics.mean(final_profits[k]):10.2f} (±{statistics.stdev(final_profits[k]):7.2f}) EUR | "
            f"Tiempo: {statistics.mean(times[k]):6.3f} (±{statistics.stdev(times[k]):5.3f}) s"
        )

    plt.figure(figsize=(7, 5))
    plt.boxplot(
        [final_profits[k] for k in strategies],
        tick_labels=strategies,
    )
    plt.ylabel("Beneficio final (EUR)")
    plt.title("Experimento 2: Influencia de la solución inicial (HC)")
    plt.tight_layout()
    plt.savefig("exp2_inicializacion.png")
    plt.close()


# ==============================================================================
# EXPERIMENTO 3: Ajuste de parámetros de Simulated Annealing
# ==============================================================================
def evaluate_sa(seeds: List[int], k: float, lam: float, limit: int) -> Tuple[float, float, float]:
    """SA desde el greedy en todas las semillas: (beneficio medio, desviación, tiempo medio)."""
    profits, elapsed_list = [], []
    for s in seeds:
        init_state = generate_initial_state_greedy(build_params(s))
        random.seed(s)
        fin_state, elapsed = run_sa(init_state, k=k, lam=lam, limit=limit)
        profits.append(fin_state.profit)
        elapsed_list.append(elapsed)
    return statistics.mean(profits), statistics.stdev(profits), statistics.mean(elapsed_list)


def experiment_3(seeds: List[int]) -> Tuple[float, float, int]:
    print("\n=== EXPERIMENTO 3: Ajuste de Simulated Annealing ===")
    k_values = [50, 500, 5000, 10000, 50000]
    lam_values = [0.01, 0.001, 0.0002, 0.0001]
    limit_values = [5000, 15000, 40000]

    # Fase 1: rejilla de (k, lam) con limit fijo
    limit = 15000
    best_mean_profit = float("-inf")
    for k in k_values:
        for lam in lam_values:
            mean_p, std_p, mean_t = evaluate_sa(seeds, k, lam, limit)
            print(
                f"  SA (k={k:5d}, lam={lam:<6g}, limit={limit:5d}) -> "
                f"Beneficio: {mean_p:10.2f} (±{std_p:8.2f}) EUR | Tiempo: {mean_t:5.3f} s"
            )
            if mean_p > best_mean_profit:
                best_mean_profit = mean_p
                best_k, best_lam = k, lam

    # Fase 2: con la mejor pareja (k, lam), variar el número de iteraciones
    print(f"  -- Mejor pareja: k={best_k}, lam={best_lam}. Variando limit:")
    best_mean_profit = float("-inf")
    for limit in limit_values:
        mean_p, std_p, mean_t = evaluate_sa(seeds, best_k, best_lam, limit)
        print(
            f"  SA (k={best_k:5d}, lam={best_lam:<6g}, limit={limit:5d}) -> "
            f"Beneficio: {mean_p:10.2f} (±{std_p:8.2f}) EUR | Tiempo: {mean_t:5.3f} s"
        )
        if mean_p > best_mean_profit:
            best_mean_profit = mean_p
            best_combo = (best_k, best_lam, limit)

    print(f"  => Mejor configuración SA seleccionada: k={best_combo[0]}, lam={best_combo[1]}, limit={best_combo[2]}")
    return best_combo


# ==============================================================================
# EXPERIMENTO 4: Escalabilidad (Variando Clientes y Variando Centrales)
# ==============================================================================
def experiment_4() -> None:
    print("\n=== EXPERIMENTO 4: Escalabilidad del Tiempo de Ejecución (HC) ===")
    # 4A: 40 centrales fijas, clientes de 250 en 250
    customer_sizes = [250, 500, 750, 1000, 1250]
    mean_times_cust = []
    for n_cust in customer_sizes:
        seeds = get_feasible_seeds(REPLICAS, BASE_PLANTS, n_cust)
        t_list = []
        for s in seeds:
            params = build_params(s, n_customers=n_cust)
            init_state = generate_initial_state_greedy(params)
            random.seed(s)
            _, elapsed = run_hc(init_state)
            t_list.append(elapsed)
        m_t = statistics.mean(t_list)
        s_t = statistics.stdev(t_list)
        mean_times_cust.append(m_t)
        print(f"  [40 centrales] Clientes={n_cust:4d} -> Tiempo medio: {m_t:6.3f} (±{s_t:5.3f}) s")

    # 4B: 1000 clientes fijos, centrales de 40 en 40 manteniendo proporción (5, 10, 25)
    plant_multipliers = [1, 2, 3, 4]
    mean_times_plants = []
    for mult in plant_multipliers:
        p_counts = (5 * mult, 10 * mult, 25 * mult)
        seeds = get_feasible_seeds(REPLICAS, p_counts, BASE_CUSTOMERS)
        t_list = []
        for s in seeds:
            params = build_params(s, p_counts)
            init_state = generate_initial_state_greedy(params)
            random.seed(s)
            _, elapsed = run_hc(init_state)
            t_list.append(elapsed)
        m_t = statistics.mean(t_list)
        s_t = statistics.stdev(t_list)
        mean_times_plants.append(m_t)
        print(f"  [1000 clientes] Centrales={40*mult:3d} -> Tiempo medio: {m_t:6.3f} (±{s_t:5.3f}) s")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.plot(customer_sizes, mean_times_cust, marker="o")
    ax1.set_xlabel("Número de clientes (40 centrales)")
    ax1.set_ylabel("Tiempo medio (s)")
    ax1.set_title("Escalabilidad por nº de clientes")

    ax2.plot([40 * m for m in plant_multipliers], mean_times_plants, marker="s", color="orange")
    ax2.set_xlabel("Número de centrales (1000 clientes)")
    ax2.set_ylabel("Tiempo medio (s)")
    ax2.set_title("Escalabilidad por nº de centrales")

    plt.tight_layout()
    plt.savefig("exp4_escalabilidad.png")
    plt.close()


# ==============================================================================
# EXPERIMENTO 5: Penalización en la heurística partiendo de solución vacía
# ==============================================================================
def guaranteed_penalty_threshold(params: EnergyProblemParameters) -> float:
    """
    Penalización P (EUR/MW) a partir de la cual servir al garantizado de menor demanda
    compensa encender la central más cara: d_min * (tarifa + P) > max coste de activación.
    """
    guaranteed = [i for i in range(params.n_customers) if params.is_guaranteed[i]]
    i_min = min(guaranteed, key=lambda i: params.customer_demand[i])
    d_min = params.customer_demand[i_min]
    tariff = params.customer_served_revenue[i_min] / d_min
    return max(params.plant_activation_delta_cost) / d_min - tariff


def experiment_5(seeds: List[int], sa_params: Tuple[float, float, int]) -> None:
    print("\n=== EXPERIMENTO 5: Solución Inicial Vacía y Penalización Garantizados ===")
    penalties = [100.0, 500.0, 1000.0, 5000.0, 20000.0, 40000.0, 50000.0, 100000.0]
    k, lam, limit = sa_params

    thresholds = [guaranteed_penalty_threshold(build_params(s)) for s in seeds]
    print(
        f"  Umbral teórico de penalización: {min(thresholds):.0f} - {max(thresholds):.0f} EUR/MW "
        f"(máximo entre semillas: {max(thresholds):.0f})"
    )

    for pen in penalties:
        hc_unserved, sa_unserved = [], []
        hc_valid_runs, sa_valid_runs = 0, 0
        for s in seeds:
            params = build_params(
                s, unserved_guaranteed_penalty_per_mw=pen, allow_unserved_guaranteed=True
            )

            # Hill Climbing desde estado vacío
            random.seed(s)
            empty_hc = generate_initial_state_empty(params)
            fin_hc, _ = run_hc(empty_hc)
            u_hc = fin_hc.count_unserved_guaranteed()
            hc_unserved.append(u_hc)
            if u_hc == 0:
                hc_valid_runs += 1

            # Simulated Annealing desde estado vacío
            random.seed(s)
            empty_sa = generate_initial_state_empty(params)
            fin_sa, _ = run_sa(empty_sa, k=k, lam=lam, limit=limit)
            u_sa = fin_sa.count_unserved_guaranteed()
            sa_unserved.append(u_sa)
            if u_sa == 0:
                sa_valid_runs += 1

        print(
            f"  Penalización={pen:7.1f} EUR/MW -> "
            f"HC: {hc_valid_runs}/{len(seeds)} válidas (media no servidos={statistics.mean(hc_unserved):.1f}) | "
            f"SA: {sa_valid_runs}/{len(seeds)} válidas (media no servidos={statistics.mean(sa_unserved):.1f})"
        )


# ==============================================================================
# EXPERIMENTO 6: Duplicar y triplicar las centrales de Tipo C
# ==============================================================================
def experiment_6(seeds: List[int], sa_params: Tuple[float, float, int]) -> None:
    print("\n=== EXPERIMENTO 6: Proporción de Centrales Tipo C (x1, x2, x3) ===")
    c_configs = [
        ("Base (5, 10, 25)", (5, 10, 25)),
        ("Doble C (5, 10, 50)", (5, 10, 50)),
        ("Triple C (5, 10, 75)", (5, 10, 75)),
    ]
    k, lam, limit = sa_params

    for label, counts in c_configs:
        hc_profits, hc_times, hc_active_ab, hc_active_c = [], [], [], []
        sa_profits, sa_times, sa_active_ab, sa_active_c = [], [], [], []

        for s in seeds:
            params = build_params(s, counts)

            # Hill Climbing
            random.seed(s)
            init_hc = generate_initial_state_greedy(params)
            fin_hc, t_hc = run_hc(init_hc)
            act_hc = fin_hc.active_plants_by_type()
            hc_profits.append(fin_hc.profit)
            hc_times.append(t_hc)
            hc_active_ab.append(act_hc[0] + act_hc[1])
            hc_active_c.append(act_hc[2])

            # Simulated Annealing
            random.seed(s)
            init_sa = generate_initial_state_greedy(params)
            fin_sa, t_sa = run_sa(init_sa, k=k, lam=lam, limit=limit)
            act_sa = fin_sa.active_plants_by_type()
            sa_profits.append(fin_sa.profit)
            sa_times.append(t_sa)
            sa_active_ab.append(act_sa[0] + act_sa[1])
            sa_active_c.append(act_sa[2])

        print(
            f"  {label:20s} [HC] -> Beneficio: {statistics.mean(hc_profits):10.2f} EUR | "
            f"Activas A+B: {statistics.mean(hc_active_ab):4.1f} | Activas C: {statistics.mean(hc_active_c):4.1f} | "
            f"Tiempo: {statistics.mean(hc_times):5.3f} s"
        )
        print(
            f"  {label:20s} [SA] -> Beneficio: {statistics.mean(sa_profits):10.2f} EUR | "
            f"Activas A+B: {statistics.mean(sa_active_ab):4.1f} | Activas C: {statistics.mean(sa_active_c):4.1f} | "
            f"Tiempo: {statistics.mean(sa_times):5.3f} s"
        )


if __name__ == "__main__":
    # Sin argumentos se lanzan todos; con un número, solo ese experimento
    selected = [int(sys.argv[1])] if len(sys.argv) > 1 else [1, 2, 3, 4, 5, 6]

    base_seeds = []
    if any(n not in (2, 4) for n in selected):
        print("Buscando 10 semillas factibles (según el greedy) para el escenario base...")
        base_seeds = get_feasible_seeds(REPLICAS, BASE_PLANTS, BASE_CUSTOMERS)
        print(f"Semillas seleccionadas: {base_seeds}")

    best_sa = DEFAULT_SA
    if 1 in selected:
        experiment_1(base_seeds)
    if 2 in selected:
        experiment_2()
    if 3 in selected:
        best_sa = experiment_3(base_seeds)
    if 4 in selected:
        experiment_4()
    if 5 in selected:
        experiment_5(base_seeds, best_sa)
    if 6 in selected:
        experiment_6(base_seeds, best_sa)
    print("\nExperimentos finalizados.")

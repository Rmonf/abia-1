import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_experiments import build_params
from energy_state import generate_initial_state_greedy, generate_initial_state_empty

def check(state, label, n=2000):
    worst = 0.0
    for _ in range(n):
        action = next(state.generate_one_action())
        state = state.apply_action(action)
        full = state._compute_full_profit()
        worst = max(worst, abs(state.profit - full))
        # también se comprueban MW usados y contadores
        used = [0.0] * state.params.n_plants; cnt = [0] * state.params.n_plants
        for i, j in enumerate(state.assignment):
            if j != -1:
                used[j] += state.params.effective_demand[i][j]; cnt[j] += 1
        assert cnt == state.plant_customer_count
        assert all(abs(a - b) < 1e-6 for a, b in zip(used, state.plant_used_mw))
        assert all(u <= c + 1e-9 for u, c in zip(state.plant_used_mw, state.params.plant_capacity))
        if not state.params.allow_unserved_guaranteed:
            assert state.count_unserved_guaranteed() == 0
    print(f"{label}: max |incremental - completo| = {worst:.2e}")
    assert worst < 1e-6

random.seed(123)
check(generate_initial_state_greedy(build_params(2)), "greedy semilla 2")
check(generate_initial_state_empty(build_params(5, unserved_guaranteed_penalty_per_mw=500.0, allow_unserved_guaranteed=True)), "vacío Exp.5 semilla 5")
print("OK")

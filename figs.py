"""
Figuras del informe para los Experimentos 3 y 5, a partir de los resultados
impresos por run_experiments.py (no vuelve a ejecutar los experimentos).
"""

import matplotlib.pyplot as plt

# Experimento 3, fase 1: beneficio medio (miles de EUR) con limit = 15000
k_values = [50, 500, 5000, 10000, 50000]
lam_values = [0.01, 0.001, 0.0002, 0.0001]
profits = [
    [821, 821, 821, 821],
    [821, 821, 821, 821],
    [846, 919, 934, 923],
    [886, 925, 927, 918],
    [906, 929, 909, 906],
]

plt.figure(figsize=(6, 4.5))
plt.imshow(profits, cmap="YlGn")
plt.colorbar(label="Beneficio medio (miles de EUR)")
plt.xticks(range(len(lam_values)), lam_values)
plt.yticks(range(len(k_values)), k_values)
plt.xlabel("λ")
plt.ylabel("k")
for i in range(len(k_values)):
    for j in range(len(lam_values)):
        plt.text(j, i, profits[i][j], ha="center", va="center", color="white" if profits[i][j] > 900 else "black")
plt.title("Experimento 3: beneficio medio de SA (limit = 15000)")
plt.tight_layout()
plt.savefig("exp3_rejilla_sa.png", dpi=200)
plt.close()

# Experimento 5: garantizados sin servir (media de 10 semillas) según la penalización
penalties = [100, 500, 1000, 5000, 20000, 40000, 50000, 100000]
hc_unserved = [734.8, 695.3, 642.0, 506.6, 199.6, 6.5, 8.6, 8.9]
sa_unserved = [243.4, 164.7, 87.0, 41.5, 41.8, 41.0, 41.0, 41.0]

plt.figure(figsize=(7, 4.5))
plt.plot(penalties, hc_unserved, marker="o", label="Hill Climbing")
plt.plot(penalties, sa_unserved, marker="s", label="Simulated Annealing")
plt.axvspan(34402, 41038, color="grey", alpha=0.3, label="Umbral teórico")
plt.xscale("log")
plt.xlabel("Penalización (EUR/MW, escala logarítmica)")
plt.ylabel("Garantizados sin servir (media)")
plt.title("Experimento 5: partiendo del estado vacío")
plt.legend()
plt.tight_layout()
plt.savefig("exp5_penalizacion.png", dpi=200)
plt.close()
"""Regenerates every figure. Each script stops loudly if its own checks fail.

Run from the repo root:  python -m validation.run_all
"""
from validation import (
    fig1_trotter,
    fig2_memory_wall,
    fig3_entropy,
    fig4_glauber,
    fig5_observable_error,
)

if __name__ == "__main__":
    for figure in (fig1_trotter, fig2_memory_wall, fig5_observable_error, fig4_glauber, fig3_entropy):
        print(f"--- {figure.__name__}")
        figure.main()

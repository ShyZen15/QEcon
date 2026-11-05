from core.engine import Plugin


class ChainEconomy(Plugin):
    name = "chain"

    def build_system(self):
        n = 6
        edges = {(i, i + 1): 1.0 for i in range(n - 1)}
        return n, edges, [0.1] * n, [0.5] * n

    def init_ones(self):
        return (0,)


times = [0.1 * k for k in range(1, 6)]
out = ChainEconomy().run(times)
print([float(x[0]) for x in out])
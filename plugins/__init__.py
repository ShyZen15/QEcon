"""Economics plugins. Each one turns a YAML spec into (n, edges, h, gamma) for
core.engine.compile_ising, via Snigdha's Plugin base class."""
from .banks import BanksPlugin
from .firms import FirmsPlugin
from .taxpayers import TaxpayersPlugin

REGISTRY = {
    "banks": BanksPlugin,
    "firms": FirmsPlugin,
    "taxpayers": TaxpayersPlugin,
}

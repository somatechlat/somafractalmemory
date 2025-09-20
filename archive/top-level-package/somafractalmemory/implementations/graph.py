import networkx as nx

from somafractalmemory.interfaces.graph import IGraphStore


class NetworkXGraphStore(IGraphStore):
    """NetworkX implementation of the graph store interface (archived copy)."""

    def __init__(self):
        self.graph = nx.DiGraph()

    # ... archived copy of methods; see src/ for active implementation

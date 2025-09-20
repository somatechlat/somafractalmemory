from enum import Enum
from typing import Any, Dict, Optional

from somafractalmemory.core import SomaFractalMemoryEnterprise


class MemoryMode(Enum):
    ON_DEMAND = "on_demand"
    LOCAL_AGENT = "local_agent"
    ENTERPRISE = "enterprise"


def create_memory_system(
    mode: MemoryMode, namespace: str, config: Optional[Dict[str, Any]] = None
) -> SomaFractalMemoryEnterprise:
    config = config or {}
    # Archive copy - see active factory under src/
    return SomaFractalMemoryEnterprise(namespace=namespace)

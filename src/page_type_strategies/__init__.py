"""Page-type strategy package.

Each module defines a concrete PageTypeStrategy for one page type.
The registry (page_type_registry.py) maps type IDs to strategy instances.
"""
from .base import PageTypeStrategy, BriefContext

__all__ = ["PageTypeStrategy", "BriefContext"]

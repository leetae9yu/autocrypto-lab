"""Small typed registries for declarative component lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class RegistryError(KeyError):
    """Raised when a declarative registry lookup or registration is invalid."""


@dataclass
class Registry(Generic[T]):
    name: str
    _items: dict[str, T] = field(default_factory=dict)

    def register(self, key: str, value: T) -> None:
        if not key:
            raise RegistryError("registry key is required")
        if key in self._items:
            raise RegistryError(f"duplicate {self.name} registry key: {key}")
        self._items[key] = value

    def get(self, key: str) -> T:
        try:
            return self._items[key]
        except KeyError as exc:
            raise RegistryError(f"unknown {self.name}: {key}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


FactorFn = Callable[..., object]
factor_registry: Registry[FactorFn] = Registry("factor")
model_registry: Registry[object] = Registry("model")

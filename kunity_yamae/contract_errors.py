from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContractError(Exception):
    field: str

    def __str__(self) -> str:
        return f"Missing or invalid contract field: {self.field}"

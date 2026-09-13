# food. thats it. an amber dot you can eat

from dataclasses import dataclass


@dataclass(slots=True)
class Food:
    id: int
    x: float
    y: float
    energy: float

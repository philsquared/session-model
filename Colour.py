from dataclasses import dataclass


@dataclass
class Colour:
    red: float
    green: float
    blue: float
    alpha: float  # 0.0 - 1.0

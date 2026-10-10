from dataclasses import dataclass


@dataclass
class Domanda:
    domanda: str
    A: str
    B: str
    C: str
    D: str
    corretta: str


DOMANDE = []

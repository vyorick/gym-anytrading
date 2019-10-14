from enum import Enum


class Positions(Enum):
    Short = 0
    Long = 1
    Out_of_market = 3

    def opposite(self):
        return Positions.Short if self == Positions.Long else Positions.Long
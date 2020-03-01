# -*- coding: utf-8 -*-
from enum import Enum


class Actions(Enum):
    Sell = 1
    Buy = 0


class Positions(Enum):
    Long = 0
    Short = 1


class StateElement:
    def __init__(self, old_position, action, new_position, penalty=None):
        self.old_position = old_position
        self.action = action
        self.new_position = new_position
        self.is_trade_start = old_position != new_position
        self.is_trade_end = old_position != new_position
        self.penalty = penalty

    def __str__(self):
        return f"old: {self.old_position}, action: {self.action}, new: {self.new_position}," \
               f" start: {self.is_trade_start}, end:{self.is_trade_end}, penalty after :{self.penalty} ticks"


class TradingFSM:
    def __init__(self, hold_penalty_ticks=None):
        self._states = [
            StateElement(Positions.Long, Actions.Buy, Positions.Long, hold_penalty_ticks),
            StateElement(Positions.Long, Actions.Sell, Positions.Short),
            StateElement(Positions.Short, Actions.Buy, Positions.Long),
            StateElement(Positions.Short, Actions.Sell, Positions.Short, hold_penalty_ticks),
        ]

    def get_state(self, old_position, action):
        for state in self._states:
            if old_position == state.old_position and action == state.action.value:
                return state
        raise Exception('State not found!')

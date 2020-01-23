# -*- coding: utf-8 -*-
from enum import Enum


class Actions(Enum):
    Sell = 2
    Buy = 1
    Nothing = 0


class Positions(Enum):
    Long = 1
    Short = 2
    Out = 0


class StateElement:
    def __init__(self, old_position, action, new_position, penalty_steps=None):
        self.old_position = old_position
        self.action = action
        self.new_position = new_position
        self.penalty_after_steps_count = penalty_steps
        self.is_trade_start = old_position == Positions.Out and new_position != Positions.Out
        self.is_trade_end = old_position != Positions.Out and new_position == Positions.Out

    def __str__(self):
        return f"old: {self.old_position}, action: {self.action}, new: {self.new_position}," \
               f" start: {self.is_trade_start}, end:{self.is_trade_end}, penalty after steps:{self.penalty_after_steps_count}"


class TradingFSM:
    def __init__(self):
        self._states = [StateElement(Positions.Out, Actions.Buy, Positions.Long),
                        StateElement(Positions.Out, Actions.Sell, Positions.Short),
                        StateElement(Positions.Out, Actions.Nothing, Positions.Out, 5),
                        StateElement(Positions.Long, Actions.Buy, Positions.Long),
                        StateElement(Positions.Long, Actions.Sell, Positions.Out),
                        StateElement(Positions.Long, Actions.Nothing, Positions.Long),
                        StateElement(Positions.Short, Actions.Buy, Positions.Out),
                        StateElement(Positions.Short, Actions.Sell, Positions.Short),
                        StateElement(Positions.Short, Actions.Nothing, Positions.Short)
                        ]

    def get_state(self, old_position, action):
        for state in self._states:
            if old_position == state.old_position and action == state.action.value:
                return state
        raise Exception('State not found!')

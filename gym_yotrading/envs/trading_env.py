import logging
from enum import Enum

import gym
import matplotlib.pyplot as plt
import numpy as np
from gym import spaces
from gym.utils import seeding

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
# Create handlers
c_handler = logging.StreamHandler()
# Create formatters and add it to handlers
c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
# Add handlers to the logger
logger.addHandler(c_handler)


class Actions(Enum):
    Sell = -1
    Buy = 1
    Nothing = 0


class Positions(Enum):
    Long = 1
    Short = -1
    Out = 0


class StateElement:
    def __init__(self, old_position, action, new_position):
        self.old_position = old_position
        self.action = action
        self.new_position = new_position
        self.is_trade_start = old_position == Positions.Out and new_position != Positions.Out
        self.is_trade_end = old_position != Positions.Out and new_position == Positions.Out

    def __str__(self):
        return f"old: {self.old_position}, action: {self.action}, new: {self.new_position}, start: {self.is_trade_start}, end:{self.is_trade_end}"


class TradingFSM:
    def __init__(self):
        self._states = [StateElement(Positions.Out, Actions.Buy, Positions.Long),
                        StateElement(Positions.Out, Actions.Sell, Positions.Short),
                        StateElement(Positions.Out, Actions.Nothing, Positions.Out),
                        StateElement(Positions.Long, Actions.Buy, Positions.Long),
                        StateElement(Positions.Long, Actions.Sell, Positions.Out),
                        StateElement(Positions.Long, Actions.Nothing, Positions.Long),
                        StateElement(Positions.Short, Actions.Buy, Positions.Out),
                        StateElement(Positions.Short, Actions.Sell, Positions.Short),
                        StateElement(Positions.Short, Actions.Nothing, Positions.Short)]

    def get_state(self, old_position, action):
        for state in self._states:
            if old_position == state.old_position and action == state.action.value:
                return state
        raise Exception('State not found!')


class TradingEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, df, window_size, max_loss=None):
        assert df.ndim == 2
        self.df = df
        self.window_size = window_size
        self.max_loss = max_loss
        self.prices, self.signal_features = self._process_data()
        self.shape = (window_size, self.signal_features.shape[1])
        self.fsm = TradingFSM()
        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=np.inf, high=np.inf, shape=self.shape, dtype=np.float32)

        # episode
        self._start_tick = self.window_size
        self._end_tick = len(self.prices) - 1
        self._position = Positions.Out
        self._done = None
        self._current_tick = None
        self._last_trade_tick = None
        self._action_history = None
        self._position_history = None
        self._total_reward = None
        self._total_profit = None
        self._first_rendering = None
        self.np_random = None
        self.trades_count = 0
        self.leverage = 1

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self):
        self._done = False
        self._current_tick = self._start_tick
        self._last_trade_tick = self._current_tick - 1
        self._position = Positions.Out
        self._action_history = ((self.window_size + 1) * [Actions.Nothing.value])
        self._position_history = {}
        self._total_reward = 0.
        self._total_profit = 1.  # unit
        self._first_rendering = True
        self.trades_count = 0
        return self._get_observation()

    def step(self, action):
        self._done = False
        self._current_tick += 1
        self._action_history.append(action)

        if self._current_tick == self._end_tick:
            self._done = True
        if self.max_loss is not None and self._total_reward < -self.max_loss:
            self._done = True
        state = self.fsm.get_state(self._position, action)
        logger.info(f"current tick {self._current_tick}, state {state}")
        # main works here
        step_reward = self._calculate_reward(state)
        self._total_reward += step_reward
        logger.info(f"step reward {step_reward}, total reward {self._total_reward}")
        # and here
        self._update_profit(state)
        self._position = state.new_position
        if state.old_position != state.new_position:
            self._position_history[self._current_tick] = self._position
            if state.is_trade_start:
                self._last_trade_tick = self._current_tick
                self.trades_count += 1
        observation = self._get_observation()
        info = dict(
            total_reward=self._total_reward,
            total_profit=self._total_profit,
            position=self._position
        )
        if self._done:
            info["position_history"] = self._position_history
            info["action_history"] = self._action_history
            info["trades_count"] = self.trades_count
        return observation, step_reward, self._done, info

    def _get_observation(self):
        return self.signal_features[(self._current_tick - self.window_size):self._current_tick]

    def render(self, mode='human'):

        def _plot_position(position, tick):
            if tick not in self._position_history:
                return
            color = None
            if position == Positions.Short:
                color = 'red'
            elif position == Positions.Long:
                color = 'green'
            elif position == Positions.Out:
                color = 'blue'
            if color:
                plt.scatter(tick, self.prices[tick], color=color)

        if self._first_rendering:
            self._first_rendering = False
            plt.cla()
            plt.plot(self.prices)
            start_position = self._action_history[self._start_tick]
            _plot_position(start_position, self._start_tick)

        _plot_position(self._position, self._current_tick)

        plt.suptitle(
            "Total Reward: %.6f" % self._total_reward + ' ~ ' +
            "Total Profit: %.6f" % self._total_profit
        )

        plt.pause(0.01)

    def render_all(self, mode='human'):
        window_ticks = np.arange(len(self.prices))
        plt.plot(self.prices)

        short_ticks = []
        long_ticks = []
        out_ticks = []
        for tick, position in self._position_history.items():
            if position == Positions.Long:
                long_ticks.append(tick)
            elif position == Positions.Short:
                short_ticks.append(tick)
            elif position == Positions.Out:
                out_ticks.append(tick)

        #        plt.plot(short_ticks, [1]*len(short_ticks), 'ro')
        # plt.xlabel(self._action_history)
        plt.plot(long_ticks, self.prices[long_ticks], 'go')
        plt.plot(short_ticks, self.prices[short_ticks], 'ro')
        plt.plot(out_ticks, self.prices[out_ticks], 'bo')

        plt.suptitle(
            "Total Reward: %.6f" % self._total_reward + ' ~ ' +
            "Total Profit: %.6f" % self._total_profit
        )

    def save_rendering(self, filepath):
        plt.savefig(filepath)

    def pause_rendering(self):
        plt.show()

    def _process_data(self):
        raise NotImplementedError

    def _calculate_reward(self, state):
        step_reward = 0  # pip
        if state.is_trade_end:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]
            price_diff = current_price - last_trade_price

            if state.old_position == Positions.Short:
                step_reward += -price_diff * self.leverage
            elif state.old_position == Positions.Long:
                step_reward += price_diff * self.leverage
            logger.debug(f"current_price {current_price}, last_trade_price {last_trade_price}, price_diff {price_diff} step_reward {step_reward}")

        return step_reward

    def _update_profit(self, state):
        raise NotImplementedError

    def max_possible_profit(self):  # trade fees are ignored
        raise NotImplementedError

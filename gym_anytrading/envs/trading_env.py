from enum import Enum

import gym
import matplotlib.pyplot as plt
import numpy as np
from gym import spaces
from gym.utils import seeding


class Actions(Enum):
    Sell = 2
    Buy = 1
    Nothing = 0


class Positions(Enum):
    Short = 0
    Long = 1
    Out_of_market = 3

    def opposite(self):
        return Positions.Short if self == Positions.Long else Positions.Long


class TradingEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, df, window_size):
        assert df.ndim == 2
        self.df = df
        self.window_size = window_size
        self.prices, self.signal_features = self._process_data()
        self.shape = (window_size, self.signal_features.shape[1])

        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=np.inf, high=np.inf, shape=self.shape, dtype=np.float32)

        # episode
        self._start_tick = self.window_size
        self._end_tick = len(self.prices) - 1
        self._position = Positions.Out_of_market
        self._done = None
        self._current_tick = None
        self._last_trade_tick = None
        self._action_history = None
        self._position_history = {}
        self._total_reward = None
        self._total_profit = None
        self._first_rendering = None
        self.np_random = None

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self):
        self._done = False
        self._current_tick = self._start_tick
        self._last_trade_tick = self._current_tick - 1
        self._position = Positions.Out_of_market
        self._action_history = ((self.window_size + 1) * [Actions.Nothing.value])
        self._position_history = {}
        self._total_reward = 0.
        self._total_profit = 1.  # unit
        self._first_rendering = True
        return self._get_observation()

    def step(self, action):
        self._done = False
        self._current_tick += 1
        self._action_history.append(action)

        if self._current_tick == self._end_tick:
            self._done = True
        # main works here
        step_reward = self._calculate_reward(action)
        self._total_reward += step_reward
        # and here
        self._update_profit(action)
        # TODO отдельно формировать массивы с actions и с position и рендерить оба
        if action == Actions.Buy.value:
            if self._position == Positions.Out_of_market:
                self._position = Positions.Long
                self._position_history[self._current_tick] = self._position
                self._last_trade_tick = self._current_tick
            if self._position == Positions.Short:
                self._position = Positions.Out_of_market
                self._last_trade_tick = self._current_tick
                self._position_history[self._current_tick] = self._position
            if self._position == Positions.Long:
                pass  # TODO something
        elif action == Actions.Sell.value:
            if self._position == Positions.Out_of_market:
                self._position = Positions.Short
                self._position_history[self._current_tick] = self._position
                self._last_trade_tick = self._current_tick
            if self._position == Positions.Long:
                self._position = Positions.Out_of_market
                self._last_trade_tick = self._current_tick
                self._position_history[self._current_tick] = self._position
            if self._position == Positions.Short:
                pass  # TODO something
        elif action == Actions.Nothing.value:
            pass
        else:
            raise Exception("Unknown action received!")

        observation = self._get_observation()
        info = dict(
            total_reward=self._total_reward,
            total_profit=self._total_profit,
            position=self._position.value
        )
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
            elif position == Positions.Out_of_market:
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
            elif position == Positions.Out_of_market:
                out_ticks.append(tick)

#        plt.plot(short_ticks, [1]*len(short_ticks), 'ro')
        plt.xlabel(self._action_history)
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

    def _calculate_reward(self, action):
        raise NotImplementedError

    def _update_profit(self, action):
        raise NotImplementedError

    def max_possible_profit(self):  # trade fees are ignored
        raise NotImplementedError

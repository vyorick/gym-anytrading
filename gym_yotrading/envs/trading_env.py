import logging

import gym
import matplotlib.pyplot as plt
import numpy as np
from gym import spaces
from gym.utils import seeding

# Create a custom logger
from .trading_policy import TradingFSM, Actions, Positions

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
# Create handlers
c_handler = logging.StreamHandler()
# Create formatters and add it to handlers
c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
# Add handlers to the logger
logger.addHandler(c_handler)


class TradingEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, df, window_size, max_loss=None, hold_penalty_ticks=None):
        assert df.ndim == 2
        self.df = df
        self.window_size = window_size
        self.max_loss = max_loss
        self.prices, self.signal_features = self._process_data()
        self.shape = (window_size+1, self.signal_features.shape[1])
        self.fsm = TradingFSM(hold_penalty_ticks)
        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=np.inf, high=np.inf, shape=self.shape, dtype=np.float32)

        # episode
        self._start_tick = self.window_size
        self._end_tick = len(self.prices) - 1
        self._position = Positions.Short
        self._done = None
        self._current_tick = None
        self._last_trade_tick = None
        self._action_history = None
        self._position_history = None
        self._total_reward = None
        self._current_deal_reward = None
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
        self._position = Positions.Short
        self._action_history = ((self.window_size + 1) * [Actions.Sell.value])
        self._position_history = {}
        self._total_reward = self._current_deal_reward = 0.
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
        step_reward = 0
        self._current_deal_reward = self._calculate_reward(state)
        if state.is_trade_end or self._done:
            step_reward = self._current_deal_reward
            self._total_reward += step_reward
        else:
            if state.penalty is not None and self._current_tick - self._last_trade_tick > state.penalty:
                step_reward = -1
        logger.info(f"step reward {step_reward}, total reward {self._total_reward}, current deal reward {self._current_deal_reward}")
        # and here
        # self._update_profit(state)
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
        # return self.signal_features[(self._current_tick - self.window_size):self._current_tick]
        additional_features = np.array([[self._position.value, self._current_deal_reward]])
        return np.concatenate((additional_features,
                               self.signal_features[(self._current_tick - self.window_size):self._current_tick]))

    def render(self, mode='human'):

        def _plot_position(position, tick):
            if tick not in self._position_history:
                return
            color = None
            if position == Positions.Short:
                color = 'red'
            elif position == Positions.Long:
                color = 'green'
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
            else:
                raise Exception("Unknown position - ", position)
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
        _step_reward = 0  # pip
        current_price = self.prices[self._current_tick]
        last_trade_price = self.prices[self._last_trade_tick]
        price_diff = current_price - last_trade_price

        if state.old_position == Positions.Short:
            _step_reward += -price_diff * self.leverage
        elif state.old_position == Positions.Long:
            _step_reward += price_diff * self.leverage
        logger.debug(f"current_price {current_price}, last_trade_price {last_trade_price}, price_diff {price_diff} step_reward {_step_reward}")

        return _step_reward

    def _update_profit(self, state):
        raise NotImplementedError

    def max_possible_profit(self):  # trade fees are ignored
        raise NotImplementedError

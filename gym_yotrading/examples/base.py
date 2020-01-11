import gym
import gym_yotrading
from gym_yotrading.envs import TradingEnv, ForexEnv, StocksEnv
from gym_yotrading.datasets import FOREX_EURUSD_1H_ASK, STOCKS_GOOGL
import matplotlib.pyplot as plt

env = gym.make('stocks-v1', frame_bound=(50, 500), window_size=10, max_loss=100)
# env = gym.make('stocks-v0', frame_bound=(50, 100), window_size=10)

observation = env.reset()
while True:
    action = env.action_space.sample()
    observation, reward, done, info = env.step(action)
    # env.render()
    if done:
        print("info:", info)
        break

plt.cla()
env.render_all()
plt.show()

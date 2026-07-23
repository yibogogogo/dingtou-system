import sys
sys.path.insert(0, '.')
from engine.backtest import BacktestEngine
import pandas as pd
import numpy as np

# 创建测试数据
dates = pd.date_range('2022-01-01', '2025-07-21', freq='B')
np.random.seed(42)

data_dict = {}
for key in ['kc50', 'zxhl', 'hldb']:
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, len(dates))))
    data_dict[key] = pd.DataFrame({'date': dates, 'close': prices})

# 定义评分函数
def score_func(row):
    return {'total': 60}

# 定义分配函数
def allocation_func(scores):
    from engine.allocation import AllocationEngine
    engine = AllocationEngine()
    return engine.allocate(scores)

# 运行回测
bt = BacktestEngine(initial_capital=0, monthly_invest=2000, dividend_yield_annual=0.04)
result = bt.run(data_dict, score_func, allocation_func)

print(f"Cumulative Invested: {result['cumulative_invested']}")
print(f"Final Value: {result['final_value']}")
print(f"Total Return: {result['total_return']}%")
print(f"Annual Return: {result['annual_return']}%")
print(f"Max Drawdown: {result['max_drawdown']}%")
print(f"Sharpe Ratio: {result['sharpe_ratio']}")
print(f"Win Rate: {result.get('win_rate', 0)}%")
print(f"Trades: {len(result['trades'])}")

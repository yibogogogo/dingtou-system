import sys
sys.path.insert(0, r'D:\红利\dingtou-system')
from engine.backtest import BacktestEngine
from engine.allocation import AllocationEngine
from engine.scoring import ScoringEngine
import pandas as pd
import numpy as np

# 生成2022-2026的模拟数据
dates = pd.date_range('2022-01-01', '2026-07-21', freq='B')
np.random.seed(42)

data_dict = {}
for key in ['kc50', 'zxhl', 'hldb']:
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.0003, 0.02, len(dates))))
    data_dict[key] = pd.DataFrame({'date': dates, 'close': prices})

def score_func(row):
    return 60

def allocation_func(scores):
    engine = AllocationEngine(base_amount=2000, min_score=45)
    return engine.allocate(scores)

bt = BacktestEngine(initial_capital=0, monthly_invest=2000)
result = bt.run(data_dict, score_func, allocation_func)

print('=== Fixed Backtest Results ===')
print(f'Cumulative Invested: {result["cumulative_invested"]:,.0f}')
print(f'Final Value: {result["final_value"]:,.2f}')
print(f'Total Return: {result["total_return"]:.2f}%')
print(f'Annual Return: {result["annual_return"]:.2f}%')
print(f'Max Drawdown: {result["max_drawdown"]:.2f}%')
print(f'Sharpe: {result["sharpe_ratio"]:.2f}')
print(f'Trades: {len(result["trades"])}')

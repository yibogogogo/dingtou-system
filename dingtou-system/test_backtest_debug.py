import sys
sys.path.insert(0, '.')
from engine.backtest import BacktestEngine
from engine.allocation import AllocationEngine
from engine.scoring import ScoringEngine
import pandas as pd
import numpy as np

# 创建测试数据 - 模拟2022-2025年A股市场的震荡下跌
dates = pd.date_range('2022-01-01', '2025-07-21', freq='B')
np.random.seed(42)

data_dict = {}
for key in ['kc50', 'zxhl', 'hldb']:
    # 模拟震荡下跌市场
    returns = np.random.normal(-0.0002, 0.015, len(dates))
    prices = 1000 * np.exp(np.cumsum(returns))
    data_dict[key] = pd.DataFrame({'date': dates, 'close': prices})

# 定义评分函数
def score_func(row):
    engine = ScoringEngine()
    try:
        result = engine.calculate_total_score(row)
        return result
    except:
        return {'total': 50}

# 定义分配函数
def allocation_func(scores):
    engine = AllocationEngine()
    return engine.allocate(scores)

# 运行回测
bt = BacktestEngine(initial_capital=0, monthly_invest=2000, dividend_yield_annual=0.04)
result = bt.run(data_dict, score_func, allocation_func)

# 打印关键指标
print('Cumulative Invested:', result['cumulative_invested'])
print('Final Value:', result['final_value'])
print('Total Return:', result['total_return'], '%')
print('Annual Return:', result['annual_return'], '%')
print('Max Drawdown:', result['max_drawdown'], '%')
print('Sharpe Ratio:', result['sharpe_ratio'])
print('Win Rate:', result.get('win_rate', 0), '%')
print('Trades:', len(result['trades']))
print('Dividends:', len(result['dividends']))

# 分析第一个月
print('\nFirst month data:')
for pv in result['portfolio_values'][:3]:
    print('Date:', pv['date'].strftime('%Y-%m-%d'), 'Value:', round(pv['value'], 2), 'Cash:', round(pv['cash'], 2), 'Invested:', pv['invested'])

# 分析价值vs投入
print('\nValue vs Invested analysis:')
for pv in result['portfolio_values'][:5]:
    diff = pv['value'] - pv['invested']
    print('Date:', pv['date'].strftime('%Y-%m-%d'), 'Value:', round(pv['value'], 2), 'Invested:', pv['invested'], 'Diff:', round(diff, 2))

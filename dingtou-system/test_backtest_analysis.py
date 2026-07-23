import sys
sys.path.insert(0, '.')
from engine.backtest import BacktestEngine
from engine.allocation import AllocationEngine
from engine.scoring import ScoringEngine
import pandas as pd
import numpy as np

# 创建测试数据 - 模拟2022-2025年A股市场的震荡下跌
# 使用与用户相同的参数
dates = pd.date_range('2022-01-01', '2025-07-21', freq='B')
np.random.seed(42)

data_dict = {}
for key in ['kc50', 'zxhl', 'hldb']:
    # 模拟震荡下跌市场 - 与用户场景一致
    returns = np.random.normal(-0.0002, 0.015, len(dates))  # 负收益，高波动
    prices = 1000 * np.exp(np.cumsum(returns))
    data_dict[key] = pd.DataFrame({'date': dates, 'close': prices})

# 定义评分函数 - 使用真实评分
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

# 运行回测 - 使用与用户相同的参数
bt = BacktestEngine(initial_capital=0, monthly_invest=2000, dividend_yield_annual=0.04)
result = bt.run(data_dict, score_func, allocation_func)

print("=== 回测结果分析 ===")
print(f"累计投入: {result['cumulative_invested']}")
print(f"最终价值: {result['final_value']}")
print(f"总收益: {result['total_return']}%")
print(f"年化收益: {result['annual_return']}%")
print(f"最大回撤: {result['max_drawdown']}%")
print(f"夏普比率: {result['sharpe_ratio']}")
print(f"胜率: {result.get('win_rate', 0)}%")
print(f"交易次数: {len(result['trades'])}")
print(f"分红次数: {len(result['dividends'])}")

# 分析第一个月的数据
print("\n=== 第一个月详细数据 ===")
first_month = result['portfolio_values'][:5]
for pv in first_month:
    print(f"日期: {pv['date'].strftime('%Y-%m-%d')}, 价值: {pv['value']:.2f}, 现金: {pv['cash']:.2f}, 投入: {pv['invested']}")

# 分析最后一个月的数据
print("\n=== 最后一个月详细数据 ===")
last_month = result['portfolio_values'][-5:]
for pv in last_month:
    print(f"日期: {pv['date'].strftime('%Y-%m-%d')}, 价值: {pv['value']:.2f}, 现金: {pv['cash']:.2f}, 投入: {pv['invested']}")

# 检查是否有月份价值低于投入
print("\n=== 价值分析 ===")
under_invested = [pv for pv in result['portfolio_values'] if pv['value'] < pv['invested']]
print(f"价值低于投入的月份数: {len(under_invested)} / {len(result['portfolio_values'])}")
if under_invested:
    print(f"最大亏损: {(min(pv['value'] - pv['invested'] for pv in under_invested)):.2f}")

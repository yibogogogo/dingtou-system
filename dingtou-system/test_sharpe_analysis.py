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

# 分析夏普比率计算
print("=== Sharpe Ratio Analysis ===")
portfolio_values = result['portfolio_values']

# 计算月度对数收益率
log_returns = []
for i in range(1, len(portfolio_values)):
    if portfolio_values[i-1]['value'] > 0 and portfolio_values[i]['value'] > 0:
        log_ret = np.log(portfolio_values[i]['value'] / portfolio_values[i-1]['value'])
        log_returns.append(log_ret)

print(f"Number of months: {len(log_returns)}")
print(f"Average monthly return: {np.mean(log_returns)*100:.4f}%")
print(f"Std monthly return: {np.std(log_returns, ddof=1)*100:.4f}%")
print(f"Risk-free monthly: {0.03/12*100:.4f}%")

# 手动计算夏普比率
avg_return = np.mean(log_returns)
std_return = np.std(log_returns, ddof=1)
risk_free_monthly = 0.03 / 12
sharpe = ((avg_return - risk_free_monthly) / std_return) * np.sqrt(12)

print(f"\nManual Sharpe calculation:")
print(f"Avg return: {avg_return*100:.4f}%")
print(f"Std return: {std_return*100:.4f}%")
print(f"Risk-free: {risk_free_monthly*100:.4f}%")
print(f"Sharpe = ({avg_return*100:.4f}% - {risk_free_monthly*100:.4f}%) / {std_return*100:.4f}% * sqrt(12)")
print(f"Sharpe = {sharpe:.2f}")

# 检查是否有负收益但夏普为正的情况
print(f"\nTotal return: {result['total_return']}%")
print(f"Sharpe ratio: {result['sharpe_ratio']}")

if result['total_return'] < 0 and result['sharpe_ratio'] > 0:
    print("\nWARNING: Negative return but positive Sharpe ratio!")
    print("This can happen if:")
    print("1. The return is slightly negative but volatility is very low")
    print("2. The risk-free rate is also negative (not in this case)")
    print("3. There's a calculation error")

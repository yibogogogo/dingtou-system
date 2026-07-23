import sys
sys.path.insert(0, '.')
from engine.backtest import BacktestEngine
from engine.allocation import AllocationEngine
from engine.scoring import ScoringEngine
import pandas as pd
import numpy as np

# 使用真实Excel数据
data_dict = {}
for key, file in [('kc50', '000688perf科创50.xlsx'), ('zxhl', '000922perf中证红利.xlsx'), ('hldb', 'H30269perf红利低波.xlsx')]:
    df = pd.read_excel(f'../{file}')
    columns = df.columns.tolist()
    
    # 转换日期格式
    df['date'] = pd.to_datetime(df[columns[0]].astype(str))
    df['close'] = df[columns[9]]
    
    data_dict[key] = df[['date', 'close']].copy()

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

print('=== Real Data Backtest Results ===')
print('Cumulative Invested:', result['cumulative_invested'])
print('Final Value:', result['final_value'])
print('Total Return:', result['total_return'], '%')
print('Annual Return:', result['annual_return'], '%')
print('Max Drawdown:', result['max_drawdown'], '%')
print('Sharpe Ratio:', result['sharpe_ratio'])
print('Win Rate:', result.get('win_rate', 0), '%')
print('Trades:', len(result['trades']))
print('Dividends:', len(result['dividends']))

# 基准对比
if result.get('benchmark'):
    print('\nBenchmark Total Return:', result['benchmark']['total_return'], '%')
    excess = result['total_return'] - result['benchmark']['total_return']
    print('Excess Return:', round(excess, 2), '%')

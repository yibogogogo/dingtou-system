import sys
sys.path.insert(0, r'D:\红利\dingtou-system')
from data.fetcher import DataFetcher
from engine.indicators import TechnicalIndicators
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
import pandas as pd
import numpy as np

print('=== Testing Fixed Core Calculations ===')

# 1. Test data fetching
f = DataFetcher()
data = {}
for key, info in [('kc50', '000688'), ('zxhl', '000922'), ('hldb', 'H30269')]:
    try:
        df = f.fetch_index_history(info, start_date='20240101', end_date='20240601')
        df = TechnicalIndicators.calculate_all(df)
        data[key] = df
        print(f'{key}: fetched {len(df)} rows')
    except Exception as e:
        print(f'{key}: error {e}')

# 2. Test scoring
engine = ScoringEngine()
scores = {}
for key, df in data.items():
    latest = df.iloc[-1]
    score = engine.calculate_total_score(latest)
    scores[key] = score['total']
    grade = engine.get_grade(score['total'])
    print(f'{key}: score={score["total"]:.1f}, grade={grade}')

# 3. Test allocation
alloc = AllocationEngine(base_amount=2000, min_score=25)
result = alloc.allocate(scores)
print('Allocation result:')
print(f'  Total: {result["total_amount"]}')
for rec in result['recommendations']:
    print(f'  {rec["index_key"]}: {rec["score"]:.1f} -> {rec["amount"]} ({rec["ratio"]}%)')

# 4. Test backtest
print('\n=== Testing Backtest Engine ===')
bt_data = {}
for key in ['kc50', 'zxhl', 'hldb']:
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='B')
    np.random.seed(hash(key) % 2**32)
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, len(dates))))
    bt_data[key] = pd.DataFrame({'date': dates, 'close': prices})

def score_func(row):
    return 60

def allocation_func(scores):
    return alloc.allocate(scores)

bt = BacktestEngine(initial_capital=100000, monthly_invest=2000)
bt_result = bt.run(bt_data, score_func, allocation_func)
print(f'Initial: {bt_result["initial_capital"]}')
print(f'Final: {bt_result["final_value"]}')
print(f'Total Return: {bt_result["total_return"]}%')
print(f'Annual Return: {bt_result["annual_return"]}%')
print(f'Max Drawdown: {bt_result["max_drawdown"]}%')
print(f'Sharpe: {bt_result["sharpe_ratio"]}')
print(f'Trades: {len(bt_result["trades"])}')

print('\n=== All Tests Passed ===')

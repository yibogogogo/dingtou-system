import sys
sys.path.insert(0, r'D:\红利\dingtou-system')
from data.fetcher import DataFetcher
from engine.indicators import TechnicalIndicators
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
import pandas as pd

f = DataFetcher()

# Fetch all three indices
data = {}
for key, info in [('kc50', '000688'), ('zxhl', '000922'), ('hldb', 'H30269')]:
    try:
        df = f.fetch_index_history(info, start_date='20240101', end_date='20240601')
        df = TechnicalIndicators.calculate_all(df)
        data[key] = df
        print(f'{key}: fetched {len(df)} rows')
    except Exception as e:
        print(f'{key}: error {e}')

engine = ScoringEngine()
scores = {}
for key, df in data.items():
    latest = df.iloc[-1]
    score = engine.calculate_total_score(latest)
    scores[key] = score['total']
    print(f'{key}: score={score["total"]}, grade={engine.get_grade(score["total"])}')

alloc = AllocationEngine(base_amount=2000, min_score=25)
result = alloc.allocate(scores)
print('Allocation result:')
print(result)

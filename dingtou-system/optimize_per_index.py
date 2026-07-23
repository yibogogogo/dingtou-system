"""
单指数参数优化脚本 (ETF版)
用法: python optimize_per_index.py <index_key>
示例: python optimize_per_index.py kc50
"""
import pandas as pd
import numpy as np
import sys
import os
import json
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
from engine.indicators import TechnicalIndicators
from config import INDICES

# ETF Sina代码映射
SINA_ETF = {"kc50": "sh588080", "a50": "sh563080", "zxhl": "sh515180", "hldb": "sh563020"}


def load_etf_data(index_key: str):
    """从新浪加载ETF全量历史数据"""
    sina_code = SINA_ETF[index_key]
    url = (f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           f"CN_MarketData.getKLineData?symbol={sina_code}&scale=240&ma=no&datalen=2000")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
    
    print(f"  正在获取 {sina_code} ...")
    r = requests.get(url, headers=headers, timeout=30)
    data = r.json()
    if not data or not isinstance(data, list):
        print(f"  ERROR: 无数据")
        return None
    
    records = []
    for item in data:
        records.append({
            "date": pd.to_datetime(item["day"]),
            "open": float(item["open"]), "high": float(item["high"]),
            "low": float(item["low"]), "close": float(item["close"]),
            "volume": float(item["volume"])
        })
    
    df = pd.DataFrame(records).sort_values("date")
    df['amount'] = df['close'] * df['volume']
    df = TechnicalIndicators.calculate_all(df)
    print(f"  获取 {len(df)} 条, {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
    return {index_key: df}
    return {index_key: df}


def run_single_backtest(data_dict, weights, min_score=45, monthly_invest=2000,
                        start_date=None, end_date=None):
    """运行单次回测"""
    def score_func(row):
        engine = ScoringEngine(weights=weights)
        try:
            return engine.calculate_total_score(row)
        except:
            return {'total': 50}

    def allocation_func(scores):
        engine = AllocationEngine(base_amount=monthly_invest, min_score=min_score)
        return engine.allocate(scores)

    bt = BacktestEngine(initial_capital=0, monthly_invest=monthly_invest)

    if start_date and end_date:
        result = bt.run(data_dict, score_func, allocation_func,
                         start_date=start_date.strftime('%Y%m%d'),
                         end_date=end_date.strftime('%Y%m%d'))
    else:
        result = bt.run(data_dict, score_func, allocation_func)

    return result


def optimize_index(index_key: str, data_dict: dict, n_iter: int = 50, n_splits: int = 3):
    """对单个指数运行随机搜索优化"""
    print(f"\n{'='*80}")
    print(f"优化指数: {index_key}")
    print(f"{'='*80}")

    data_key = list(data_dict.keys())[0]
    df = data_dict[data_key]
    start_date = df['date'].min()
    end_date = df['date'].max()
    total_days = (end_date - start_date).days
    fold_days = total_days // n_splits

    print(f"  数据范围: {start_date.date()} ~ {end_date.date()}")
    print(f"  数据点数: {len(df)}")
    print(f"  随机搜索次数: {n_iter}")
    print(f"  交叉验证折数: {n_splits}")

    # 基准测试 - 等权重
    baseline_weights = {
        'technical': 0.2, 'valuation': 0.2,
        'momentum': 0.2, 'sentiment': 0.2, 'fundflow': 0.2
    }
    baseline_result = run_single_backtest(
        data_dict, baseline_weights, min_score=40,
        start_date=start_date, end_date=end_date
    )

    # 参数范围
    param_ranges = {
        'technical_weight': (0.05, 0.45),
        'valuation_weight': (0.05, 0.45),
        'momentum_weight': (0.05, 0.35),
        'sentiment_weight': (0.05, 0.25),
        'fundflow_weight': (0.05, 0.20),
        'min_score': (30, 55)
    }

    results = []

    for i in range(n_iter):
        params = {}
        for pname, (pmin, pmax) in param_ranges.items():
            if pname == 'min_score':
                params[pname] = int(np.random.uniform(pmin, pmax))
            else:
                params[pname] = np.random.uniform(pmin, pmax)

        weights = {
            'technical': params['technical_weight'],
            'valuation': params['valuation_weight'],
            'momentum': params['momentum_weight'],
            'sentiment': params['sentiment_weight'],
            'fundflow': params['fundflow_weight'],
        }
        tw = sum(weights.values())
        weights = {k: v / tw for k, v in weights.items()}
        params['min_score'] = params.get('min_score', 40)

        fold_results = []
        for fold in range(n_splits):
            fs = start_date + timedelta(days=fold * fold_days)
            fe = fs + timedelta(days=fold_days)
            if fe > end_date:
                fe = end_date
            try:
                result = run_single_backtest(
                    data_dict, weights,
                    min_score=params['min_score'],
                    monthly_invest=2000,
                    start_date=fs, end_date=fe
                )
                fold_results.append(result)
            except Exception as e:
                continue

        if len(fold_results) < n_splits // 2:
            continue

        avg_annual_return = np.mean([r['annual_return'] for r in fold_results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in fold_results])
        avg_max_dd = np.mean([r['max_drawdown'] for r in fold_results])
        avg_total_return = np.mean([r['total_return'] for r in fold_results])

        score = (avg_sharpe * 0.4 +
                 (avg_annual_return / 100) * 0.3 -
                 (avg_max_dd / 100) * 0.2 +
                 (avg_total_return / 100) * 0.1)

        results.append({
            'params': params,
            'weights': weights,
            'avg_annual_return': round(avg_annual_return, 2),
            'avg_sharpe': round(avg_sharpe, 2),
            'avg_max_drawdown': round(avg_max_dd, 2),
            'avg_total_return': round(avg_total_return, 2),
            'score': round(score, 4),
        })

        if (i + 1) % 10 == 0:
            done = i + 1
            print(f"  进度: {done}/{n_iter} ({done/n_iter*100:.0f}%)")

    results.sort(key=lambda x: x['score'], reverse=True)

    return {
        'index_key': index_key,
        'data_dates': f"{start_date.date()} ~ {end_date.date()}",
        'data_points': len(df),
        'n_iterations': n_iter,
        'baseline': {
            'total_return': round(baseline_result['total_return'], 2),
            'annual_return': round(baseline_result['annual_return'], 2),
            'sharpe_ratio': round(baseline_result['sharpe_ratio'], 2),
            'max_drawdown': round(baseline_result['max_drawdown'], 2),
        },
        'top_10': results[:10],
    }


if __name__ == "__main__":
    valid = ["kc50", "a50", "zxhl", "hldb"]
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print(f"用法: python optimize_per_index.py <{('/').join(valid)}>")
        sys.exit(1)

    np.random.seed(42)

    index_key = sys.argv[1]

    print(f"正在从新浪加载 {index_key} ETF数据...")
    data_dict = load_etf_data(index_key)
    if data_dict is None:
        print("数据加载失败")
        sys.exit(1)

    result = optimize_index(index_key, data_dict, n_iter=80, n_splits=3)

    # 保存结果
    output_file = f'optimization_{index_key}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"优化完成: {index_key}")
    print(f"{'='*80}")
    print(f"\n基准表现（等权重）:")
    for k, v in result['baseline'].items():
        print(f"  {k}: {v}")
    print(f"\nTop 5 最优参数:")
    for i, r in enumerate(result['top_10'][:5]):
        print(f"\n  第{i+1}名 (综合评分={r['score']}):")
        print(f"    权重: tech={r['weights']['technical']:.3f}, val={r['weights']['valuation']:.3f}, "
              f"mom={r['weights']['momentum']:.3f}, sent={r['weights']['sentiment']:.3f}, "
              f"fund={r['weights']['fundflow']:.3f}")
        print(f"    min_score: {r['params']['min_score']}")
        print(f"    年化: {r['avg_annual_return']:.2f}%, 夏普: {r['avg_sharpe']:.2f}, "
              f"回撤: {r['avg_max_drawdown']:.2f}%, 总收益: {r['avg_total_return']:.2f}%")

    print(f"\n结果已保存至: {output_file}")

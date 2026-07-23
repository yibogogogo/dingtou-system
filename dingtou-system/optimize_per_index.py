"""
单指数参数优化脚本
用法: python optimize_per_index.py <index_key> <excel_file>
示例: python optimize_per_index.py kc50 ../000688perf科创50.xlsx
"""
import pandas as pd
import numpy as np
import sys
import os
import re
import json
import itertools
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
from engine.indicators import TechnicalIndicators


def load_single_index(index_key: str, excel_file: str):
    """加载单个指数的数据"""
    df = pd.read_excel(excel_file)
    columns = df.columns.tolist()

    if len(columns) < 13:
        print(f"ERROR: {excel_file} 格式异常，仅有{len(columns)}列")
        return None

    # 按文件名中的指数代码过滤
    code_match = re.match(r'([A-Z0-9]+)', os.path.basename(excel_file).split('perf')[0])
    if code_match:
        raw_code = code_match.group(1)
        correct_code = raw_code.lstrip('0') or '0'
        code_col = columns[1]
        df[code_col] = df[code_col].astype(str)
        before = len(df)
        df = df[df[code_col] == correct_code].copy()
        print(f"  代码过滤: {before} -> {len(df)} 行 ({correct_code})")

    df['date'] = pd.to_datetime(df[columns[0]].astype(str))
    df['close'] = df[columns[9]]
    df['open'] = df[columns[6]].fillna(df['close'])
    df['high'] = df[columns[7]].fillna(df['close'])
    df['low'] = df[columns[8]].fillna(df['close'])
    df['volume'] = df[columns[12]].fillna(0)
    df = TechnicalIndicators.calculate_all(df)

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
    if len(sys.argv) < 3:
        print("用法: python optimize_per_index.py <index_key> <excel_file>")
        print("示例: python optimize_per_index.py kc50 ../000688perf科创50.xlsx")
        sys.exit(1)

    np.random.seed(42)

    index_key = sys.argv[1]
    excel_file = sys.argv[2]

    print(f"正在加载 {index_key} 数据...")
    data_dict = load_single_index(index_key, excel_file)
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

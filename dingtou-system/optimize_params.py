import pandas as pd
import numpy as np
import sys
import os
import re
from datetime import datetime, timedelta
import itertools
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
from engine.indicators import TechnicalIndicators


def load_real_data():
    """加载真实Excel数据"""
    data_dict = {}
    
    for key, file in [('kc50', '../000688perf科创50.xlsx'), 
                       ('zxhl', '../000922perf中证红利.xlsx'), 
                       ('hldb', '../H30269perf红利低波.xlsx')]:
        df = pd.read_excel(file)
        columns = df.columns.tolist()
        
        if len(columns) < 13:
            print(f"ERROR: {file} 格式异常，仅有{len(columns)}列")
            continue
        
        # 按文件名中的指数代码过滤，处理前导零
        code_match = re.match(r'([A-Z0-9]+)', os.path.basename(file).split('perf')[0])
        if code_match:
            raw_code = code_match.group(1)
            correct_code = raw_code.lstrip('0') or '0'
            code_col = columns[1]
            df[code_col] = df[code_col].astype(str)
            before = len(df)
            df = df[df[code_col] == correct_code].copy()
            print(f"{file}: 过滤前{before}行→过滤后{len(df)}行")
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df[columns[0]].astype(str))
        df['close'] = df[columns[9]]
        df['open'] = df[columns[6]].fillna(df['close'])
        df['high'] = df[columns[7]].fillna(df['close'])
        df['low'] = df[columns[8]].fillna(df['close'])
        df['volume'] = df[columns[12]].fillna(0)
        
        # 计算技术指标
        df = TechnicalIndicators.calculate_all(df)
        
        data_dict[key] = df
        
    return data_dict


def analyze_data_distribution(data_dict):
    """分析数据分布特征"""
    print("=" * 80)
    print("真实数据统计摘要")
    print("=" * 80)
    
    for key, df in data_dict.items():
        # 计算日收益率
        df['daily_return'] = df['close'].pct_change()
        
        # 计算月度收益率
        df['year_month'] = df['date'].dt.to_period('M')
        monthly_returns = df.groupby('year_month')['close'].last().pct_change()
        
        # 计算年化收益率
        total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
        annual_return = ((df['close'].iloc[-1] / df['close'].iloc[0]) ** (365.25 / days) - 1) * 100
        
        # 计算波动率
        daily_vol = df['daily_return'].std() * np.sqrt(252) * 100
        monthly_vol = monthly_returns.std() * np.sqrt(12) * 100
        
        # 最大回撤
        cummax = df['close'].cummax()
        drawdown = (df['close'] - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        print(f"\n{key}:")
        print(f"  时间范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        print(f"  数据点数: {len(df)}")
        print(f"  总收益: {total_return:.2f}%")
        print(f"  年化收益: {annual_return:.2f}%")
        print(f"  日波动率: {daily_vol:.2f}%")
        print(f"  月波动率: {monthly_vol:.2f}%")
        print(f"  最大回撤: {max_drawdown:.2f}%")
        print(f"  夏普比率: {annual_return / daily_vol if daily_vol != 0 else 0:.2f}")


def run_single_backtest(data_dict, weights, min_score=45, monthly_invest=2000, 
                       start_date=None, end_date=None):
    """运行单次回测"""
    
    # 定义评分函数
    def score_func(row):
        engine = ScoringEngine(weights=weights)
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
    bt = BacktestEngine(initial_capital=0, monthly_invest=monthly_invest)
    
    if start_date and end_date:
        result = bt.run(data_dict, score_func, allocation_func, 
                         start_date=start_date.strftime('%Y%m%d'), 
                         end_date=end_date.strftime('%Y%m%d'))
    else:
        result = bt.run(data_dict, score_func, allocation_func)
    
    return result


def grid_search_optimization(data_dict, param_grid, n_splits=3):
    """
    网格搜索参数优化
    
    参数:
    - data_dict: 数据字典
    - param_grid: 参数网格
    - n_splits: 交叉验证折数
    """
    print("\n" + "=" * 80)
    print("开始网格搜索参数优化...")
    print("=" * 80)
    
    # 生成参数组合
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    
    results = []
    total_combinations = 1
    for values in param_values:
        total_combinations *= len(values)
    
    print(f"总参数组合数: {total_combinations}")
    
    # 数据时间范围
    start_date = data_dict['kc50']['date'].min()
    end_date = data_dict['kc50']['date'].max()
    total_days = (end_date - start_date).days
    
    # 计算每折的时间长度
    fold_days = total_days // n_splits
    
    for i, combo in enumerate(itertools.product(*param_values)):
        params = dict(zip(param_names, combo))
        
        # 构建权重字典
        weights = {
            'technical': params.get('technical_weight', 0.25),
            'valuation': params.get('valuation_weight', 0.25),
            'momentum': params.get('momentum_weight', 0.25),
            'sentiment': params.get('sentiment_weight', 0.15),
            'fundflow': params.get('fundflow_weight', 0.10),
        }
        
        # 归一化权重
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # 交叉验证
        fold_results = []
        for fold in range(n_splits):
            # 训练集和测试集划分
            train_start = start_date + timedelta(days=fold * fold_days)
            train_end = train_start + timedelta(days=fold_days)
            
            # 运行回测
            result = run_single_backtest(
                data_dict, weights, 
                min_score=params.get('min_score', 45),
                start_date=train_start, 
                end_date=train_end
            )
            
            fold_results.append(result)
        
        # 计算平均表现
        avg_annual_return = np.mean([r['annual_return'] for r in fold_results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in fold_results])
        avg_max_dd = np.mean([r['max_drawdown'] for r in fold_results])
        
        # 综合评分（夏普比率优先，兼顾收益和回撤）
        score = avg_sharpe * 0.5 + (avg_annual_return / 100) * 0.3 - (avg_max_dd / 100) * 0.2
        
        results.append({
            'params': params,
            'weights': weights,
            'avg_annual_return': avg_annual_return,
            'avg_sharpe': avg_sharpe,
            'avg_max_drawdown': avg_max_dd,
            'score': score
        })
        
        if (i + 1) % 10 == 0:
            print(f"已完成 {i + 1}/{total_combinations} 组参数测试...")
    
    # 按综合评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def random_search_optimization(data_dict, param_ranges, n_iter=50, n_splits=3):
    """
    随机搜索参数优化
    
    参数:
    - data_dict: 数据字典
    - param_ranges: 参数范围字典
    - n_iter: 迭代次数
    - n_splits: 交叉验证折数
    """
    print("\n" + "=" * 80)
    print("开始随机搜索参数优化...")
    print("=" * 80)
    
    results = []
    
    # 数据时间范围
    start_date = data_dict['kc50']['date'].min()
    end_date = data_dict['kc50']['date'].max()
    total_days = (end_date - start_date).days
    
    # 计算每折的时间长度
    fold_days = total_days // n_splits
    
    for i in range(n_iter):
        # 随机采样参数
        params = {}
        for param_name, (min_val, max_val) in param_ranges.items():
            if param_name == 'min_score':
                params[param_name] = int(np.random.uniform(min_val, max_val))
            else:
                params[param_name] = np.random.uniform(min_val, max_val)
        
        # 构建权重字典
        weights = {
            'technical': params.get('technical_weight', 0.25),
            'valuation': params.get('valuation_weight', 0.25),
            'momentum': params.get('momentum_weight', 0.25),
            'sentiment': params.get('sentiment_weight', 0.15),
            'fundflow': params.get('fundflow_weight', 0.10),
        }
        
        # 归一化权重
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # 交叉验证
        fold_results = []
        for fold in range(n_splits):
            # 训练集和测试集划分
            train_start = start_date + timedelta(days=fold * fold_days)
            train_end = train_start + timedelta(days=fold_days)
            
            # 运行回测
            result = run_single_backtest(
                data_dict, weights, 
                min_score=params.get('min_score', 45),
                start_date=train_start, 
                end_date=train_end
            )
            
            fold_results.append(result)
        
        # 计算平均表现
        avg_annual_return = np.mean([r['annual_return'] for r in fold_results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in fold_results])
        avg_max_dd = np.mean([r['max_drawdown'] for r in fold_results])
        
        # 综合评分
        score = avg_sharpe * 0.5 + (avg_annual_return / 100) * 0.3 - (avg_max_dd / 100) * 0.2
        
        results.append({
            'params': params,
            'weights': weights,
            'avg_annual_return': avg_annual_return,
            'avg_sharpe': avg_sharpe,
            'avg_max_drawdown': avg_max_dd,
            'score': score
        })
        
        if (i + 1) % 10 == 0:
            print(f"已完成 {i + 1}/{n_iter} 组参数测试...")
    
    # 按综合评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def rolling_window_validation(data_dict, best_params, window_years=2, step_months=3):
    """
    滚动窗口验证
    
    参数:
    - data_dict: 数据字典
    - best_params: 最优参数
    - window_years: 窗口年数
    - step_months: 步长月数
    """
    print("\n" + "=" * 80)
    print("开始滚动窗口验证...")
    print("=" * 80)
    
    start_date = data_dict['kc50']['date'].min()
    end_date = data_dict['kc50']['date'].max()
    
    # 构建权重
    weights = best_params['weights']
    
    results = []
    current_date = start_date
    
    while current_date + timedelta(days=365 * window_years) <= end_date:
        window_end = current_date + timedelta(days=365 * window_years)
        
        # 运行回测
        result = run_single_backtest(
            data_dict, weights,
            min_score=best_params['params'].get('min_score', 45),
            start_date=current_date,
            end_date=window_end
        )
        
        results.append({
            'window_start': current_date.strftime('%Y-%m-%d'),
            'window_end': window_end.strftime('%Y-%m-%d'),
            'annual_return': result['annual_return'],
            'sharpe_ratio': result['sharpe_ratio'],
            'max_drawdown': result['max_drawdown'],
            'total_return': result['total_return']
        })
        
        current_date += timedelta(days=30 * step_months)
    
    return results


def main():
    print("=" * 80)
    print("量化定投策略参数优化")
    print("=" * 80)
    
    # 加载真实数据
    print("\n加载真实数据...")
    data_dict = load_real_data()
    
    # 分析数据分布
    analyze_data_distribution(data_dict)
    
    # 参数优化
    print("\n" + "=" * 80)
    print("参数优化配置")
    print("=" * 80)
    
    # 随机搜索参数范围
    param_ranges = {
        'technical_weight': (0.1, 0.4),
        'valuation_weight': (0.1, 0.4),
        'momentum_weight': (0.1, 0.4),
        'sentiment_weight': (0.05, 0.25),
        'fundflow_weight': (0.05, 0.20),
        'min_score': (35, 55)
    }
    
    print("\n随机搜索参数范围:")
    for param, (min_val, max_val) in param_ranges.items():
        print(f"  {param}: [{min_val}, {max_val}]")
    
    # 执行随机搜索
    results = random_search_optimization(data_dict, param_ranges, n_iter=50, n_splits=3)
    
    # 显示前10名结果
    print("\n" + "=" * 80)
    print("Top 10 最优参数组合")
    print("=" * 80)
    
    for i, result in enumerate(results[:10]):
        print(f"\n第 {i + 1} 名:")
        print(f"  参数: {result['params']}")
        print(f"  权重: {result['weights']}")
        print(f"  平均年化收益: {result['avg_annual_return']:.2f}%")
        print(f"  平均夏普比率: {result['avg_sharpe']:.2f}")
        print(f"  平均最大回撤: {result['avg_max_drawdown']:.2f}%")
        print(f"  综合评分: {result['score']:.4f}")
    
    # 选择最优参数
    best_params = results[0]
    
    # 滚动窗口验证
    rolling_results = rolling_window_validation(data_dict, best_params, window_years=2, step_months=3)
    
    print("\n" + "=" * 80)
    print("滚动窗口验证结果")
    print("=" * 80)
    
    for result in rolling_results:
        print(f"\n窗口: {result['window_start']} ~ {result['window_end']}")
        print(f"  年化收益: {result['annual_return']:.2f}%")
        print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
        print(f"  最大回撤: {result['max_drawdown']:.2f}%")
        print(f"  总收益: {result['total_return']:.2f}%")
    
    # 保存最优参数
    output = {
        'best_params': best_params['params'],
        'best_weights': best_params['weights'],
        'optimization_results': results[:10],
        'rolling_validation': rolling_results
    }
    
    with open('optimization_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("优化结果已保存到 optimization_results.json")
    print("=" * 80)


if __name__ == "__main__":
    main()

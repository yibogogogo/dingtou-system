import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
from engine.indicators import TechnicalIndicators
from config import INDICES, INVESTMENT


def load_real_data():
    """加载真实Excel数据"""
    data_dict = {}
    
    for key, file in [('kc50', '../000688perf科创50.xlsx'), 
                       ('zxhl', '../000922perf中证红利.xlsx'), 
                       ('hldb', '../H30269perf红利低波.xlsx')]:
        df = pd.read_excel(file)
        columns = df.columns.tolist()
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df[columns[0]].astype(str))
        df['close'] = df[columns[9]]
        df['open'] = df[columns[6]]
        df['high'] = df[columns[7]]
        df['low'] = df[columns[8]]
        df['volume'] = df[columns[12]]
        
        # 计算技术指标
        df = TechnicalIndicators.calculate_all(df)
        
        data_dict[key] = df
        
    return data_dict


def run_backtest_with_current_config(data_dict):
    """使用当前配置运行回测"""
    print("=" * 80)
    print("使用优化后的参数运行回测")
    print("=" * 80)
    
    # 使用当前配置
    weights = INDICES['kc50']['weights']  # 使用统一的优化权重
    min_score = INVESTMENT['min_score']
    
    print(f"\n当前配置:")
    print(f"  权重: {weights}")
    print(f"  最低评分阈值: {min_score}")
    
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
    bt = BacktestEngine(initial_capital=0, monthly_invest=2000)
    result = bt.run(data_dict, score_func, allocation_func)
    
    print(f"\n回测结果:")
    print(f"  累计投入: {result['cumulative_invested']:,.0f}")
    print(f"  最终价值: {result['final_value']:,.2f}")
    print(f"  总收益: {result['total_return']:.2f}%")
    print(f"  年化收益: {result['annual_return']:.2f}%")
    print(f"  最大回撤: {result['max_drawdown']:.2f}%")
    print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"  胜率: {result.get('win_rate', 0):.1f}%")
    print(f"  交易次数: {len(result['trades'])}")
    print(f"  分红次数: {len(result['dividends'])}")
    
    return result


def compare_with_benchmark(data_dict):
    """与基准对比"""
    print("\n" + "=" * 80)
    print("与基准对比")
    print("=" * 80)
    
    # 简单等额定投基准
    bt = BacktestEngine(initial_capital=0, monthly_invest=2000)
    
    # 等额定投策略（每月平均分配）
    def equal_allocation(scores):
        recommendations = []
        for key in scores:
            recommendations.append({
                'index_key': key,
                'amount': 2000 / len(scores),
                'score': scores[key],
                'label': '基准'
            })
        return {
            'total_amount': 2000,
            'recommendations': recommendations
        }
    
    def dummy_score(row):
        return {'total': 50}
    
    benchmark_result = bt.run(data_dict, dummy_score, equal_allocation)
    
    print(f"\n基准策略（等额定投）:")
    print(f"  累计投入: {benchmark_result['cumulative_invested']:,.0f}")
    print(f"  最终价值: {benchmark_result['final_value']:,.2f}")
    print(f"  总收益: {benchmark_result['total_return']:.2f}%")
    print(f"  年化收益: {benchmark_result['annual_return']:.2f}%")
    print(f"  最大回撤: {benchmark_result['max_drawdown']:.2f}%")
    print(f"  夏普比率: {benchmark_result['sharpe_ratio']:.2f}")
    
    return benchmark_result


def main():
    print("=" * 80)
    print("优化参数验证")
    print("=" * 80)
    
    # 加载真实数据
    print("\n加载真实数据...")
    data_dict = load_real_data()
    
    # 使用当前配置运行回测
    result = run_backtest_with_current_config(data_dict)
    
    # 与基准对比
    benchmark = compare_with_benchmark(data_dict)
    
    # 计算超额收益
    excess_return = result['total_return'] - benchmark['total_return']
    excess_annual = result['annual_return'] - benchmark['annual_return']
    
    print(f"\n" + "=" * 80)
    print("超额收益分析")
    print("=" * 80)
    print(f"  超额总收益: {excess_return:.2f}%")
    print(f"  超额年化收益: {excess_annual:.2f}%")
    print(f"  夏普比率提升: {result['sharpe_ratio'] - benchmark['sharpe_ratio']:.2f}")
    
    # 保存结果
    output = {
        'optimized_result': {
            'cumulative_invested': result['cumulative_invested'],
            'final_value': result['final_value'],
            'total_return': result['total_return'],
            'annual_return': result['annual_return'],
            'max_drawdown': result['max_drawdown'],
            'sharpe_ratio': result['sharpe_ratio'],
            'win_rate': result.get('win_rate', 0),
            'trades_count': len(result['trades']),
            'dividends_count': len(result['dividends'])
        },
        'benchmark_result': {
            'cumulative_invested': benchmark['cumulative_invested'],
            'final_value': benchmark['final_value'],
            'total_return': benchmark['total_return'],
            'annual_return': benchmark['annual_return'],
            'max_drawdown': benchmark['max_drawdown'],
            'sharpe_ratio': benchmark['sharpe_ratio']
        },
        'excess_return': excess_return,
        'excess_annual': excess_annual,
        'sharpe_improvement': result['sharpe_ratio'] - benchmark['sharpe_ratio']
    }
    
    with open('validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n验证结果已保存到 validation_results.json")
    print("=" * 80)


if __name__ == "__main__":
    main()

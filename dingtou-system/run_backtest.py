"""
回测与参数优化主脚本
整合所有功能：数据获取、回测、参数优化、实盘模拟
"""
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, r'D:\红利\dingtou-system')

from engine.backtest_enhanced import EnhancedBacktestEngine
from engine.paper_trading import PaperTradingSimulator
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.indicators import TechnicalIndicators
from data.fetcher import DataFetcher


def run_backtest_with_real_data(
    start_date: str = "20230101",
    end_date: str = None,
    weights: Dict[str, float] = None,
    min_score: float = 45,
    use_enhanced: bool = True,
) -> Dict:
    """
    使用真实数据运行回测
    
    Returns:
        回测结果
    """
    print("=" * 60)
    print("真实数据回测")
    print("=" * 60)
    
    # 初始化引擎
    engine = EnhancedBacktestEngine(
        initial_capital=100000,
        monthly_invest=2000,
        fee_rate=0.0005,
    )
    
    # 获取真实数据
    print("\n获取数据: " + start_date + " 至 " + (end_date or "今天"))
    data_dict = engine.fetch_real_data(start_date=start_date, end_date=end_date)
    
    # 检查数据
    for key, df in data_dict.items():
        if df is None or df.empty:
            print("警告: " + key + " 数据为空")
        else:
            print("  " + key + ": " + str(len(df)) + " 条记录, " + str(df['date'].min()) + " 至 " + str(df['date'].max()))
    
    # 运行回测
    print("\n运行回测...")
    print("  权重: " + str(weights))
    print("  最低分: " + str(min_score))
    print("  增强评分: " + str(use_enhanced))
    
    result = engine.run_with_real_data(
        data_dict=data_dict,
        weights=weights,
        min_score=min_score,
        use_enhanced=use_enhanced,
        start_date=start_date,
        end_date=end_date,
    )
    
    # 打印结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print("初始资金: " + str(result['initial_capital']))
    print("最终价值: " + str(result['final_value']))
    print("总收益: " + str(round(result['total_return'], 2)) + "%")
    print("年化收益: " + str(round(result['annual_return'], 2)) + "%")
    print("最大回撤: " + str(round(result['max_drawdown'], 2)) + "%")
    print("夏普比率: " + str(round(result['sharpe_ratio'], 2)))
    print("总投入: " + str(result['total_invested']))
    print("总手续费: " + str(round(result['total_fees'], 2)))
    print("交易次数: " + str(result['trade_counts']))
    
    return result


def optimize_parameters(
    start_date: str = "20230101",
    end_date: str = None,
) -> pd.DataFrame:
    """
    参数优化
    
    测试不同权重和min_score组合，找到最优参数
    """
    print("=" * 60)
    print("参数优化")
    print("=" * 60)
    
    engine = EnhancedBacktestEngine()
    
    # 获取数据
    print("\n获取数据...")
    data_dict = engine.fetch_real_data(start_date=start_date, end_date=end_date)
    
    # 定义参数网格
    param_grid = {
        "min_score": [35, 40, 45, 50, 55],
        "technical_weight": [0.20, 0.25, 0.30],
        "valuation_weight": [0.15, 0.20, 0.25],
        "momentum_weight": [0.10, 0.15, 0.20],
        "sentiment_weight": [0.05, 0.10, 0.15],
        "fundflow_weight": [0.10, 0.15, 0.20],
    }
    
    print("\n参数网格: " + str(len(param_grid['min_score'])) + " x " + str(len(param_grid['technical_weight'])) + "^5 = " +
          str(len(param_grid['min_score']) * len(param_grid['technical_weight'])**5) + " 种组合")
    print("开始优化...")
    
    # 运行优化
    results = engine.optimize_parameters(
        data_dict=data_dict,
        param_grid=param_grid,
        start_date=start_date,
        end_date=end_date,
    )
    
    # 按夏普比率排序
    results_sorted = results.sort_values("sharpe_ratio", ascending=False)
    
    print("\n" + "=" * 60)
    print("Top 10 最优参数")
    print("=" * 60)
    print(results_sorted.head(10).to_string(index=False))
    
    # 保存结果
    results_sorted.to_csv("parameter_optimization.csv", index=False, encoding="utf-8-sig")
    print("\n结果已保存到 parameter_optimization.csv")
    
    return results_sorted


def run_paper_trading():
    """运行实盘模拟"""
    print("=" * 60)
    print("实盘模拟")
    print("=" * 60)
    
    simulator = PaperTradingSimulator()
    
    # 获取数据
    print("\n获取最近2年数据...")
    data_dict = simulator.backtest_engine.fetch_real_data(start_date="20240101")
    
    # 定义策略
    strategies = [
        {
            "name": "当前权重(增强)",
            "weights": {
                "technical": 0.25,
                "valuation": 0.20,
                "momentum": 0.15,
                "sentiment": 0.10,
                "fundflow": 0.15,
                "rotation": 0.15,
            },
            "min_score": 45,
            "use_enhanced": True,
        },
        {
            "name": "保守策略",
            "weights": {
                "technical": 0.20,
                "valuation": 0.30,
                "momentum": 0.10,
                "sentiment": 0.10,
                "fundflow": 0.20,
                "rotation": 0.10,
            },
            "min_score": 50,
            "use_enhanced": True,
        },
        {
            "name": "激进策略",
            "weights": {
                "technical": 0.30,
                "valuation": 0.15,
                "momentum": 0.20,
                "sentiment": 0.15,
                "fundflow": 0.10,
                "rotation": 0.10,
            },
            "min_score": 35,
            "use_enhanced": True,
        },
        {
            "name": "等权定投(基准)",
            "weights": {
                "technical": 0.20,
                "valuation": 0.20,
                "momentum": 0.20,
                "sentiment": 0.20,
                "fundflow": 0.20,
            },
            "min_score": 30,
            "use_enhanced": False,
        },
    ]
    
    # 对比
    comparison = simulator.compare_strategies(
        data_dict=data_dict,
        strategies=strategies,
        start_date="20240101",
    )
    
    print("\n" + "=" * 60)
    print("策略对比")
    print("=" * 60)
    print(comparison.to_string(index=False))
    
    # 保存
    comparison.to_csv("paper_trading_comparison.csv", index=False, encoding="utf-8-sig")
    print("\n结果已保存到 paper_trading_comparison.csv")
    
    return comparison


def run_full_pipeline():
    """运行完整流程"""
    print("\n" + "=" * 80)
    print("量化定投择时系统 - 完整回测与优化流程")
    print("=" * 80)
    
    # 1. 真实数据回测（最近2年）
    print("\n【步骤1】真实数据回测")
    result = run_backtest_with_real_data(
        start_date="20240101",
        weights={
            "technical": 0.25,
            "valuation": 0.20,
            "momentum": 0.15,
            "sentiment": 0.10,
            "fundflow": 0.15,
            "rotation": 0.15,
        },
        min_score=45,
        use_enhanced=True,
    )
    
    # 2. 参数优化（可选，耗时较长）
    print("\n【步骤2】参数优化")
    print("注意: 参数优化可能需要较长时间，跳过请输入 'skip'")
    user_input = input("是否运行参数优化? (yes/skip): ").strip().lower()
    
    if user_input != "skip":
        optimize_results = optimize_parameters(start_date="20240101")
        
        # 使用最优参数再次回测
        best = optimize_results.iloc[0]
        print("\n使用最优参数重新回测...")
        
        best_weights = {
            "technical": best["technical_weight"],
            "valuation": best["valuation_weight"],
            "momentum": best["momentum_weight"],
            "sentiment": best["sentiment_weight"],
            "fundflow": best["fundflow_weight"],
        }
        
        run_backtest_with_real_data(
            start_date="20240101",
            weights=best_weights,
            min_score=best["min_score"],
            use_enhanced=True,
        )
    
    # 3. 实盘模拟
    print("\n【步骤3】实盘模拟 - 策略对比")
    comparison = run_paper_trading()
    
    print("\n" + "=" * 80)
    print("流程完成!")
    print("=" * 80)
    print("\n生成的文件:")
    print("  - paper_trading_comparison.csv (策略对比)")
    if user_input != "skip":
        print("  - parameter_optimization.csv (参数优化结果)")
    print("\n建议:")
    print("  1. 查看策略对比结果，选择最适合的策略")
    print("  2. 根据参数优化结果微调权重")
    print("  3. 在app.py中使用优化后的参数")


if __name__ == "__main__":
    # 默认运行完整流程
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 快速模式：只运行回测
        run_backtest_with_real_data(
            start_date="20240101",
            weights={
                "technical": 0.25,
                "valuation": 0.20,
                "momentum": 0.15,
                "sentiment": 0.10,
                "fundflow": 0.15,
                "rotation": 0.15,
            },
            min_score=45,
            use_enhanced=True,
        )
    else:
        run_full_pipeline()

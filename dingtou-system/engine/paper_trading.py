"""
实盘模拟器
使用最近1-2年数据进行模拟交易验证
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from engine.backtest_enhanced import EnhancedBacktestEngine
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from data.fetcher import DataFetcher


class PaperTradingSimulator:
    """实盘模拟器"""

    def __init__(
        self,
        initial_capital: float = 100000,
        monthly_invest: float = 2000,
        fee_rate: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.monthly_invest = monthly_invest
        self.fee_rate = fee_rate
        self.backtest_engine = EnhancedBacktestEngine(
            initial_capital=initial_capital,
            monthly_invest=monthly_invest,
            fee_rate=fee_rate,
        )

    def simulate(
        self,
        data_dict: Dict[str, pd.DataFrame],
        weights: Dict[str, float] = None,
        min_score: float = 45,
        use_enhanced: bool = True,
        start_date: str = "20240101",
        end_date: str = None,
    ) -> Dict:
        """
        运行实盘模拟
        
        Returns:
            模拟结果，包含详细交易记录和绩效分析
        """
        print(f"开始实盘模拟: {start_date} 至 {end_date or '今天'}")
        print(f"参数: 初始资金=¥{self.initial_capital}, 月投=¥{self.monthly_invest}, 最低分={min_score}")
        print(f"权重: {weights}")
        
        # 运行回测
        result = self.backtest_engine.run_with_real_data(
            data_dict=data_dict,
            weights=weights,
            min_score=min_score,
            use_enhanced=use_enhanced,
            start_date=start_date,
            end_date=end_date,
        )
        
        # 添加分析
        result["analysis"] = self._analyze_result(result)
        
        return result

    def _analyze_result(self, result: Dict) -> Dict:
        """分析回测结果"""
        analysis = {}
        
        # 收益分析
        analysis["total_return"] = result.get("total_return", 0)
        analysis["annual_return"] = result.get("annual_return", 0)
        analysis["max_drawdown"] = result.get("max_drawdown", 0)
        analysis["sharpe_ratio"] = result.get("sharpe_ratio", 0)
        
        # 交易分析
        trades = result.get("trades", [])
        if trades:
            analysis["total_trades"] = len(trades)
            analysis["total_invested"] = result.get("total_invested", 0)
            analysis["avg_trade_amount"] = analysis["total_invested"] / len(trades) if trades else 0
            
            # 各标的交易统计
            trade_counts = result.get("trade_counts", {})
            analysis["trade_distribution"] = trade_counts
        else:
            analysis["total_trades"] = 0
            analysis["total_invested"] = 0
            analysis["avg_trade_amount"] = 0
            analysis["trade_distribution"] = {}
        
        # 评分分析
        monthly_scores = result.get("monthly_scores", [])
        if monthly_scores:
            scores_df = pd.DataFrame(monthly_scores)
            for key in ["kc50", "zxhl", "hldb"]:
                if key in scores_df.columns:
                    analysis[f"{key}_avg_score"] = scores_df[key].mean()
                    analysis[f"{key}_min_score"] = scores_df[key].min()
                    analysis[f"{key}_max_score"] = scores_df[key].max()
        
        return analysis

    def compare_strategies(
        self,
        data_dict: Dict[str, pd.DataFrame],
        strategies: List[Dict],
        start_date: str = "20240101",
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        对比多个策略
        
        Args:
            strategies: 策略列表
                [
                    {
                        "name": "策略A",
                        "weights": {...},
                        "min_score": 45,
                    },
                    ...
                ]
                
        Returns:
            DataFrame: 各策略对比结果
        """
        results = []
        
        for strategy in strategies:
            print(f"\n测试策略: {strategy['name']}")
            
            result = self.simulate(
                data_dict=data_dict,
                weights=strategy.get("weights"),
                min_score=strategy.get("min_score", 45),
                use_enhanced=strategy.get("use_enhanced", True),
                start_date=start_date,
                end_date=end_date,
            )
            
            results.append({
                "策略": strategy["name"],
                "总收益": result["total_return"],
                "年化收益": result["annual_return"],
                "最大回撤": result["max_drawdown"],
                "夏普比率": result["sharpe_ratio"],
                "交易次数": result["analysis"]["total_trades"],
                "总投入": result["analysis"]["total_invested"],
            })
        
        return pd.DataFrame(results)


def run_paper_trading_test():
    """运行实盘模拟测试"""
    print("=" * 60)
    print("实盘模拟测试")
    print("=" * 60)
    
    # 初始化
    simulator = PaperTradingSimulator(
        initial_capital=100000,
        monthly_invest=2000,
        fee_rate=0.0005,
    )
    
    # 获取真实数据（最近2年）
    print("\n获取真实数据...")
    data_dict = simulator.backtest_engine.fetch_real_data(
        start_date="20240101"
    )
    
    # 定义对比策略
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
    
    # 对比策略
    comparison = simulator.compare_strategies(
        data_dict=data_dict,
        strategies=strategies,
        start_date="20240101",
    )
    
    print("\n" + "=" * 60)
    print("策略对比结果")
    print("=" * 60)
    print(comparison.to_string(index=False))
    
    # 保存结果
    comparison.to_csv("paper_trading_results.csv", index=False, encoding="utf-8-sig")
    print("\n结果已保存到 paper_trading_results.csv")
    
    return comparison


if __name__ == "__main__":
    run_paper_trading_test()

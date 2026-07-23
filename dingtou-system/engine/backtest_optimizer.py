"""
回测优化器 - 寻找最优min_score_threshold和指标权重
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from itertools import product

from engine.backtest import BacktestEngine
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.indicators import TechnicalIndicators


class RealisticDataGenerator:
    """生成更真实的模拟数据（带趋势、波动、均值回归）"""

    @staticmethod
    def generate(
        symbol: str,
        start_date: str = "20200101",
        end_date: str = "20241231",
        base_price: float = 1000,
        trend: float = 0.03,  # 年化趋势
        volatility: float = 0.25,  # 年化波动率
        mean_reversion: float = 0.1,  # 均值回归强度
    ) -> pd.DataFrame:
        """
        生成真实价格序列（带均值回归的Ornstein-Uhlenbeck过程）
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start=start, end=end, freq="B")
        n = len(dates)

        # 使用固定种子保证可重复性，但不同symbol有不同序列
        # 使用确定性哈希，避免PYTHONHASHSEED导致的不可重复
        import hashlib
        seed_bytes = (symbol + "42").encode("utf-8")
        seed = int(hashlib.md5(seed_bytes).hexdigest()[:8], 16)
        np.random.seed(seed)

        dt = 1 / 252  # 日时间步长
        sigma = volatility * np.sqrt(dt)
        theta = mean_reversion  # 均值回归速度
        mu = np.log(base_price)  # 对数价格长期均值
        drift = (trend - 0.5 * volatility**2) * dt  # 趋势项（Girsanov）

        # Ornstein-Uhlenbeck过程模拟对数价格
        log_prices = np.zeros(n)
        log_prices[0] = np.log(base_price)

        for i in range(1, n):
            # OU过程: dX = theta*(mu - X)*dt + sigma*dW + drift*dt
            dW = np.random.normal(0, 1)
            log_prices[i] = (
                log_prices[i-1]
                + theta * (mu - log_prices[i-1]) * dt
                + drift
                + sigma * dW
            )

        prices = np.exp(log_prices)

        # 计算日波动率（用于OHLC生成）
        daily_vol = volatility / np.sqrt(252)

        # 生成OHLC - 使用确定性种子
        np.random.seed((hash(symbol) + 44) % 2**32)
        opens = prices * (1 + np.random.normal(0, daily_vol * 0.3, n))
        np.random.seed((hash(symbol) + 45) % 2**32)
        highs = np.maximum(
            prices * (1 + abs(np.random.normal(0, daily_vol * 0.8, n))),
            np.maximum(opens, prices)
        )
        np.random.seed((hash(symbol) + 46) % 2**32)
        lows = np.minimum(
            prices * (1 - abs(np.random.normal(0, daily_vol * 0.8, n))),
            np.minimum(opens, prices)
        )

        # 成交量（与波动正相关）- 使用确定性种子
        np.random.seed((hash(symbol) + 47) % 2**32)
        volume = np.random.lognormal(15, 0.5, n) * (1 + abs(np.random.normal(0, daily_vol, n)) * 10)

        df = pd.DataFrame({
            "date": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volume.astype(int),
            "amount": (volume * prices).astype(int),
            "amplitude": ((highs - lows) / prices * 100),
            "pct_change": np.concatenate([[0], np.diff(prices) / prices[:-1] * 100]),
            "change": np.concatenate([[0], np.diff(prices)]),
            "turnover": np.random.uniform(0.5, 5.0, n),
        })

        return df


class BacktestOptimizer:
    """回测优化器"""

    def __init__(self):
        self.data_generator = RealisticDataGenerator()

    def generate_test_data(
        self,
        indices_config: Dict[str, dict],
        start_date: str = "20200101",
        end_date: str = "20241231",
    ) -> Dict[str, pd.DataFrame]:
        """生成测试数据"""
        data = {}
        for key, config in indices_config.items():
            df = self.data_generator.generate(
                symbol=key,
                start_date=start_date,
                end_date=end_date,
                base_price=config.get("base_price", 1000),
                trend=config.get("trend", 0.03),
                volatility=config.get("volatility", 0.25),
                mean_reversion=config.get("mean_reversion", 0.1),
            )
            # 计算技术指标
            df = TechnicalIndicators.calculate_all(df)
            data[key] = df
        return data

    def run_single_backtest(
        self,
        data_dict: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
        min_score: float,
        base_amount: float = 2000,
        fee_rate: float = 0.0005,
    ) -> Dict:
        """运行单次回测"""
        # 创建评分函数
        def score_func(row):
            engine = ScoringEngine(weights=weights)
            result = engine.calculate_total_score(row)
            return result["total"]

        # 创建分配函数
        def allocation_func(scores):
            engine = AllocationEngine(
                base_amount=base_amount,
                min_score=min_score,
                max_single_ratio=0.6,
            )
            return engine.allocate(scores)

        # 运行回测
        bt = BacktestEngine(
            initial_capital=0,  # 定投从零开始
            monthly_invest=base_amount,
            fee_rate=fee_rate,
        )

        result = bt.run(
            data_dict=data_dict,
            score_func=score_func,
            allocation_func=allocation_func,
            start_date=data_dict[list(data_dict.keys())[0]]["date"].min().strftime("%Y%m%d"),
            end_date=data_dict[list(data_dict.keys())[0]]["date"].max().strftime("%Y%m%d"),
        )

        return result

    def optimize_min_score(
        self,
        data_dict: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
        score_range: List[float] = None,
    ) -> Tuple[float, List[Dict]]:
        """
        优化最低投资阈值

        Returns:
            (最优阈值, 所有测试结果)
        """
        if score_range is None:
            score_range = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

        results = []
        for min_score in score_range:
            result = self.run_single_backtest(data_dict, weights, min_score)

            # 综合评分（考虑收益、回撤、夏普比率）
            # 目标：最大化风险调整收益，同时保证一定交易频率
            annual_return = result["annual_return"]
            max_drawdown = result["max_drawdown"]
            sharpe = result["sharpe_ratio"]
            n_trades = len(result["trades"])

            # 综合得分（越高越好）
            # 惩罚过大回撤，奖励高夏普
            if max_drawdown > 0:
                score = (
                    annual_return * 0.4
                    + sharpe * 10 * 0.3
                    - max_drawdown * 0.2
                    + min(n_trades / 12, 5) * 0.1  # 保证至少一年交易几次
                )
            else:
                score = annual_return * 0.4 + sharpe * 10 * 0.3 + min(n_trades / 12, 5) * 0.1

            results.append({
                "min_score": min_score,
                "annual_return": result["annual_return"],
                "total_return": result["total_return"],
                "max_drawdown": result["max_drawdown"],
                "sharpe_ratio": result["sharpe_ratio"],
                "n_trades": n_trades,
                "final_value": result["final_value"],
                "composite_score": score,
            })

        # 找到最优
        best = max(results, key=lambda x: x["composite_score"])
        return best["min_score"], results

    def optimize_weights(
        self,
        data_dict: Dict[str, pd.DataFrame],
        min_score: float,
        n_trials: int = 50,
    ) -> Tuple[Dict[str, float], List[Dict]]:
        """
        使用随机搜索优化权重

        Returns:
            (最优权重, 所有测试结果)
        """
        np.random.seed(42)

        best_score = -np.inf
        best_weights = None
        results = []

        for i in range(n_trials):
            # 随机生成权重（Dirichlet分布保证和为1）
            weights_raw = np.random.dirichlet([1, 1, 1, 1, 1])
            weights = {
                "technical": weights_raw[0],
                "valuation": weights_raw[1],
                "momentum": weights_raw[2],
                "sentiment": weights_raw[3],
                "fundflow": weights_raw[4],
            }

            result = self.run_single_backtest(data_dict, weights, min_score)

            annual_return = result["annual_return"]
            max_drawdown = result["max_drawdown"]
            sharpe = result["sharpe_ratio"]
            n_trades = len(result["trades"])

            if max_drawdown > 0:
                composite = (
                    annual_return * 0.4
                    + sharpe * 10 * 0.3
                    - max_drawdown * 0.2
                    + min(n_trades / 12, 5) * 0.1
                )
            else:
                composite = annual_return * 0.4 + sharpe * 10 * 0.3 + min(n_trades / 12, 5) * 0.1

            results.append({
                "trial": i,
                "weights": weights,
                "annual_return": annual_return,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe,
                "n_trades": n_trades,
                "composite_score": composite,
            })

            if composite > best_score:
                best_score = composite
                best_weights = weights.copy()

        return best_weights, results

    def full_optimization(
        self,
        indices_config: Dict[str, dict] = None,
        start_date: str = "20200101",
        end_date: str = "20241231",
    ) -> Dict:
        """
        完整优化流程
        """
        if indices_config is None:
            indices_config = {
                "kc50": {"base_price": 1000, "trend": 0.05, "volatility": 0.30, "mean_reversion": 0.08},
                "zxhl": {"base_price": 2000, "trend": 0.02, "volatility": 0.18, "mean_reversion": 0.12},
                "hldb": {"base_price": 1500, "trend": 0.03, "volatility": 0.15, "mean_reversion": 0.15},
            }

        print("=" * 60)
        print("开始回测优化")
        print("=" * 60)

        # 生成数据
        print("\n[1/3] 生成测试数据...")
        data_dict = self.generate_test_data(indices_config, start_date, end_date)
        for key, df in data_dict.items():
            print(f"  {key}: {len(df)} 条记录, 价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

        # 步骤1：使用默认权重优化min_score
        print("\n[2/3] 优化最低投资阈值...")
        default_weights = {
            "technical": 0.40,
            "valuation": 0.25,
            "momentum": 0.15,
            "sentiment": 0.10,
            "fundflow": 0.10,
        }
        best_min_score, score_results = self.optimize_min_score(data_dict, default_weights)

        print(f"\n  阈值优化结果:")
        print(f"  {'阈值':>6} {'年化收益':>10} {'总收益':>10} {'最大回撤':>10} {'夏普':>8} {'交易次数':>8} {'综合分':>8}")
        print(f"  {'-'*60}")
        for r in score_results:
            print(f"  {r['min_score']:>6} {r['annual_return']:>9.2f}% {r['total_return']:>9.2f}% {r['max_drawdown']:>9.2f}% {r['sharpe_ratio']:>8.2f} {r['n_trades']:>8} {r['composite_score']:>8.2f}")

        print(f"\n  最优阈值: {best_min_score}")

        # 步骤2：使用最优阈值优化权重
        print(f"\n[3/3] 优化指标权重 (使用阈值={best_min_score})...")
        best_weights, weight_results = self.optimize_weights(data_dict, best_min_score, n_trials=100)

        print(f"\n  权重优化结果 (Top 10):")
        sorted_results = sorted(weight_results, key=lambda x: x["composite_score"], reverse=True)[:10]
        print(f"  {'排名':>4} {'技术':>6} {'估值':>6} {'动量':>6} {'情绪':>6} {'资金':>6} {'年化':>8} {'回撤':>8} {'夏普':>8} {'综合':>8}")
        print(f"  {'-'*80}")
        for i, r in enumerate(sorted_results, 1):
            w = r["weights"]
            print(f"  {i:>4} {w['technical']:>6.3f} {w['valuation']:>6.3f} {w['momentum']:>6.3f} {w['sentiment']:>6.3f} {w['fundflow']:>6.3f} {r['annual_return']:>7.2f}% {r['max_drawdown']:>7.2f}% {r['sharpe_ratio']:>8.2f} {r['composite_score']:>8.2f}")

        print(f"\n  最优权重:")
        for k, v in best_weights.items():
            print(f"    {k}: {v:.3f}")

        return {
            "best_min_score": best_min_score,
            "best_weights": best_weights,
            "score_results": score_results,
            "weight_results": weight_results,
            "data_dict": data_dict,
        }


if __name__ == "__main__":
    optimizer = BacktestOptimizer()
    result = optimizer.full_optimization()

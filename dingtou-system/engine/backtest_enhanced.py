"""
回测引擎 - 增强版
支持真实数据、增强评分、参数优化
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
from engine.scoring import ScoringEngine
from engine.valuation import EnhancedScoringEngine
from engine.allocation import AllocationEngine
from data.fetcher import DataFetcher


class EnhancedBacktestEngine:
    """增强版回测引擎"""

    def __init__(
        self,
        initial_capital: float = 100000,
        monthly_invest: float = 2000,
        fee_rate: float = 0.0005,
        dividend_yields: Dict[str, float] = None,
    ):
        self.initial_capital = initial_capital
        self.monthly_invest = monthly_invest
        self.fee_rate = fee_rate
        self.dividend_yields = dividend_yields or {
            "kc50": 0.005, "a50": 0.025, "a500": 0.020,
            "zxhl": 0.05, "hldb": 0.045,
        }
        self.fetcher = DataFetcher()

    def fetch_real_data(
        self,
        start_date: str = "20230101",
        end_date: str = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        获取真实历史数据
        
        Returns:
            {index_key: DataFrame with indicators}
        """
        from engine.indicators import TechnicalIndicators
        
        print("获取真实数据...")
        data = self.fetcher.fetch_all_indices(start_date=start_date, end_date=end_date)
        
        # 计算技术指标
        for key, df in data.items():
            if df is not None and not df.empty:
                print(f"计算 {key} 技术指标...")
                df = TechnicalIndicators.calculate_all(df)
                data[key] = df
        
        return data

    def run_with_real_data(
        self,
        data_dict: Dict[str, pd.DataFrame],
        weights: Dict[str, float] = None,
        min_score: float = 45,
        use_enhanced: bool = True,
        start_date: str = "20230101",
        end_date: str = None,
    ) -> Dict:
        """
        使用真实数据运行回测
        
        Args:
            data_dict: 真实数据
            weights: 评分权重
            min_score: 最低投资分数
            use_enhanced: 是否使用增强评分
            start_date: 回测开始
            end_date: 回测结束
            
        Returns:
            回测结果
        """
        if use_enhanced:
            score_engine = EnhancedScoringEngine(weights=weights)
            
            # 准备价格字典（用于轮动计算）
            prices_dict = {}
            for key, df in data_dict.items():
                if df is not None and not df.empty:
                    prices_dict[key] = df.set_index("date")["close"]
            
            def score_func(row, index_key, close_history):
                return score_engine.calculate_total_score_enhanced(
                    row, index_key, close_history, prices_dict
                )["total"]
        else:
            score_engine = ScoringEngine(weights=weights)
            
            def score_func(row, index_key=None, close_history=None):
                return score_engine.calculate_total_score(row)["total"]

        allocation_engine = AllocationEngine(
            base_amount=self.monthly_invest,
            min_score=min_score
        )
        
        def allocation_func(scores):
            return allocation_engine.allocate(scores)

        return self.run(
            data_dict=data_dict,
            score_func=score_func,
            allocation_func=allocation_func,
            start_date=start_date,
            end_date=end_date,
        )

    def run(
        self,
        data_dict: Dict[str, pd.DataFrame],
        score_func: Callable,
        allocation_func: Callable,
        start_date: str = "20230101",
        end_date: str = None,
    ) -> Dict:
        """
        运行回测
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else pd.to_datetime("today")

        # 生成每月第一个交易日
        trading_days = self._get_monthly_trading_days(data_dict, start, end)
        
        if not trading_days:
            print("警告: 没有可用的交易日")
            return self._empty_result()

        # 初始化
        cash = self.initial_capital
        cumulative_invested = self.initial_capital
        positions = {key: 0.0 for key in data_dict.keys()}
        trades = []
        dividends = []
        portfolio_values = []
        monthly_scores = []
        last_div_quarter = None

        for trade_date in trading_days:
            # 每月追加定投资金
            cash += self.monthly_invest
            cumulative_invested += self.monthly_invest
            
            # 获取当日各指数数据
            scores = {}
            close_histories = {}
            
            for key, df in data_dict.items():
                if df is None or df.empty:
                    continue
                    
                day_data = df[df["date"] <= trade_date]
                if len(day_data) > 0:
                    row = day_data.iloc[-1]
                    
                    # 获取历史数据（用于计算百分位）
                    history = day_data["close"] if len(day_data) > 60 else None
                    
                    try:
                        scores[key] = score_func(row, key, history)
                    except:
                        scores[key] = score_func(row)
                else:
                    scores[key] = 50

            # 记录分数
            monthly_scores.append({
                "date": trade_date,
                **scores
            })

            # 资金分配
            allocation = allocation_func(scores)

            # 执行交易
            for rec in allocation.get("recommendations", []):
                if rec["amount"] > 0:
                    key = rec["index_key"]
                    amount = rec["amount"]

                    # 获取当日价格
                    df = data_dict[key]
                    if df is None or df.empty:
                        continue
                        
                    price_data = df[df["date"] <= trade_date]
                    if len(price_data) == 0:
                        continue
                        
                    day_price = price_data["close"].iloc[-1]

                    # 手续费（扣减模式）
                    fee = amount * self.fee_rate
                    invest_amount = amount - fee

                    # 检查资金是否充足
                    if cash < amount:
                        if cash <= fee:
                            continue
                        amount = cash
                        fee = amount * self.fee_rate
                        invest_amount = amount - fee

                    # 计算购买份额
                    shares = invest_amount / day_price
                    positions[key] += shares
                    cash -= amount

                    trades.append({
                        "date": trade_date,
                        "index_key": key,
                        "amount": amount,
                        "price": day_price,
                        "shares": shares,
                        "fee": fee,
                    })

            # 红利再投资（每季度一次）
            quarter = (trade_date.year, (trade_date.month - 1) // 3)
            if quarter != last_div_quarter:
                last_div_quarter = quarter
            if trade_date.month in [3, 6, 9, 12] and trade_date.day <= 5:
                for key in positions:
                    if positions[key] > 0:
                        df = data_dict[key]
                        if df is None or df.empty:
                            continue
                        price_data = df[df["date"] <= trade_date]
                        if len(price_data) == 0:
                            continue
                        day_price = price_data["close"].iloc[-1]

                        div_yield = self.dividend_yields.get(key, 0.0)
                        if div_yield <= 0:
                            continue
                        quarterly_dividend_rate = div_yield / 4
                        dividend_amount = positions[key] * day_price * quarterly_dividend_rate

                        if dividend_amount > 0:
                            dividend_shares = dividend_amount / day_price
                            positions[key] += dividend_shares

            # 计算当日组合价值
            portfolio_value = cash
            for key, df in data_dict.items():
                if df is None or df.empty:
                    continue
                    
                price_data = df[df["date"] <= trade_date]
                if len(price_data) > 0:
                    day_price = price_data["close"].iloc[-1]
                    portfolio_value += positions[key] * day_price

            portfolio_values.append({
                "date": trade_date,
                "value": portfolio_value,
                "cash": cash,
            })

        return self._calculate_metrics(
            portfolio_values, trades, monthly_scores, cumulative_invested, start, end
        )

    def _calculate_metrics(
        self,
        portfolio_values: List[Dict],
        trades: List[Dict],
        monthly_scores: List[Dict],
        cumulative_invested: float,
        start: datetime,
        end: datetime,
    ) -> Dict:
        """计算回测指标"""
        if not portfolio_values:
            return self._empty_result()

        # 基础指标
        final_value = portfolio_values[-1]["value"]
        total_invested = cumulative_invested
        
        total_return = (final_value - total_invested) / total_invested * 100 if total_invested > 0 else 0

        years = (end - start).days / 365.25
        if years > 0 and total_invested > 0 and final_value > 0:
            avg_invested_time = years / 2
            annual_return = ((final_value / total_invested) ** (1 / avg_invested_time) - 1) * 100
        else:
            annual_return = 0

        # 最大回撤
        values = [v["value"] for v in portfolio_values]
        max_drawdown = self._calculate_max_drawdown(values)

        # 夏普比率
        sharpe = self._calculate_sharpe(portfolio_values)

        # 交易统计
        total_fees = sum(t["fee"] for t in trades)
        
        # 各标的交易次数
        trade_counts = {}
        for t in trades:
            key = t["index_key"]
            trade_counts[key] = trade_counts.get(key, 0) + 1

        return {
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_invested": round(total_invested, 2),
            "total_fees": round(total_fees, 2),
            "trade_counts": trade_counts,
            "trades": trades,
            "portfolio_values": portfolio_values,
            "monthly_scores": monthly_scores,
        }

    def _calculate_sharpe(self, portfolio_values: List[Dict]) -> float:
        """计算夏普比率（使用对数收益率）"""
        if len(portfolio_values) < 2:
            return 0.0

        # 计算月度对数收益率
        log_returns = []
        for i in range(1, len(portfolio_values)):
            if portfolio_values[i-1]["value"] > 0 and portfolio_values[i]["value"] > 0:
                log_ret = np.log(portfolio_values[i]["value"] / portfolio_values[i-1]["value"])
                log_returns.append(log_ret)

        if not log_returns or len(log_returns) < 2:
            return 0.0

        avg_return = np.mean(log_returns)
        std_return = np.std(log_returns, ddof=1)  # 使用样本标准差

        if std_return > 0:
            risk_free_annual = 0.03
            risk_free_monthly_log = np.log(1 + risk_free_annual) / 12
            sharpe = ((avg_return - risk_free_monthly_log) / std_return) * np.sqrt(12)
        else:
            sharpe = 0.0

        return sharpe

    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """计算最大回撤"""
        if not values:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak * 100
            else:
                dd = 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _get_monthly_trading_days(
        self,
        data_dict: Dict[str, pd.DataFrame],
        start: datetime,
        end: datetime,
    ) -> List[datetime]:
        """获取每月第一个交易日"""
        first_key = list(data_dict.keys())[0]
        df = data_dict[first_key]
        
        if df is None or df.empty:
            return []
            
        df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
        
        if df.empty:
            return []

        df["year_month"] = df["date"].dt.to_period("M")
        monthly_first = df.groupby("year_month")["date"].first().reset_index(drop=True)

        return monthly_first.tolist()

    def _empty_result(self) -> Dict:
        """空结果"""
        return {
            "initial_capital": self.initial_capital,
            "final_value": self.initial_capital,
            "total_return": 0.0,
            "annual_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "total_invested": 0.0,
            "total_fees": 0.0,
            "trade_counts": {},
            "trades": [],
            "portfolio_values": [],
            "monthly_scores": [],
        }

    def optimize_parameters(
        self,
        data_dict: Dict[str, pd.DataFrame],
        param_grid: Dict[str, List],
        start_date: str = "20230101",
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        参数优化
        
        Args:
            data_dict: 数据
            param_grid: 参数网格
                {
                    "min_score": [30, 40, 50, 60],
                    "technical_weight": [0.2, 0.3, 0.4],
                    "valuation_weight": [0.15, 0.25, 0.35],
                    ...
                }
            
        Returns:
            DataFrame: 各参数组合的回测结果
        """
        results = []
        
        # 生成参数组合
        from itertools import product
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        for combo in product(*values):
            params = dict(zip(keys, combo))
            
            # 构建权重
            weights = {
                "technical": params.get("technical_weight", 0.25),
                "valuation": params.get("valuation_weight", 0.20),
                "momentum": params.get("momentum_weight", 0.15),
                "sentiment": params.get("sentiment_weight", 0.10),
                "fundflow": params.get("fundflow_weight", 0.15),
                "rotation": params.get("rotation_weight", 0.15),
            }
            
            min_score = params.get("min_score", 45)
            
            # 运行回测
            result = self.run_with_real_data(
                data_dict=data_dict,
                weights=weights,
                min_score=min_score,
                use_enhanced=True,
                start_date=start_date,
                end_date=end_date,
            )
            
            results.append({
                **params,
                **{k: v for k, v in result.items() if k not in ["trades", "portfolio_values", "monthly_scores"]}
            })
        
        return pd.DataFrame(results)


if __name__ == "__main__":
    # 测试
    engine = EnhancedBacktestEngine()
    
    # 获取真实数据
    data = engine.fetch_real_data(start_date="20230101")
    
    # 运行回测
    result = engine.run_with_real_data(
        data_dict=data,
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
        start_date="20230101",
    )
    
    print("回测结果:")
    print(f"  初始资金: ¥{result['initial_capital']}")
    print(f"  最终价值: ¥{result['final_value']}")
    print(f"  总收益: {result['total_return']}%")
    print(f"  年化收益: {result['annual_return']}%")
    print(f"  最大回撤: {result['max_drawdown']}%")
    print(f"  夏普比率: {result['sharpe_ratio']}")
    print(f"  总投入: ¥{result['total_invested']}")
    print(f"  总手续费: ¥{result['total_fees']:.2f}")
    print(f"  交易次数: {result['trade_counts']}")

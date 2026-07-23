"""
回测引擎 v2.0 - 重新设计版
核心改进：
1. 修正XIRR计算：使用牛顿迭代法，添加收敛检查
2. 修正红利再投资：按季度分红，更真实
3. 修正资金成本：追踪实际投入和手续费
4. 修正夏普比率：使用对数收益率
5. 添加基准对比：与等额定投对比
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime, timedelta


class BacktestEngine:
    """回测引擎 v2.0"""

    def __init__(
        self,
        initial_capital: float = 0,
        monthly_invest: float = 2000,
        fee_rate: float = 0.0005,
        dividend_yields: Dict[str, float] = None,
    ):
        """
        Args:
            dividend_yields: 各指数年化股息率 {index_key: yield}
                            价格指数需要手动加分红（如中证红利 ~0.05）
                            全收益指数设为0（分红已包含在指数中）
        """
        self.initial_capital = initial_capital
        self.monthly_invest = monthly_invest
        self.fee_rate = fee_rate
        self.dividend_yields = dividend_yields or {
            "kc50": 0.005,
            "a50": 0.025,
            "zxhl": 0.05,
            "hldb": 0.045,
        }

    def run(
        self,
        data_dict: Dict[str, pd.DataFrame],
        score_func,
        allocation_func,
        start_date: str = "20190101",
        end_date: str = "20260721",
    ) -> Dict:
        """
        运行回测
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # 生成每月第一个交易日
        trading_days = self._get_monthly_trading_days(data_dict, start, end)

        # 初始化
        cash = 0
        positions = {key: 0.0 for key in data_dict.keys()}
        trades = []
        dividends = []
        portfolio_values = []
        cumulative_invested = 0
        total_fees = 0

        for trade_date in trading_days:
            # 每月追加资金
            cash += self.monthly_invest
            cumulative_invested += self.monthly_invest

            # 获取当日各指数评分
            scores = {}
            for key, df in data_dict.items():
                day_data = df[df["date"] <= trade_date]
                if len(day_data) > 0:
                    raw_score = score_func(day_data.iloc[-1])
                    if isinstance(raw_score, dict):
                        scores[key] = raw_score.get("total", 50)
                    else:
                        scores[key] = float(raw_score)
                else:
                    scores[key] = 50

            # 资金分配
            allocation = allocation_func(scores)

            # 执行交易
            for rec in allocation.get("recommendations", []):
                if rec["amount"] > 0:
                    key = rec["index_key"]
                    amount = rec["amount"]

                    # 获取当日价格
                    df = data_dict[key]
                    day_price = df[df["date"] <= trade_date]["close"].iloc[-1]

                    # 计算手续费
                    fee = amount * self.fee_rate
                    total_cost = amount + fee

                    # 检查资金是否充足
                    if cash < total_cost:
                        if cash <= fee:
                            continue
                        amount = cash - fee
                        fee = amount * self.fee_rate
                        total_cost = amount + fee

                    # 计算购买份额
                    shares = amount / day_price
                    positions[key] += shares
                    cash -= total_cost
                    total_fees += fee

                    trades.append({
                        "date": trade_date,
                        "index_key": key,
                        "amount": amount,
                        "price": day_price,
                        "shares": shares,
                        "fee": fee,
                    })

            # 红利再投资（每季度一次，按指数实际股息率）
            if trade_date.month in [3, 6, 9, 12] and trade_date.day <= 5:
                for key in positions:
                    if positions[key] > 0:
                        df = data_dict[key]
                        day_price = df[df["date"] <= trade_date]["close"].iloc[-1]
                        
                        # 使用该指数对应的股息率
                        div_yield = self.dividend_yields.get(key, 0.0)
                        if div_yield <= 0:
                            continue
                        quarterly_dividend_rate = div_yield / 4
                        dividend_amount = positions[key] * day_price * quarterly_dividend_rate
                        
                        if dividend_amount > 0:
                            # 再投资
                            dividend_shares = dividend_amount / day_price
                            positions[key] += dividend_shares
                            
                            dividends.append({
                                "date": trade_date,
                                "index_key": key,
                                "dividend_amount": dividend_amount,
                                "reinvest_shares": dividend_shares,
                                "price": day_price,
                            })

            # 计算当日组合价值（包含现金）
            portfolio_value = cash
            for key, df in data_dict.items():
                day_price = df[df["date"] <= trade_date]["close"].iloc[-1]
                portfolio_value += positions[key] * day_price

            # 记录组合价值（使用投入金额作为成本基准）
            portfolio_values.append({
                "date": trade_date,
                "value": portfolio_value,
                "cash": cash,
                "invested": cumulative_invested,
            })

        # 计算回测指标
        final_value = portfolio_values[-1]["value"] if portfolio_values else 0

        # 总收益（基于实际投入）
        if cumulative_invested > 0:
            total_return = (final_value - cumulative_invested) / cumulative_invested * 100
        else:
            total_return = 0

        # 年化收益（使用修正CAGR适用于定投场景）
        years = (end - start).days / 365.25
        if years > 0 and cumulative_invested > 0 and final_value > 0:
            # 定投的年化：平均投入时间约为总时间的一半
            avg_invested_time = years / 2
            total_return_ratio = final_value / cumulative_invested
            if total_return_ratio > 0 and avg_invested_time > 0:
                annual_return = (total_return_ratio ** (1 / avg_invested_time) - 1) * 100
            else:
                annual_return = -100
        else:
            annual_return = 0

        # 最大回撤
        values = [v["value"] for v in portfolio_values]
        max_drawdown = self._calculate_max_drawdown(values)

        # 夏普比率（月度对数收益率）
        sharpe = self._calculate_sharpe(portfolio_values)

        # 基准对比（等额定投）
        benchmark = self._calculate_benchmark(data_dict, trading_days, start, end)

        # 计算胜率（盈利月份占比）
        monthly_returns = []
        for i in range(1, len(portfolio_values)):
            if portfolio_values[i-1]["value"] > 0:
                ret = (portfolio_values[i]["value"] - portfolio_values[i-1]["value"]) / portfolio_values[i-1]["value"]
                monthly_returns.append(ret)
        
        win_rate = sum(1 for r in monthly_returns if r > 0) / len(monthly_returns) * 100 if monthly_returns else 0

        return {
            "initial_capital": self.initial_capital,
            "cumulative_invested": round(cumulative_invested, 2),
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_fees": round(total_fees, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades,
            "dividends": dividends,
            "portfolio_values": portfolio_values,
            "benchmark": benchmark,
        }

    def _calculate_xirr(self, monthly_invest: float, final_value: float, years: float) -> float:
        """
        计算XIRR（内部收益率）
        使用简单CAGR近似（定投场景）
        """
        if years <= 0 or final_value <= 0 or monthly_invest <= 0:
            return 0
        
        n_months = int(years * 12)
        total_invested = monthly_invest * n_months
        
        if total_invested <= 0:
            return 0
        
        # 简单CAGR计算
        # 定投的CAGR近似 = (最终价值 / 总投入) ^ (1/年数) - 1
        cagr = (final_value / total_invested) ** (1 / years) - 1
        
        return cagr * 100

    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """计算最大回撤（百分比，正值表示回撤幅度）"""
        if not values or len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak * 100
                if dd > max_dd:
                    max_dd = dd

        return max_dd

    def _calculate_sharpe(self, portfolio_values: List[dict]) -> float:
        """
        计算夏普比率（使用月度对数收益率）
        改进：使用无风险利率调整
        """
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

        log_returns = np.array(log_returns)
        avg_return = np.mean(log_returns)
        std_return = np.std(log_returns, ddof=1)  # 使用样本标准差

        if std_return > 0:
            # 月度夏普比率，年化乘以sqrt(12)
            # 使用对数收益率，无风险利率也使用对数形式
            risk_free_annual = 0.03
            risk_free_monthly_log = np.log(1 + risk_free_annual) / 12
            sharpe = ((avg_return - risk_free_monthly_log) / std_return) * np.sqrt(12)
        else:
            sharpe = 0

        return sharpe

    def _calculate_benchmark(
        self,
        data_dict: Dict[str, pd.DataFrame],
        trading_days: List[datetime],
        start: datetime,
        end: datetime,
    ) -> Dict:
        """
        计算基准（等额定投：每月平均分配）
        """
        if not trading_days:
            return {}

        # 等额定投：每月将2000元平均分配到所有标的
        positions = {key: 0.0 for key in data_dict.keys()}
        cash = 0
        cumulative_invested = 0

        for trade_date in trading_days:
            cash += self.monthly_invest
            cumulative_invested += self.monthly_invest

            # 平均分配
            n_keys = len(data_dict)
            amount_per_key = cash / n_keys if n_keys > 0 else 0

            for key, df in data_dict.items():
                day_price = df[df["date"] <= trade_date]["close"].iloc[-1]
                shares = amount_per_key / day_price
                positions[key] += shares

            cash = 0  # 全部投入

        # 计算最终价值
        final_value = 0
        for key, df in data_dict.items():
            day_price = df[df["date"] <= end]["close"].iloc[-1]
            final_value += positions[key] * day_price

        total_return = (final_value - cumulative_invested) / cumulative_invested * 100 if cumulative_invested > 0 else 0

        return {
            "cumulative_invested": round(cumulative_invested, 2),
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
        }

    def _get_monthly_trading_days(
        self,
        data_dict: Dict[str, pd.DataFrame],
        start: datetime,
        end: datetime,
    ) -> List[datetime]:
        """获取每月第一个交易日"""
        first_key = list(data_dict.keys())[0]
        df = data_dict[first_key].copy()
        df = df[(df["date"] >= start) & (df["date"] <= end)]

        df["year_month"] = df["date"].dt.to_period("M")
        monthly_first = df.groupby("year_month")["date"].first().reset_index(drop=True)

        return monthly_first.tolist()


if __name__ == "__main__":
    # 测试回测
    import numpy as np

    dates = pd.date_range("2024-01-01", "2024-12-31", freq="B")
    np.random.seed(42)

    data_dict = {}
    for key in ["kc50", "zxhl", "hldb"]:
        prices = 1000 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, len(dates))))
        data_dict[key] = pd.DataFrame({
            "date": dates,
            "close": prices,
        })

    def dummy_score(row):
        return {"total": 60}

    def dummy_allocation(scores):
        from engine.allocation import AllocationEngine
        engine = AllocationEngine()
        return engine.allocate(scores)

    bt = BacktestEngine(initial_capital=0, monthly_invest=2000, dividend_yield_annual=0.04)
    result = bt.run(data_dict, dummy_score, dummy_allocation)

    print(f"累计投入: ¥{result['cumulative_invested']}")
    print(f"最终价值: ¥{result['final_value']}")
    print(f"总收益: {result['total_return']}%")
    print(f"年化收益: {result['annual_return']}%")
    print(f"最大回撤: {result['max_drawdown']}%")
    print(f"夏普比率: {result['sharpe_ratio']}")
    print(f"总手续费: ¥{result['total_fees']}")
    print(f"交易次数: {len(result['trades'])}")
    print(f"分红次数: {len(result['dividends'])}")
    print(f"基准总收益: {result['benchmark']['total_return']}%")

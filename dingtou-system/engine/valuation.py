"""
估值指标计算器 - 增强版
支持PE/PB百分位、股息率百分位、行业轮动等
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


class ValuationIndicators:
    """估值指标计算器"""

    def __init__(self):
        # 指数基准估值（基于历史数据估算）
        self.base_valuations = {
            "kc50": {"pe": 45.0, "pb": 4.5, "dividend_yield": 0.5},
            "zxhl": {"pe": 7.5, "pb": 0.85, "dividend_yield": 5.5},
            "hldb": {"pe": 6.8, "pb": 0.75, "dividend_yield": 6.0},
        }

    def calculate_pe_percentile(
        self, 
        close: pd.Series, 
        index_key: str,
        window: int = 252 * 3  # 3年滚动窗口
    ) -> pd.Series:
        """
        计算PE百分位（基于价格代理）
        
        原理：价格越低，PE越低（假设盈利稳定）
        使用3年滚动窗口计算当前价格处于历史什么位置
        
        Args:
            close: 收盘价序列
            index_key: 指数代码
            window: 历史窗口（交易日数）
            
        Returns:
            PE百分位序列 (0-100)
        """
        # 使用价格作为PE代理（价格与PE成正比）
        # 计算价格在历史窗口中的百分位
        rolling_min = close.rolling(window=window, min_periods=60).min()
        rolling_max = close.rolling(window=window, min_periods=60).max()
        
        # 避免除以零
        range_val = rolling_max - rolling_min
        range_val = range_val.replace(0, np.nan)
        
        percentile = (close - rolling_min) / range_val * 100
        percentile = percentile.fillna(50)  # 数据不足时默认50%
        
        return percentile

    def calculate_pb_percentile(
        self, 
        close: pd.Series,
        index_key: str,
        window: int = 252 * 3
    ) -> pd.Series:
        """
        计算PB百分位
        
        原理与PE类似，PB与价格成正比（假设净资产稳定）
        """
        return self.calculate_pe_percentile(close, index_key, window)

    def calculate_dividend_yield_percentile(
        self,
        close: pd.Series,
        index_key: str,
        window: int = 252 * 3
    ) -> pd.Series:
        """
        计算股息率百分位
        
        原理：价格越低，股息率越高（假设分红稳定）
        因此股息率百分位 = 100 - 价格百分位
        """
        price_percentile = self.calculate_pe_percentile(close, index_key, window)
        return 100 - price_percentile

    def calculate_valuation_score(
        self,
        row: pd.Series,
        index_key: str,
        close_history: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        计算综合估值评分
        
        Returns:
            dict: {
                "pe_percentile": PE百分位,
                "pb_percentile": PB百分位,
                "dividend_percentile": 股息率百分位,
                "valuation_score": 估值得分 (0-100, 越低越便宜)
            }
        """
        close = row.get("close", 1000)
        
        # 如果有历史数据，计算百分位
        if close_history is not None and len(close_history) >= 60:
            pe_pct = self.calculate_pe_percentile(close_history, index_key).iloc[-1]
            pb_pct = self.calculate_pb_percentile(close_history, index_key).iloc[-1]
            div_pct = self.calculate_dividend_yield_percentile(close_history, index_key).iloc[-1]
        else:
            # 使用简化方法：基于MA60的位置
            ma60 = row.get("ma_60", close)
            if ma60 > 0:
                price_ratio = (close - ma60) / ma60 * 100
                # 映射到0-100
                pe_pct = max(0, min(100, 50 + price_ratio * 2))
                pb_pct = pe_pct
                div_pct = 100 - pe_pct
            else:
                pe_pct = 50
                pb_pct = 50
                div_pct = 50
        
        # 估值得分：越低越便宜（得分越高）
        # PE百分位低 = 便宜 = 高分
        # PB百分位低 = 便宜 = 高分
        # 股息率百分位高 = 便宜 = 高分
        valuation_score = (
            (100 - pe_pct) * 0.35 +  # PE权重35%
            (100 - pb_pct) * 0.35 +  # PB权重35%
            div_pct * 0.30           # 股息率权重30%
        )
        
        return {
            "pe_percentile": pe_pct,
            "pb_percentile": pb_pct,
            "dividend_percentile": div_pct,
            "valuation_score": valuation_score,
        }


class MarketRotationIndicators:
    """市场轮动指标"""

    @staticmethod
    def calculate_relative_strength(
        prices: pd.Series,
        benchmark: pd.Series,
        window: int = 20
    ) -> pd.Series:
        """
        计算相对强弱（相对于基准）
        
        RS = (指数涨幅 / 基准涨幅) - 1
        RS > 0 表示强于基准
        """
        # 计算收益率
        ret = prices.pct_change(window)
        bench_ret = benchmark.pct_change(window)
        
        # 相对强弱
        rs = (ret - bench_ret) * 100
        
        return rs

    @staticmethod
    def calculate_momentum_rank(
        prices_dict: Dict[str, pd.Series],
        window: int = 20
    ) -> pd.DataFrame:
        """
        计算多指数动量排名
        
        Args:
            prices_dict: {index_key: price_series}
            window: 动量窗口
            
        Returns:
            DataFrame: 每日排名
        """
        momentum = {}
        for key, prices in prices_dict.items():
            momentum[key] = prices.pct_change(window) * 100
        
        df_momentum = pd.DataFrame(momentum)
        
        # 每日排名（1=最强）
        ranks = df_momentum.rank(axis=1, ascending=False)
        
        return ranks

    @staticmethod
    def calculate_sector_rotation_score(
        index_key: str,
        prices_dict: Dict[str, pd.Series],
        window_short: int = 5,
        window_mid: int = 20,
        window_long: int = 60
    ) -> float:
        """
        计算行业轮动得分
        
        综合短期、中期、长期动量排名
        
        Returns:
            轮动得分 (0-100, 越高表示越应该配置)
        """
        if index_key not in prices_dict:
            return 50
        
        scores = []
        weights = [0.5, 0.3, 0.2]  # 短期、中期、长期权重
        
        for window, weight in zip([window_short, window_mid, window_long], weights):
            ranks = MarketRotationIndicators.calculate_momentum_rank(prices_dict, window)
            if index_key in ranks.columns:
                latest_rank = ranks[index_key].iloc[-1]
                # 排名1=最强，转换为得分
                n = len(prices_dict)
                score = (n - latest_rank + 1) / n * 100
                scores.append(score * weight)
        
        return sum(scores) if scores else 50


class EnhancedScoringEngine:
    """增强版评分引擎 - 整合估值百分位和轮动指标"""

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "technical": 0.25,
            "valuation": 0.20,
            "momentum": 0.15,
            "sentiment": 0.10,
            "fundflow": 0.15,
            "rotation": 0.15,
        }
        self.valuation = ValuationIndicators()
        self.rotation = MarketRotationIndicators()

    def calculate_valuation_score_enhanced(
        self,
        row: pd.Series,
        index_key: str,
        close_history: Optional[pd.Series] = None
    ) -> float:
        """计算增强版估值得分"""
        result = self.valuation.calculate_valuation_score(row, index_key, close_history)
        return result["valuation_score"]

    def calculate_rotation_score(
        self,
        index_key: str,
        prices_dict: Dict[str, pd.Series]
    ) -> float:
        """计算轮动得分"""
        return self.rotation.calculate_sector_rotation_score(index_key, prices_dict)

    def calculate_total_score_enhanced(
        self,
        row: pd.Series,
        index_key: str,
        close_history: Optional[pd.Series] = None,
        prices_dict: Optional[Dict[str, pd.Series]] = None
    ) -> Dict[str, float]:
        """
        计算增强版综合评分
        
        Args:
            row: 当前行数据
            index_key: 指数代码
            close_history: 历史收盘价（用于计算百分位）
            prices_dict: 多指数价格字典（用于轮动计算）
            
        Returns:
            综合评分结果
        """
        from engine.scoring import ScoringEngine
        
        base_engine = ScoringEngine(weights=self.weights)
        
        # 基础因子得分
        technical = base_engine.calculate_technical_score(row)
        momentum = base_engine.calculate_momentum_score(row)
        sentiment = base_engine.calculate_sentiment_score(row)
        fundflow = base_engine.calculate_fundflow_score(row)
        
        # 增强版估值得分
        valuation = self.calculate_valuation_score_enhanced(row, index_key, close_history)
        
        # 轮动得分
        rotation = 50  # 默认中性
        if prices_dict is not None:
            rotation = self.calculate_rotation_score(index_key, prices_dict)
        
        # 权重归一化
        weight_sum = sum(self.weights.values())
        if weight_sum > 0:
            normalized_weights = {k: v / weight_sum for k, v in self.weights.items()}
        else:
            normalized_weights = self.weights

        # 加权总分（各因子已经是0-100，直接加权平均）
        total = (
            technical * normalized_weights.get("technical", 0) +
            valuation * normalized_weights.get("valuation", 0) +
            momentum * normalized_weights.get("momentum", 0) +
            sentiment * normalized_weights.get("sentiment", 0) +
            fundflow * normalized_weights.get("fundflow", 0) +
            rotation * normalized_weights.get("rotation", 0)
        )
        
        total = min(max(total, 0), 100)
        
        return {
            "technical": technical,
            "valuation": valuation,
            "momentum": momentum,
            "sentiment": sentiment,
            "fundflow": fundflow,
            "rotation": rotation,
            "total": total,
        }


if __name__ == "__main__":
    # 测试
    import numpy as np
    
    dates = pd.date_range("2020-01-01", "2024-12-31", freq="B")
    np.random.seed(42)
    
    # 生成模拟价格
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.0002, 0.015, len(dates))))
    close = pd.Series(prices, index=dates)
    
    # 测试估值百分位
    valuation = ValuationIndicators()
    pe_pct = valuation.calculate_pe_percentile(close, "kc50")
    
    print("PE百分位测试:")
    print(f"  最新: {pe_pct.iloc[-1]:.1f}%")
    print(f"  历史平均: {pe_pct.mean():.1f}%")
    print(f"  历史最低: {pe_pct.min():.1f}%")
    print(f"  历史最高: {pe_pct.max():.1f}%")
    
    # 测试轮动
    prices_dict = {
        "kc50": close,
        "zxhl": close * 0.8,
        "hldb": close * 1.2,
    }
    
    rotation = MarketRotationIndicators()
    ranks = rotation.calculate_momentum_rank(prices_dict, window=20)
    
    print("\n轮动排名测试:")
    print(ranks.tail())
    
    # 测试增强评分
    enhanced = EnhancedScoringEngine()
    
    row = pd.Series({
        "close": close.iloc[-1],
        "rsi_6": 25,
        "rsi_12": 30,
        "rsi_24": 35,
        "kdj_k": 20,
        "kdj_d": 25,
        "kdj_j": 10,
        "bias_20": -8,
        "bias_60": -15,
        "macd_dif": -1,
        "macd_dea": -2,
        "ma_5": close.iloc[-1] * 0.98,
        "ma_20": close.iloc[-1] * 0.95,
        "ma_60": close.iloc[-1] * 0.90,
        "volatility_20": 25,
        "volume": 1000000,
    })
    
    result = enhanced.calculate_total_score_enhanced(
        row, "kc50", close_history=close, prices_dict=prices_dict
    )
    
    print("\n增强版评分测试:")
    for key, value in result.items():
        print(f"  {key}: {value:.1f}")

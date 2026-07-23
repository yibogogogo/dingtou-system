"""
综合评分引擎 v2.0 - 重新设计版
核心改进：
1. 评分公式更科学：使用sigmoid函数实现平滑过渡
2. 因子独立性更强：各因子评分范围明确
3. 权重影响更合理：权重变化对总分影响线性
4. 支持参数调优：所有阈值可配置
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple


class ScoringEngine:
    """综合评分引擎 v2.0"""

    @staticmethod
    def _safe_get(row: pd.Series, key: str, default: float) -> float:
        """安全获取行数据，处理NaN和缺失键"""
        val = row.get(key, default)
        if val is None or (isinstance(val, (float, np.floating)) and np.isnan(val)):
            return default
        return val

    def __init__(
        self,
        weights: Dict[str, float] = None,
        technical_params: Dict = None,
        valuation_params: Dict = None,
        momentum_params: Dict = None,
        sentiment_params: Dict = None,
        fundflow_params: Dict = None,
    ):
        """
        Args:
            weights: 各因子权重配置
            technical_params: 技术指标参数
            valuation_params: 估值因子参数
            momentum_params: 动量因子参数
            sentiment_params: 情绪因子参数
            fundflow_params: 资金因子参数
        """
        self.weights = weights or {
            "technical": 0.35,
            "valuation": 0.25,
            "momentum": 0.15,
            "sentiment": 0.10,
            "fundflow": 0.15,
        }

        # 技术指标参数（可配置）
        self.technical_params = technical_params or {
            "rsi_oversold": 30,      # RSI超卖阈值
            "rsi_overbought": 70,    # RSI超买阈值
            "kdj_oversold": 20,      # KDJ超卖阈值
            "kdj_overbought": 80,    # KDJ超买阈值
            "bias_extreme": -10,     # BIAS极端偏离
            "macd_weight": 2,        # MACD金叉加分
        }

        # 估值因子参数
        self.valuation_params = valuation_params or {
            "pe_cheap": 15,          # PE便宜阈值
            "pe_expensive": 30,      # PE昂贵阈值
            "pb_cheap": 1.5,         # PB便宜阈值
            "pb_expensive": 3.0,     # PB昂贵阈值
            "dividend_high": 3.5,    # 高股息率
            "dividend_low": 1.5,     # 低股息率
        }

        # 动量因子参数
        self.momentum_params = momentum_params or {
            "short_window": 20,      # 短期窗口
            "mid_window": 60,      # 中期窗口
            "long_window": 120,      # 长期窗口
            "extreme_drop": -15,     # 极端下跌
            "extreme_rise": 15,      # 极端上涨
        }

        # 情绪因子参数
        self.sentiment_params = sentiment_params or {
            "volatility_high": 25,   # 高波动率
            "volatility_low": 10,    # 低波动率
            "turnover_high": 5,      # 高换手率
            "turnover_low": 1,       # 低换手率
        }

        # 资金因子参数
        self.fundflow_params = fundflow_params or {
            "short_window": 5,       # 短期资金窗口
            "mid_window": 20,        # 中期资金窗口
            "extreme_outflow": -10,  # 极端流出
            "extreme_inflow": 10,    # 极端流入
        }

    def _sigmoid_score(self, value: float, center: float, scale: float, 
                       direction: str = "lower_better") -> float:
        """
        使用sigmoid函数计算评分
        
        Args:
            value: 当前值
            center: 中心点（50分位置）
            scale: 缩放因子（越大越平缓）
            direction: "lower_better" 或 "higher_better"
        
        Returns:
            0-100之间的评分
        """
        if direction == "lower_better":
            # 值越低越好（如RSI、下跌幅度）
            score = 100 / (1 + np.exp((value - center) / scale))
        else:
            # 值越高越好（如股息率）
            score = 100 / (1 + np.exp(-(value - center) / scale))
        
        return score

    def _linear_score(self, value: float, min_val: float, max_val: float,
                      direction: str = "lower_better") -> float:
        """
        线性评分函数
        
        Args:
            value: 当前值
            min_val: 最小值（0分）
            max_val: 最大值（100分）
            direction: 方向
        """
        if direction == "lower_better":
            # 值越低越好
            if value <= min_val:
                return 100
            elif value >= max_val:
                return 0
            else:
                return 100 * (max_val - value) / (max_val - min_val)
        else:
            # 值越高越好
            if value <= min_val:
                return 0
            elif value >= max_val:
                return 100
            else:
                return 100 * (value - min_val) / (max_val - min_val)

    def calculate_technical_score(self, row: pd.Series) -> float:
        """
        计算技术指标评分（0-100）
        使用sigmoid函数实现平滑过渡
        """
        scores = []
        params = self.technical_params

        # === RSI 评分 ===
        for col, weight in [("rsi_6", 0.4), ("rsi_12", 0.35), ("rsi_24", 0.25)]:
            rsi = row.get(col, 50)
            # RSI 30为中性，越低越好
            score = self._sigmoid_score(rsi, center=50, scale=15, direction="lower_better")
            scores.append((score, weight))

        # === KDJ 评分 ===
        k = row.get("kdj_k", 50)
        d = row.get("kdj_d", 50)
        j = row.get("kdj_j", 50)

        # K值评分
        k_score = self._sigmoid_score(k, center=50, scale=20, direction="lower_better")
        scores.append((k_score, 0.3))

        # D值评分
        d_score = self._sigmoid_score(d, center=50, scale=20, direction="lower_better")
        scores.append((d_score, 0.25))

        # J值评分（更敏感）
        j_score = self._sigmoid_score(j, center=50, scale=30, direction="lower_better")
        scores.append((j_score, 0.25))

        # KDJ金叉/死叉检测（真正交叉事件，非状态）
        prev_k = row.get("kdj_k_prev", k)
        prev_d = row.get("kdj_d_prev", d)
        golden_cross = prev_k <= prev_d and k > d
        dead_cross = prev_k >= prev_d and k < d
        if golden_cross:
            scores.append((80, 0.2))  # 金叉事件
        elif dead_cross:
            scores.append((40, 0.2))  # 死叉事件
        else:
            scores.append((60, 0.2))  # 中性状态

        # === BIAS 评分 ===
        bias20 = row.get("bias_20", 0)
        bias60 = row.get("bias_60", 0)

        # BIAS越低（负得越多）越好
        bias20_score = self._sigmoid_score(bias20, center=0, scale=8, direction="lower_better")
        scores.append((bias20_score, 0.3))

        bias60_score = self._sigmoid_score(bias60, center=0, scale=12, direction="lower_better")
        scores.append((bias60_score, 0.2))

        # === MACD 评分（平滑过渡，避免跳跃） ===
        dif = row.get("macd_dif", 0)
        dea = row.get("macd_dea", 0)
        macd_hist = row.get("macd_hist", 0)

        # 使用sigmoid平滑过渡：dif-dea > 0 时趋向高分，< 0 时趋向低分
        macd_raw_score = 50 + (dif - dea) * 50 / max(abs(dea) if abs(dea) > 0 else 1, 0.01)
        macd_score = max(0, min(100, macd_raw_score))
        scores.append((macd_score, 0.3))

        # 计算加权平均
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            final_score = sum(s * w for s, w in scores) / total_weight
        else:
            final_score = 50

        return min(max(final_score, 0), 100)

    def calculate_valuation_score(self, row: pd.Series) -> float:
        """
        计算估值因子评分（0-100）
        
        注意：当PE/PB/股息率数据不可用时，使用价格位置作为估值代理
        """
        scores = []
        params = self.valuation_params

        # === PE 评分（如果数据不可用，使用价格代理） ===
        pe = row.get("pe_ttm", None)
        if pe is not None and not np.isnan(pe):
            pe_score = self._linear_score(pe, min_val=params["pe_cheap"], 
                                          max_val=params["pe_expensive"], 
                                          direction="lower_better")
        else:
            # 使用价格位置作为估值代理：价格低于MA60 = 便宜 = 高分
            close = row.get("close", 1000)
            ma60 = row.get("ma_60", close)
            if ma60 > 0:
                proxy = (close - ma60) / ma60 * 100
            else:
                proxy = 0
            pe_score = self._sigmoid_score(proxy, center=0, scale=15, direction="lower_better")
        scores.append((pe_score, 0.3))

        # === PB 评分 ===
        pb = row.get("pb", None)
        if pb is not None and not np.isnan(pb):
            pb_score = self._linear_score(pb, min_val=params["pb_cheap"],
                                          max_val=params["pb_expensive"],
                                          direction="lower_better")
        else:
            # 使用BIAS20作为PB代理
            bias20 = row.get("bias_20", 0)
            pb_score = self._sigmoid_score(bias20, center=0, scale=15, direction="lower_better")
        scores.append((pb_score, 0.25))

        # === 股息率 评分 ===
        dividend = row.get("dividend_yield", None)
        if dividend is not None and not np.isnan(dividend):
            div_score = self._linear_score(dividend, min_val=params["dividend_low"],
                                           max_val=params["dividend_high"],
                                           direction="higher_better")
        else:
            # 使用价格位置代理：价格越低 = 股息率越高
            close = row.get("close", 1000)
            ma20 = row.get("ma_20", close)
            if ma20 > 0:
                proxy_div = 1 - (close - ma20) / ma20  # 价格越低，值越大
            else:
                proxy_div = 1
            div_score = self._sigmoid_score(proxy_div, center=1, scale=0.3, direction="higher_better")
        scores.append((div_score, 0.25))

        # === 价格位置 评分 ===
        close = row.get("close", 1000)
        ma60 = row.get("ma_60", close)
        if ma60 != 0:
            price_position = (close - ma60) / ma60 * 100
        else:
            price_position = 0

        position_score = self._sigmoid_score(price_position, center=0, scale=15, 
                                               direction="lower_better")
        scores.append((position_score, 0.2))

        # 计算加权平均
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            final_score = sum(s * w for s, w in scores) / total_weight
        else:
            final_score = 50

        return min(max(final_score, 0), 100)

    def calculate_momentum_score(self, row: pd.Series) -> float:
        """
        计算动量因子评分（0-100）
        改进：下跌时高分，上涨时低分（反向指标）
        """
        scores = []
        params = self.momentum_params

        close = row.get("close", 1000)
        ma20 = row.get("ma_20", close)
        ma60 = row.get("ma_60", close)

        # === 短期动量 ===
        if ma20 != 0:
            short_return = (close - ma20) / ma20 * 100
        else:
            short_return = 0

        short_score = self._sigmoid_score(short_return, center=0, scale=8, 
                                          direction="lower_better")
        scores.append((short_score, 0.35))

        # === 中期动量 ===
        if ma60 != 0:
            mid_return = (close - ma60) / ma60 * 100
        else:
            mid_return = 0

        mid_score = self._sigmoid_score(mid_return, center=0, scale=12, 
                                        direction="lower_better")
        scores.append((mid_score, 0.35))

        # === 长期动量（使用BIAS60代理）===
        bias60 = row.get("bias_60", 0)
        long_score = self._sigmoid_score(bias60, center=0, scale=15, 
                                         direction="lower_better")
        scores.append((long_score, 0.3))

        # 计算加权平均
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            final_score = sum(s * w for s, w in scores) / total_weight
        else:
            final_score = 50

        return min(max(final_score, 0), 100)

    def calculate_sentiment_score(self, row: pd.Series) -> float:
        """
        计算情绪因子评分（0-100）
        """
        scores = []
        params = self.sentiment_params

        # === RSI情绪 ===
        rsi6 = row.get("rsi_6", 50)
        # RSI 50为中性，越低越恐慌（越好）
        rsi_score = self._sigmoid_score(rsi6, center=50, scale=20, 
                                        direction="lower_better")
        scores.append((rsi_score, 0.4))

        # === 波动率 ===
        vol = row.get("volatility_20", 20)
        # 波动率越高，恐慌越大，得分越高
        vol_score = self._sigmoid_score(vol, center=20, scale=10, 
                                        direction="higher_better")
        scores.append((vol_score, 0.3))

        # === 价格位置 ===
        close = row.get("close", 1000)
        ma60 = row.get("ma_60", close)
        if ma60 != 0:
            price_position = (close - ma60) / ma60 * 100
        else:
            price_position = 0

        position_score = self._sigmoid_score(price_position, center=0, scale=20, 
                                             direction="lower_better")
        scores.append((position_score, 0.3))

        # 计算加权平均
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            final_score = sum(s * w for s, w in scores) / total_weight
        else:
            final_score = 50

        return min(max(final_score, 0), 100)

    def calculate_fundflow_score(self, row: pd.Series) -> float:
        """
        计算资金因子评分（0-100）
        """
        scores = []
        params = self.fundflow_params

        close = row.get("close", 1000)
        ma5 = row.get("ma_5", close)
        ma20 = row.get("ma_20", close)

        # === 短期资金 ===
        if ma5 != 0:
            short_flow = (close - ma5) / ma5 * 100
        else:
            short_flow = 0

        short_score = self._sigmoid_score(short_flow, center=0, scale=5, 
                                          direction="lower_better")
        scores.append((short_score, 0.4))

        # === 中期资金 ===
        if ma20 != 0:
            mid_flow = (close - ma20) / ma20 * 100
        else:
            mid_flow = 0

        mid_score = self._sigmoid_score(mid_flow, center=0, scale=10, 
                                        direction="lower_better")
        scores.append((mid_score, 0.35))

        # === 成交量变化 ===
        volume = row.get("volume", 0)
        volume_ma = row.get("volume_ma20", volume)
        if volume_ma > 0:
            vol_change = (volume - volume_ma) / volume_ma * 100
        else:
            vol_change = 0

        # 放量下跌 = 恐慌 = 高分
        if short_flow < 0:
            vol_score = self._sigmoid_score(vol_change, center=0, scale=50, 
                                            direction="higher_better")
        else:
            vol_score = 50  # 上涨时成交量中性
        
        scores.append((vol_score, 0.25))

        # 计算加权平均
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            final_score = sum(s * w for s, w in scores) / total_weight
        else:
            final_score = 50

        return min(max(final_score, 0), 100)

    def calculate_total_score(self, row: pd.Series) -> Dict[str, float]:
        """
        计算综合评分
        
        改进：
        1. 各因子独立评分（0-100）
        2. 权重直接加权（无需归一化）
        3. 总分 = 加权平均
        """
        technical = self.calculate_technical_score(row)
        valuation = self.calculate_valuation_score(row)
        momentum = self.calculate_momentum_score(row)
        sentiment = self.calculate_sentiment_score(row)
        fundflow = self.calculate_fundflow_score(row)

        # 权重归一化
        weight_sum = sum(self.weights.values())
        if weight_sum > 0:
            normalized_weights = {k: v / weight_sum for k, v in self.weights.items()}
        else:
            normalized_weights = self.weights

        # 计算加权总分（各因子已经是0-100）
        total = (
            technical * normalized_weights.get("technical", 0) +
            valuation * normalized_weights.get("valuation", 0) +
            momentum * normalized_weights.get("momentum", 0) +
            sentiment * normalized_weights.get("sentiment", 0) +
            fundflow * normalized_weights.get("fundflow", 0)
        )

        return {
            "technical": round(technical, 2),
            "valuation": round(valuation, 2),
            "momentum": round(momentum, 2),
            "sentiment": round(sentiment, 2),
            "fundflow": round(fundflow, 2),
            "total": round(total, 2),
        }

    def get_grade(self, score: float) -> str:
        """根据评分获取等级"""
        if score >= 85:
            return "S"
        elif score >= 70:
            return "A"
        elif score >= 55:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"

    def get_multiplier(self, score: float) -> float:
        """根据评分获取定投倍数"""
        if score >= 85:
            return 2.0
        elif score >= 70:
            return 1.5
        elif score >= 55:
            return 1.0
        elif score >= 40:
            return 0.5
        elif score >= 25:
            return 0.25
        else:
            return 0.0

    def get_grade_label(self, score: float) -> str:
        """获取等级标签"""
        if score >= 85:
            return "极度超卖"
        elif score >= 70:
            return "严重超卖"
        elif score >= 55:
            return "中度超卖"
        elif score >= 40:
            return "轻度超卖"
        elif score >= 25:
            return "中性区域"
        else:
            return "偏强区域"


if __name__ == "__main__":
    # 测试新评分引擎
    import numpy as np

    dates = pd.date_range("2024-01-01", "2024-01-31", freq="B")
    np.random.seed(42)
    data = {
        "close": 1000 + np.cumsum(np.random.normal(0, 10, len(dates))),
        "rsi_6": np.random.uniform(10, 90, len(dates)),
        "rsi_12": np.random.uniform(10, 90, len(dates)),
        "rsi_24": np.random.uniform(10, 90, len(dates)),
        "kdj_k": np.random.uniform(0, 100, len(dates)),
        "kdj_d": np.random.uniform(0, 100, len(dates)),
        "kdj_j": np.random.uniform(-20, 120, len(dates)),
        "bias_20": np.random.uniform(-20, 20, len(dates)),
        "bias_60": np.random.uniform(-30, 30, len(dates)),
        "macd_dif": np.random.uniform(-5, 5, len(dates)),
        "macd_dea": np.random.uniform(-5, 5, len(dates)),
        "macd_hist": np.random.uniform(-3, 3, len(dates)),
        "ma_5": 1000 + np.random.normal(0, 5, len(dates)),
        "ma_20": 1000 + np.random.normal(0, 10, len(dates)),
        "ma_60": 1000 + np.random.normal(0, 15, len(dates)),
        "volatility_20": np.random.uniform(10, 30, len(dates)),
        "volume": np.random.randint(1000000, 5000000, len(dates)),
        "volume_ma20": np.random.randint(1000000, 5000000, len(dates)),
        "pe_ttm": np.random.uniform(10, 40, len(dates)),
        "pb": np.random.uniform(1, 5, len(dates)),
        "dividend_yield": np.random.uniform(1, 5, len(dates)),
    }
    df = pd.DataFrame(data, index=dates)

    engine = ScoringEngine()
    result = engine.calculate_total_score(df.iloc[-1])
    print(f"综合评分: {result['total']:.1f}")
    print(f"各因子: {result}")
    print(f"等级: {engine.get_grade(result['total'])}")
    print(f"倍数: {engine.get_multiplier(result['total'])}")
    print(f"标签: {engine.get_grade_label(result['total'])}")

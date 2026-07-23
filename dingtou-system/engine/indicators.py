"""
技术指标计算引擎
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple


class TechnicalIndicators:
    """技术指标计算器"""

    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI相对强弱指数
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 避免除以零，处理gain=loss=0的情况
        rs = pd.Series(np.where(
            loss == 0,
            np.where(gain == 0, 0, np.inf),  # gain=0且loss=0时RS=0 -> RSI=50; gain>0且loss=0时RS=inf -> RSI=100
            gain / loss
        ), index=prices.index)
        
        rsi = 100 - (100 / (1 + rs))
        
        # 处理可能的NaN（前period-1个值）
        rsi = rsi.fillna(50)
        
        return rsi

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算KDJ随机指标

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            n: RSV周期
            m1: K平滑系数
            m2: D平滑系数

        Returns:
            (K, D, J) 三个序列
        """
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()

        # 避免除以零
        denominator = highest_high - lowest_low
        rsv = pd.Series(np.where(denominator == 0, 50, (close - lowest_low) / denominator * 100), index=close.index)
        rsv = rsv.replace([np.inf, -np.inf], 50).fillna(50)

        K = pd.Series(index=close.index, dtype=float)
        D = pd.Series(index=close.index, dtype=float)

        # 找到第一个非NaN的RSV位置（即第n-1个位置，0-indexed）
        first_valid_idx = rsv.first_valid_index()
        if first_valid_idx is None:
            # 所有数据都是NaN，返回全NaN
            return K, D, pd.Series(index=close.index, dtype=float)

        K.loc[first_valid_idx] = 50
        D.loc[first_valid_idx] = 50

        # 从first_valid_idx之后的位置开始迭代
        valid_indices = rsv.loc[first_valid_idx:].index
        for i in range(1, len(valid_indices)):
            idx = valid_indices[i]
            prev_idx = valid_indices[i - 1]
            K.loc[idx] = (2/3) * K.loc[prev_idx] + (1/3) * rsv.loc[idx]
            D.loc[idx] = (2/3) * D.loc[prev_idx] + (1/3) * K.loc[idx]

        J = 3 * K - 2 * D

        return K, D, J

    @staticmethod
    def bias(prices: pd.Series, period: int) -> pd.Series:
        """
        计算BIAS乖离率

        Args:
            prices: 价格序列
            period: 计算周期

        Returns:
            BIAS值序列 (%)
        """
        ma = prices.rolling(window=period).mean()
        bias = np.where(ma != 0, (prices - ma) / ma * 100, 0)
        return pd.Series(bias, index=prices.index)

    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标

        Args:
            prices: 价格序列
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            (DIF, DEA, MACD柱)
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = (dif - dea)  # 标准MACD柱状图，不乘以2

        return dif, dea, macd_hist

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标

        Args:
            df: DataFrame with columns: date, open, high, low, close, volume

        Returns:
            DataFrame with added indicator columns
        """
        result = df.copy()
        close = result["close"]
        high = result["high"]
        low = result["low"]

        # RSI
        result["rsi_6"] = TechnicalIndicators.rsi(close, 6)
        result["rsi_12"] = TechnicalIndicators.rsi(close, 12)
        result["rsi_24"] = TechnicalIndicators.rsi(close, 24)

        # KDJ
        k, d, j = TechnicalIndicators.kdj(high, low, close, 9, 3, 3)
        result["kdj_k"] = k
        result["kdj_d"] = d
        result["kdj_j"] = j
        # 前一日KDJ值（用于金叉/死叉检测）
        result["kdj_k_prev"] = k.shift(1)
        result["kdj_d_prev"] = d.shift(1)

        # BIAS
        result["bias_5"] = TechnicalIndicators.bias(close, 5)
        result["bias_10"] = TechnicalIndicators.bias(close, 10)
        result["bias_20"] = TechnicalIndicators.bias(close, 20)
        result["bias_60"] = TechnicalIndicators.bias(close, 60)

        # MACD
        dif, dea, macd_h = TechnicalIndicators.macd(close, 12, 26, 9)
        result["macd_dif"] = dif
        result["macd_dea"] = dea
        result["macd_hist"] = macd_h

        # 额外指标
        result["ma_5"] = close.rolling(window=5).mean()
        result["ma_10"] = close.rolling(window=10).mean()
        result["ma_20"] = close.rolling(window=20).mean()
        result["ma_60"] = close.rolling(window=60).mean()

        # 成交量均线
        result["volume_ma5"] = result["volume"].rolling(window=5).mean()
        result["volume_ma20"] = result["volume"].rolling(window=20).mean()

        # 波动率
        result["volatility_20"] = close.pct_change().rolling(window=20).std() * np.sqrt(252) * 100

        # 填充所有技术指标的NaN
        indicator_cols = [c for c in result.columns if c not in ["date", "open", "high", "low", "close", "volume", "amount", "amplitude", "pct_change", "change", "turnover"]]
        for col in indicator_cols:
            result[col] = result[col].bfill().ffill().fillna(0)

        return result


class ValuationIndicators:
    """估值指标计算器（简化版）"""

    @staticmethod
    def estimate_pe(close: pd.Series, base_pe: float = 15.0) -> pd.Series:
        """
        估算PE（基于价格变动比例）

        Args:
            close: 收盘价序列
            base_pe: 基准PE

        Returns:
            估算PE序列
        """
        # 简化：假设价格与PE成正比
        price_ratio = close / close.iloc[0] if len(close) > 0 else 1.0
        return base_pe * price_ratio

    @staticmethod
    def estimate_pb(close: pd.Series, base_pb: float = 1.0) -> pd.Series:
        """估算PB"""
        price_ratio = close / close.iloc[0] if len(close) > 0 else 1.0
        return base_pb * price_ratio

    @staticmethod
    def estimate_dividend_yield(close: pd.Series, base_yield: float = 4.0) -> pd.Series:
        """估算股息率（价格越低，股息率越高）"""
        price_ratio = close / close.iloc[0] if len(close) > 0 else 1.0
        return base_yield / price_ratio


if __name__ == "__main__":
    # 测试
    import numpy as np

    dates = pd.date_range("2024-01-01", "2024-12-31", freq="B")
    np.random.seed(42)
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, len(dates))))

    df = pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, len(dates)),
    })

    result = TechnicalIndicators.calculate_all(df)
    print(result[["date", "close", "rsi_6", "kdj_k", "kdj_d", "bias_20", "macd_dif"]].tail())

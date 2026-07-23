"""
数据获取模块 - 增强版
支持多种数据源：
1. akshare（优先）
2. 中证指数官网 (CSIndex)
3. East Money K-line API（备用）
4. 模拟数据（兜底）
"""
import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import requests
import json

warnings.filterwarnings("ignore")

try:
    import akshare as ak
except ImportError:
    ak = None
    print("警告: akshare未安装，将使用备用数据源")


class DataFetcher:
    """数据获取器 - 支持多数据源"""

    def __init__(self, use_proxy: bool = False, proxy_url: str = "http://127.0.0.1:7890"):
        """
        Args:
            use_proxy: 是否使用代理
            proxy_url: 代理地址
        """
        self.indices = {
            "kc50": {"name": "科创50", "code": "000688", "csindex_code": "000688"},
            "zxhl": {"name": "中证红利", "code": "000922", "csindex_code": "000922"},
            "hldb": {"name": "红利低波", "code": "H30269", "csindex_code": "H30269"},
        }
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        
        # 设置代理（仅在请求时使用，不修改全局环境变量）
        self.proxies = {"http": proxy_url, "https": proxy_url} if use_proxy else None

    def fetch_index_history(
        self,
        symbol: str,
        start_date: str = "20190101",
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取指数历史日线数据（多数据源回退）

        Args:
            symbol: 指数代码 (如 "000688")
            start_date: 起始日期 (格式: YYYYMMDD)
            end_date: 结束日期 (格式: YYYYMMDD)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 尝试1: akshare
        try:
            df = self._fetch_from_akshare(symbol, start_date, end_date)
            if df is not None and not df.empty:
                print(f"[OK] 从akshare获取 {symbol} 数据成功")
                return df
        except Exception as e:
            print(f"[!] akshare获取 {symbol} 失败: {e}")

        # 尝试2: 中证指数官网
        try:
            df = self._fetch_from_csindex(symbol, start_date, end_date)
            if df is not None and not df.empty:
                print(f"[OK] 从中证指数获取 {symbol} 数据成功")
                return df
        except Exception as e:
            print(f"[!] 中证指数获取 {symbol} 失败: {e}")

        # 尝试3: East Money K-line API
        try:
            df = self._fetch_from_eastmoney(symbol, start_date, end_date)
            if df is not None and not df.empty:
                print(f"[OK] 从East Money获取 {symbol} 数据成功")
                return df
        except Exception as e:
            print(f"[!] East Money获取 {symbol} 失败: {e}")

        # 兜底: 模拟数据
        print(f"[MOCK] 使用模拟数据 for {symbol}")
        return self._generate_mock_data(symbol, start_date, end_date)

    def _fetch_from_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取数据"""
        if ak is None:
            return None

        df = ak.index_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
        )

        if df is None or df.empty:
            return None

        # 标准化列名
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "换手率": "turnover",
            }
        )

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        return df

    def _fetch_from_csindex(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从中证指数官网获取数据
        API: http://www.csindex.com.cn/zh-CN/indices/index-detail/{code}
        """
        try:
            # 中证指数API
            url = f"http://www.csindex.com.cn/zh-CN/indices/index-detail/{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "http://www.csindex.com.cn/",
            }
            
            response = requests.get(url, headers=headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            
            # 中证指数的HTML页面包含历史数据
            # 由于页面结构复杂，这里尝试解析JSON数据
            # 如果失败，返回None让下一个数据源尝试
            
            # 尝试从页面中提取数据（简化版）
            html = response.text
            
            # 查找历史数据JSON
            import re
            json_match = re.search(r'"historicalData":\s*(\[[^\]]*\])', html)
            if json_match:
                data = json.loads(json_match.group(1))
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                return df
            
            return None
            
        except Exception as e:
            print(f"中证指数获取失败: {e}")
            return None

    def _fetch_from_eastmoney(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从East Money K-line API获取数据
        注意：此API可能有反爬虫限制
        """
        try:
            # East Money K-line API
            # secid: 0=深圳, 1=上海
            # 中证指数（000xxx, H开头）使用上海前缀
            if symbol.startswith(("6", "000", "H")):
                secid = f"1.{symbol}"
            else:
                secid = f"0.{symbol}"
            
            url = (
                f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
                f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
                f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
                f"&klt=101&fqt=1&beg={start_date}&end={end_date}&_=0"
            )
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
                "Referer": "https://quote.eastmoney.com/",
            }
            
            response = requests.get(url, headers=headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                
                # 解析K线数据
                records = []
                for line in klines:
                    parts = line.split(",")
                    if len(parts) >= 6:
                        records.append({
                            "date": parts[0],
                            "open": float(parts[1]),
                            "close": float(parts[2]),
                            "high": float(parts[3]),
                            "low": float(parts[4]),
                            "volume": float(parts[5]),
                            "amount": float(parts[6]) if len(parts) > 6 else 0,
                        })
                
                if records:
                    df = pd.DataFrame(records)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)
                    return df
            
            return None
            
        except Exception as e:
            print(f"East Money获取失败: {e}")
            return None

    def fetch_all_indices(
        self,
        start_date: str = "20190101",
        end_date: Optional[str] = None,
    ) -> dict:
        """
        获取所有指数数据

        Returns:
            dict: {index_key: DataFrame}
        """
        data = {}
        for key, info in self.indices.items():
            print(f"\n正在获取 {info['name']}({info['code']}) 数据...")
            df = self.fetch_index_history(info["code"], start_date, end_date)
            data[key] = df
            print(f"  获取到 {len(df)} 条记录")
        return data

    def fetch_realtime(self, symbol: str) -> dict:
        """
        获取实时行情

        Returns:
            dict: 最新价格信息
        """
        try:
            if ak is None:
                return {"price": 0, "change_pct": 0, "change": 0, "volume": 0, "amount": 0}

            # 获取实时行情
            df = ak.index_zh_a_spot_em()
            
            # 查找对应指数
            if df is not None and not df.empty:
                # 尝试匹配指数代码
                match = df[df["代码"] == symbol]
                if not match.empty:
                    row = match.iloc[0]
                    return {
                        "price": float(row.get("最新价", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                    }
            
            return {"price": 0, "change_pct": 0, "change": 0, "volume": 0, "amount": 0}
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return {"price": 0, "change_pct": 0, "change": 0, "volume": 0, "amount": 0}

    def _generate_mock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """生成模拟数据（用于测试）"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) if end_date else pd.to_datetime("today")

        # 生成交易日
        dates = pd.date_range(start=start, end=end, freq="B")  # 工作日

        # 使用确定性种子（避免PYTHONHASHSEED导致不可重复）
        import hashlib
        seed = int(hashlib.md5(symbol.encode("utf-8")).hexdigest()[:8], 16)
        np.random.seed(seed)

        # 生成价格序列（随机游走）
        n = len(dates)
        returns = np.random.normal(0.0005, 0.02, n)  # 日收益率
        prices = 1000 * np.exp(np.cumsum(returns))

        # 生成OHLC
        df = pd.DataFrame({
            "date": dates,
            "open": prices * (1 + np.random.normal(0, 0.005, n)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, n),
            "amount": np.random.randint(100000000, 1000000000, n),
            "amplitude": np.random.uniform(0.5, 3.0, n),
            "pct_change": returns * 100,
            "change": prices * returns,
            "turnover": np.random.uniform(0.5, 5.0, n),
        })

        # 确保 high >= close >= low
        df["high"] = np.maximum(df["high"], df[["open", "close"]].max(axis=1))
        df["low"] = np.minimum(df["low"], df[["open", "close"]].min(axis=1))

        return df


if __name__ == "__main__":
    # 测试 - 不使用代理
    fetcher = DataFetcher(use_proxy=False)
    data = fetcher.fetch_all_indices(start_date="20240101")
    for key, df in data.items():
        print(f"\n{key}:")
        print(df.tail())

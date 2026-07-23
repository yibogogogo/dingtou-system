"""
数据缓存管理模块
"""
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


class DataCache:
    """数据缓存管理器"""

    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, index_key: str, suffix: str = ".parquet") -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{index_key}{suffix}"

    def _get_meta_path(self, index_key: str) -> Path:
        """获取元数据文件路径"""
        return self.cache_dir / f"{index_key}_meta.pkl"

    def save(self, index_key: str, df: pd.DataFrame) -> None:
        """保存数据到缓存"""
        cache_path = self._get_cache_path(index_key)
        meta_path = self._get_meta_path(index_key)

        # 保存数据
        df.to_parquet(cache_path, index=False)

        # 保存元数据
        meta = {
            "last_update": datetime.now().isoformat(),
            "records": len(df),
            "start_date": df["date"].min().isoformat() if "date" in df.columns else None,
            "end_date": df["date"].max().isoformat() if "date" in df.columns else None,
        }
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)

        print(f"缓存已保存: {index_key} ({len(df)} 条记录)")

    def load(self, index_key: str) -> pd.DataFrame:
        """从缓存加载数据"""
        cache_path = self._get_cache_path(index_key)

        if not cache_path.exists():
            raise FileNotFoundError(f"缓存不存在: {index_key}")

        df = pd.read_parquet(cache_path)
        print(f"从缓存加载: {index_key} ({len(df)} 条记录)")
        return df

    def exists(self, index_key: str) -> bool:
        """检查缓存是否存在"""
        return self._get_cache_path(index_key).exists()

    def get_meta(self, index_key: str) -> dict:
        """获取缓存元数据"""
        meta_path = self._get_meta_path(index_key)
        if meta_path.exists():
            with open(meta_path, "rb") as f:
                return pickle.load(f)
        return {}

    def is_stale(self, index_key: str, max_age_days: int = 1) -> bool:
        """检查缓存是否过期"""
        meta = self.get_meta(index_key)
        if not meta:
            return True

        last_update = datetime.fromisoformat(meta["last_update"])
        age = datetime.now() - last_update
        return age.days > max_age_days

    def get_last_date(self, index_key: str) -> datetime:
        """获取缓存数据的最后日期"""
        meta = self.get_meta(index_key)
        if meta and meta.get("end_date"):
            return datetime.fromisoformat(meta["end_date"])
        return datetime(2019, 1, 1)

    def list_cached(self) -> list:
        """列出所有已缓存的指数"""
        cached = []
        for f in self.cache_dir.glob("*.parquet"):
            key = f.stem
            meta = self.get_meta(key)
            cached.append({
                "key": key,
                "records": meta.get("records", 0),
                "last_update": meta.get("last_update", "unknown"),
            })
        return cached

    def clear(self, index_key: str = None) -> None:
        """清除缓存"""
        if index_key:
            for ext in [".parquet", "_meta.pkl"]:
                path = self._get_cache_path(index_key, ext)
                if path.exists():
                    path.unlink()
            print(f"已清除缓存: {index_key}")
        else:
            # 只删除缓存文件，不删除目录本身
            for f in self.cache_dir.glob("*.parquet"):
                f.unlink()
            for f in self.cache_dir.glob("*_meta.pkl"):
                f.unlink()
            print("已清除所有缓存")


if __name__ == "__main__":
    cache = DataCache()
    print("已缓存的指数:")
    for item in cache.list_cached():
        print(f"  {item}")

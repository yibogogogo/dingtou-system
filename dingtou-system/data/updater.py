"""
数据更新模块 - 每日增量更新
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from data.fetcher import DataFetcher
from data.cache import DataCache


class DataUpdater:
    """数据更新器"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.cache = DataCache()

    def update_index(self, index_key: str) -> bool:
        """
        更新单个指数数据

        Returns:
            bool: 是否成功更新
        """
        try:
            info = self.fetcher.indices[index_key]
            print(f"\n更新 {info['name']}({info['code']})...")

            # 检查缓存
            if self.cache.exists(index_key):
                last_date = self.cache.get_last_date(index_key)
                start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
                print(f"  缓存最后日期: {last_date.strftime('%Y-%m-%d')}")
                print(f"  增量更新起始: {start_date}")

                # 获取新数据
                new_data = self.fetcher.fetch_index_history(
                    info["code"],
                    start_date=start_date,
                )

                if len(new_data) > 0:
                    # 合并数据
                    old_data = self.cache.load(index_key)
                    combined = pd.concat([old_data, new_data], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["date"], keep="last")
                    combined = combined.sort_values("date").reset_index(drop=True)

                    self.cache.save(index_key, combined)
                    print(f"  更新完成: 新增 {len(new_data)} 条记录")
                else:
                    print("  无新数据")
            else:
                # 首次获取
                print("  首次获取全量数据...")
                data = self.fetcher.fetch_index_history(
                    info["code"],
                    start_date="20190101",
                )
                self.cache.save(index_key, data)
                print(f"  获取完成: {len(data)} 条记录")

            return True

        except Exception as e:
            print(f"  更新失败: {e}")
            return False

    def update_all(self) -> dict:
        """更新所有指数数据"""
        results = {}
        for key in self.fetcher.indices.keys():
            results[key] = self.update_index(key)
        return results

    def check_status(self) -> dict:
        """检查数据状态"""
        status = {}
        for key in self.fetcher.indices.keys():
            if self.cache.exists(key):
                meta = self.cache.get_meta(key)
                status[key] = {
                    "cached": True,
                    "records": meta.get("records", 0),
                    "last_update": meta.get("last_update", "unknown"),
                    "stale": self.cache.is_stale(key),
                }
            else:
                status[key] = {"cached": False}
        return status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据更新工具")
    parser.add_argument("--init", action="store_true", help="初始化所有数据")
    parser.add_argument("--status", action="store_true", help="查看数据状态")
    parser.add_argument("--index", type=str, help="指定指数更新")

    args = parser.parse_args()
    updater = DataUpdater()

    if args.status:
        status = updater.check_status()
        for key, info in status.items():
            print(f"\n{key}:")
            for k, v in info.items():
                print(f"  {k}: {v}")
    elif args.init:
        print("初始化所有数据...")
        updater.update_all()
    elif args.index:
        updater.update_index(args.index)
    else:
        print("使用 --init 初始化数据 或 --status 查看状态")

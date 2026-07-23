"""
历史信号验证与优化引擎

核心逻辑：
1. 在历史数据上计算每日评分
2. 分析不同评分等级对应的未来收益表现
3. 基于历史表现优化评分阈值
4. 验证信号的有效性
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.scoring import ScoringEngine
from engine.indicators import TechnicalIndicators


class HistoricalSignalValidator:
    """历史信号验证器"""
    
    def __init__(self, data_dict: Dict[str, pd.DataFrame], weights: Dict[str, float]):
        """
        Args:
            data_dict: 历史数据字典 {index_key: DataFrame}
            weights: 评分权重
        """
        self.data_dict = data_dict
        self.weights = weights
        self.scoring_engine = ScoringEngine(weights=weights)
        
        # 存储历史评分
        self.historical_scores = {}
        
        # 存储验证结果
        self.validation_results = {}
        
    def calculate_historical_scores(self, index_key: str) -> pd.DataFrame:
        """
        计算历史每日评分
        
        Returns:
            DataFrame with columns: date, score, grade, close, future_return_1d, future_return_5d, future_return_20d
        """
        df = self.data_dict[index_key].copy()
        
        scores = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            try:
                score_result = self.scoring_engine.calculate_total_score(row)
                scores.append({
                    'date': row['date'],
                    'score': score_result['total'],
                    'close': row['close'],
                })
            except:
                scores.append({
                    'date': row['date'],
                    'score': 50,
                    'close': row['close'],
                })
        
        scores_df = pd.DataFrame(scores)
        
        # 计算未来收益
        scores_df['future_return_1d'] = scores_df['close'].shift(-1) / scores_df['close'] - 1
        scores_df['future_return_5d'] = scores_df['close'].shift(-5) / scores_df['close'] - 1
        scores_df['future_return_20d'] = scores_df['close'].shift(-20) / scores_df['close'] - 1
        
        # 计算等级
        scores_df['grade'] = scores_df['score'].apply(self._get_grade)
        
        return scores_df
    
    def _get_grade(self, score: float) -> str:
        """根据评分获取等级"""
        if score >= 85:
            return 'S'
        elif score >= 70:
            return 'A'
        elif score >= 55:
            return 'B'
        elif score >= 40:
            return 'C'
        elif score >= 25:
            return 'D'
        else:
            return 'F'
    
    def analyze_grade_performance(self, scores_df: pd.DataFrame) -> Dict:
        """
        分析不同评分等级的历史表现
        
        Returns:
            dict: 各等级的收益统计
        """
        results = {}
        
        for grade in ['S', 'A', 'B', 'C', 'D', 'F']:
            grade_data = scores_df[scores_df['grade'] == grade]
            
            if len(grade_data) == 0:
                continue
            
            results[grade] = {
                'count': len(grade_data),
                'avg_score': grade_data['score'].mean(),
                'avg_return_1d': grade_data['future_return_1d'].mean() * 100,
                'avg_return_5d': grade_data['future_return_5d'].mean() * 100,
                'avg_return_20d': grade_data['future_return_20d'].mean() * 100,
                'win_rate_1d': (grade_data['future_return_1d'] > 0).mean() * 100,
                'win_rate_5d': (grade_data['future_return_5d'] > 0).mean() * 100,
                'win_rate_20d': (grade_data['future_return_20d'] > 0).mean() * 100,
                'max_return_1d': grade_data['future_return_1d'].max() * 100,
                'min_return_1d': grade_data['future_return_1d'].min() * 100,
                'std_return_1d': grade_data['future_return_1d'].std() * 100,
            }
        
        return results
    
    def optimize_thresholds(self, scores_df: pd.DataFrame) -> Dict:
        """
        基于历史表现优化评分阈值
        
        优化目标：
        1. 最大化高评分等级的平均收益
        2. 最大化高评分等级的胜率
        3. 确保信号数量合理
        
        Returns:
            dict: 优化后的阈值
        """
        best_thresholds = {}
        
        # 测试不同的阈值组合
        thresholds_to_test = []
        
        # S级阈值：80-95
        for s_threshold in range(80, 96, 5):
            # A级阈值：65-80
            for a_threshold in range(65, 81, 5):
                if a_threshold >= s_threshold:
                    continue
                # B级阈值：50-65
                for b_threshold in range(50, 66, 5):
                    if b_threshold >= a_threshold:
                        continue
                    # C级阈值：35-50
                    for c_threshold in range(35, 51, 5):
                        if c_threshold >= b_threshold:
                            continue
                        
                        thresholds_to_test.append({
                            'S': s_threshold,
                            'A': a_threshold,
                            'B': b_threshold,
                            'C': c_threshold,
                            'D': 25,
                        })
        
        best_score = -np.inf
        best_threshold = None
        
        for thresholds in thresholds_to_test:
            # 应用阈值
            scores_df['temp_grade'] = scores_df['score'].apply(
                lambda x: self._get_grade_with_thresholds(x, thresholds)
            )
            
            # 计算综合评分
            total_score = 0
            
            for grade in ['S', 'A', 'B']:
                grade_data = scores_df[scores_df['temp_grade'] == grade]
                if len(grade_data) > 0:
                    # 高评分等级应该有正收益
                    avg_return = grade_data['future_return_5d'].mean()
                    win_rate = (grade_data['future_return_5d'] > 0).mean()
                    count = len(grade_data)
                    
                    # 综合评分：收益 * 胜率 * 数量权重
                    total_score += avg_return * win_rate * min(count / 10, 1)
            
            if total_score > best_score:
                best_score = total_score
                best_threshold = thresholds
        
        return best_threshold if best_threshold else {'S': 85, 'A': 70, 'B': 55, 'C': 40, 'D': 25}
    
    def _get_grade_with_thresholds(self, score: float, thresholds: Dict) -> str:
        """根据自定义阈值获取等级"""
        if score >= thresholds['S']:
            return 'S'
        elif score >= thresholds['A']:
            return 'A'
        elif score >= thresholds['B']:
            return 'B'
        elif score >= thresholds['C']:
            return 'C'
        elif score >= thresholds['D']:
            return 'D'
        else:
            return 'F'
    
    def validate_signals(self, index_key: str) -> Dict:
        """
        验证信号在历史数据中的有效性（带训练/测试集划分，避免过拟合）
        
        Returns:
            dict: 验证结果
        """
        # 计算历史评分
        scores_df = self.calculate_historical_scores(index_key)
        
        # 按时间划分训练集（前50%）和测试集（后50%）
        split_idx = len(scores_df) // 2
        train_df = scores_df.iloc[:split_idx].copy()
        test_df = scores_df.iloc[split_idx:].copy()
        
        # 在训练集上优化阈值
        optimized_thresholds = self.optimize_thresholds(train_df)
        
        # 在测试集上评估优化后的阈值
        test_df['optimized_grade'] = test_df['score'].apply(
            lambda x: self._get_grade_with_thresholds(x, optimized_thresholds)
        )
        
        # 计算优化后的表现（使用测试集）
        original_analysis = self.analyze_grade_performance(test_df)
        
        # 使用优化阈值后的表现
        optimized_performance = {}
        for grade in ['S', 'A', 'B', 'C', 'D', 'F']:
            grade_data = test_df[test_df['optimized_grade'] == grade]
            if len(grade_data) == 0:
                continue
            optimized_performance[grade] = {
                'count': len(grade_data),
                'avg_score': grade_data['score'].mean(),
                'avg_return_1d': grade_data['future_return_1d'].mean() * 100,
                'avg_return_5d': grade_data['future_return_5d'].mean() * 100,
                'avg_return_20d': grade_data['future_return_20d'].mean() * 100,
                'win_rate_1d': (grade_data['future_return_1d'] > 0).mean() * 100,
                'win_rate_5d': (grade_data['future_return_5d'] > 0).mean() * 100,
                'win_rate_20d': (grade_data['future_return_20d'] > 0).mean() * 100,
                'max_return_1d': grade_data['future_return_1d'].max() * 100,
                'min_return_1d': grade_data['future_return_1d'].min() * 100,
                'std_return_1d': grade_data['future_return_1d'].std() * 100,
            }
        
        return {
            'index_key': index_key,
            'total_days': len(scores_df),
            'train_days': len(train_df),
            'test_days': len(test_df),
            'grade_performance': original_analysis,
            'optimized_thresholds': optimized_thresholds,
            'optimized_performance': optimized_performance,
            'scores_df': scores_df,
        }
    
    def generate_validated_signals(self, index_key: str, current_date: datetime = None) -> Dict:
        """
        生成经过历史验证的信号
        
        Args:
            index_key: 指数代码
            current_date: 当前日期
            
        Returns:
            dict: 验证后的信号
        """
        if current_date is None:
            current_date = datetime.now()
        
        # 验证信号
        validation = self.validate_signals(index_key)
        
        # 获取当前评分
        df = self.data_dict[index_key]
        latest = df[df['date'] <= current_date].iloc[-1]
        
        try:
            score_result = self.scoring_engine.calculate_total_score(latest)
            current_score = score_result['total']
        except:
            current_score = 50
        
        # 使用优化后的阈值
        optimized_thresholds = validation['optimized_thresholds']
        current_grade = self._get_grade_with_thresholds(current_score, optimized_thresholds)
        
        # 获取该等级的历史表现
        grade_perf = validation['optimized_performance'].get(current_grade, {})
        
        return {
            'index_key': index_key,
            'date': current_date.strftime('%Y-%m-%d'),
            'current_score': current_score,
            'current_grade': current_grade,
            'optimized_thresholds': optimized_thresholds,
            'historical_performance': grade_perf,
            'validation': validation,
        }


def main():
    """测试历史信号验证"""
    
    # 加载数据
    data_dict = {}
    for key, file in [('kc50', '../000688perf科创50.xlsx'), 
                       ('zxhl', '../000922perf中证红利.xlsx'), 
                       ('hldb', '../H30269perf红利低波.xlsx')]:
        df = pd.read_excel(file)
        columns = df.columns.tolist()
        if len(columns) < 13:
            print(f"ERROR: {file} 格式异常，仅有{len(columns)}列")
            continue
        # 按文件名中的指数代码过滤
        import re
        code_match = re.match(r'([A-Z0-9]+)', os.path.basename(file).split('perf')[0])
        if code_match:
            raw_code = code_match.group(1)
            correct_code = raw_code.lstrip('0') or '0'
            code_col = columns[1]
            df[code_col] = df[code_col].astype(str)
            before = len(df)
            df = df[df[code_col] == correct_code].copy()
            print(f"{file}: 过滤前{before}行→过滤后{len(df)}行 (指数代码={correct_code})")
        df['date'] = pd.to_datetime(df[columns[0]].astype(str))
        df['close'] = df[columns[9]]
        df['open'] = df[columns[6]].fillna(df['close'])
        df['high'] = df[columns[7]].fillna(df['close'])
        df['low'] = df[columns[8]].fillna(df['close'])
        df['volume'] = df[columns[12]].fillna(0)
        df = TechnicalIndicators.calculate_all(df)
        data_dict[key] = df
    
    # 权重
    weights = {
        'technical': 0.157,
        'valuation': 0.345,
        'momentum': 0.170,
        'sentiment': 0.162,
        'fundflow': 0.166,
    }
    
    # 验证信号
    validator = HistoricalSignalValidator(data_dict, weights)
    
    for key in data_dict.keys():
        print(f"\n{'='*80}")
        print(f"验证 {key} 的信号")
        print(f"{'='*80}")
        
        result = validator.validate_signals(key)
        
        print(f"\n总天数: {result['total_days']}")
        print(f"\n原始等级表现:")
        for grade, perf in result['grade_performance'].items():
            print(f"  {grade}级: 数量={perf['count']}, 平均5日收益={perf['avg_return_5d']:.2f}%, 胜率={perf['win_rate_5d']:.1f}%")
        
        print(f"\n优化后的阈值: {result['optimized_thresholds']}")
        print(f"\n优化后等级表现:")
        for grade, perf in result['optimized_performance'].items():
            print(f"  {grade}级: 数量={perf['count']}, 平均5日收益={perf['avg_return_5d']:.2f}%, 胜率={perf['win_rate_5d']:.1f}%")
        
        # 生成验证后的信号
        validated_signal = validator.generate_validated_signals(key)
        print(f"\n当前验证后的信号:")
        print(f"  评分: {validated_signal['current_score']:.1f}")
        print(f"  等级: {validated_signal['current_grade']}")
        print(f"  历史表现: {validated_signal['historical_performance']}")


if __name__ == "__main__":
    main()

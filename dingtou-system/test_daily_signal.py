from engine.daily_signal import DailySignalEngine

engine = DailySignalEngine(base_amount=2000)

# 测试不同评分
for score in [90, 75, 60, 45, 30, 15]:
    signal = engine.get_signal(score)
    print(f'Score: {score} -> Grade: {signal["grade"]}, Signal: {signal["signal_type"]}, Amount: {signal["amount"]:.0f}')

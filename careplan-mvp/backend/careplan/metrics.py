from prometheus_client import Counter, Histogram
# 定义指标（在文件顶部，模块级别）
careplan_generated_total = Counter(
    'careplan_generated_total',
    'Total care plans generated',
    ['status']  # 标签：success / failed
)

careplan_duration_seconds = Histogram(
    'careplan_duration_seconds',
    'Time spent generating care plan',
    buckets=[5, 10, 20, 30, 60, 120]
)
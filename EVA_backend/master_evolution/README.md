# EVA 主控进化与记忆系统开发文档

## 模块简介

- **user_info_manager.py**：用户信息管理，支持异步存储、提取、自动分类、消息提取。
- **memory_summary.py**：记忆归纳总结，异步调用大模型自动聚类、标签提取。
- **behavior_adapt.py**：行为自适应，根据画像动态调整对话风格和推荐策略。
- **master_improvement.py**：自我优化，自动发现画像空白并生成补全问题。
- **tasks.py**：定时任务，自动批量归纳记忆、更新画像、行为自适应。

## 主要接口说明

### 用户信息管理
```python
from master_evolution.user_info_manager import UserInfoManager
import asyncio

manager = UserInfoManager()
asyncio.run(manager.save_user_info({"name": "小明", "age": 18}))
info = asyncio.run(manager.get_user_info())
```

### 记忆归纳总结
```python
from master_evolution.memory_summary import MemorySummary
class DummyLLM:
    async def generate(self, x):
        return {"content": "兴趣: 篮球\n习惯: 早起\n"}
summary = MemorySummary(DummyLLM())
result = asyncio.run(summary.summarize_memories(["我喜欢篮球", "我每天早起"]))
print(result)
```

### 行为自适应
```python
from master_evolution.behavior_adapt import BehaviorAdapt
profile = {"tags": ["简洁", "友好"]}
adapt = BehaviorAdapt()
strategy = adapt.get_behavior_strategy(profile)
print(strategy)
```

## 常见问题
- **如何扩展用户信息字段？**
  只需修改 user_info_config/info_categories.json 和 extraction_patterns.json，无需改动代码。
- **如何处理异步接口超时？**
  所有异步接口已内置超时处理，超时会自动记录日志并返回默认值。
- **如何批量处理用户？**
  定时任务支持传入用户ID列表，自动批量归纳和更新。

## 测试
- 推荐使用 pytest 运行 tests/memory_test/test_memory_system.py，覆盖正常、边界、异常场景。

---
如有更多问题，请查阅源码注释或联系开发团队。 
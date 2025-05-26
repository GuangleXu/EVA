"""Second-Me集成模块

该模块提供EVA系统与Second-Me系统之间的适配层，
使EVA可以使用Second-Me的高级记忆功能。
"""

import os
import sys

# 自动适配 Second-Me 目录在 EVA_backend 下的情况
CURRENT_DIR = os.path.dirname(__file__)
EVA_BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', '..'))
SECOND_ME_PATH = os.path.join(EVA_BACKEND_DIR, 'Second-Me')

if SECOND_ME_PATH not in sys.path:
    sys.path.append(SECOND_ME_PATH)

# 确保 Second-Me 的 lpm_kernel 路径也被添加到 sys.path
LPM_KERNEL_PATH = os.path.join(SECOND_ME_PATH, 'lpm_kernel')
if LPM_KERNEL_PATH not in sys.path:
    sys.path.append(LPM_KERNEL_PATH)

__all__ = ['memory_adapter', 'rule_adapter', 'working_memory_adapter'] 
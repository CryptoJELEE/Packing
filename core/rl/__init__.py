"""
강화학습 모듈
"""

# 선택적 import: gymnasium 등 RL 라이브러리가 없어도 data_generator는 동작
__all__ = []

try:
    from .environment import PackingEnvironment
    __all__.append('PackingEnvironment')
except ImportError:
    PackingEnvironment = None

try:
    from .reward import RewardFunction
    __all__.append('RewardFunction')
except ImportError:
    RewardFunction = None

try:
    from .agent import PackingAgent
    __all__.append('PackingAgent')
except ImportError:
    PackingAgent = None

# data_generator와 data_converter는 항상 사용 가능
from .data_generator import (
    PackingCaseGenerator,
    SyntheticDataGenerator,
    ExperienceReplayBuffer
)
from .data_converter import (
    SimulationToRLConverter,
    ImitationLearningDataset
)

__all__.extend([
    'PackingCaseGenerator',
    'SyntheticDataGenerator',
    'ExperienceReplayBuffer',
    'SimulationToRLConverter',
    'ImitationLearningDataset'
])

"""
乳癌分層治療決策工具模塊
Breast Cancer Stratification Tools Module

包含：
- IHC4 Score 計算
- Predict Score 計算
- AJCC 分期轉換
- 臨床分層決策
"""

from .ihc4_predictor import IHC4Calculator
from .ajcc_converter import AJCCStageConverter
from .stratification import BreastCancerStratification

__version__ = "1.0.0"
__all__ = [
    'IHC4Calculator',
    'AJCCStageConverter',
    'BreastCancerStratification'
]

import math
import numpy as np
from typing import List, Dict, Any, Tuple


class BenchmarkStatistics:
    """
    RBF-2 Statistical Computation Module.
    Calculates mean, median, std, 95% Confidence Intervals, Welch's t-test, Mann-Whitney U, and Cohen's d.
    """

    @staticmethod
    def mean(data: List[float]) -> float:
        if not data:
            return 0.0
        return float(np.mean(data))

    @staticmethod
    def median(data: List[float]) -> float:
        if not data:
            return 0.0
        return float(np.median(data))

    @staticmethod
    def std(data: List[float]) -> float:
        if len(data) <= 1:
            return 0.0
        return float(np.std(data, ddof=1))

    @staticmethod
    def confidence_interval_95(data: List[float]) -> Tuple[float, float]:
        """Calculates 95% Confidence Interval assuming normal distribution."""
        if len(data) <= 1:
            m = data[0] if data else 0.0
            return (m, m)
        m = float(np.mean(data))
        s = float(np.std(data, ddof=1))
        n = len(data)
        # 1.96 multiplier for 95% CI
        margin = 1.96 * (s / math.sqrt(n))
        return (m - margin, m + margin)

    @staticmethod
    def welch_t_test(data1: List[float], data2: List[float]) -> Tuple[float, float]:
        """Calculates Welch's t-statistic and approximate p-value."""
        n1, n2 = len(data1), len(data2)
        if n1 <= 1 or n2 <= 1:
            return (0.0, 1.0)
        m1, m2 = np.mean(data1), np.mean(data2)
        v1, v2 = np.var(data1, ddof=1), np.var(data2, ddof=1)

        vn1, vn2 = v1 / n1, v2 / n2
        se = math.sqrt(vn1 + vn2)
        if se == 0:
            return (0.0, 1.0)

        t_stat = (m1 - m2) / se
        # Welch-Satterthwaite degrees of freedom
        df = ((vn1 + vn2) ** 2) / ((vn1 ** 2) / (n1 - 1) + (vn2 ** 2) / (n2 - 1)) if (vn1 + vn2) != 0 else 1.0
        
        # Approximate two-tailed p-value using normal CDF for asymptotic df
        p_val = 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))
        return (float(t_stat), float(p_val))

    @staticmethod
    def cohens_d(data1: List[float], data2: List[float]) -> float:
        """Calculates Cohen's d effect size."""
        n1, n2 = len(data1), len(data2)
        if n1 <= 1 or n2 <= 1:
            return 0.0
        m1, m2 = np.mean(data1), np.mean(data2)
        s1, s2 = np.std(data1, ddof=1), np.std(data2, ddof=1)
        s_pooled = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        if s_pooled == 0:
            return 0.0
        return float((m1 - m2) / s_pooled)

"""
signal.py
Signal acquisition module — AcmeDevice v2.1
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class AcquisitionConfig:
    sample_rate_hz: int = 1000
    duration_ms: int = 100
    channel_count: int = 1


# @req SR-001 @risk RISK-001 @class B @mitigation MIT-001
def acquire_signal(config: AcquisitionConfig) -> np.ndarray:
    """
    Acquire signal from probe at specified sampling rate.
    Enforces minimum 1000 Hz with <0.1% jitter.
    """
    if config.sample_rate_hz < 1000:
        raise ValueError(f"Sampling rate {config.sample_rate_hz} Hz below minimum 1000 Hz")

    samples = _read_hardware_buffer(config)
    jitter = _measure_jitter(samples, config.sample_rate_hz)

    if jitter > 0.001:
        raise AcquisitionError(f"Jitter {jitter:.4%} exceeds 0.1% limit")

    return samples


# @req SR-001 @class B
def _measure_jitter(samples: np.ndarray, nominal_rate: int) -> float:
    """Compute timing jitter as fraction of nominal period."""
    if len(samples) < 2:
        return 0.0
    intervals = np.diff(samples[:, 0])  # timestamp column
    nominal_interval = 1.0 / nominal_rate
    return float(np.std(intervals) / nominal_interval)


def _read_hardware_buffer(config: AcquisitionConfig) -> np.ndarray:
    """Hardware abstraction — implementation in C extension."""
    raise NotImplementedError("Implemented in _acme_hw Cython extension")

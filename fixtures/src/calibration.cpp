/**
 * calibration.cpp
 * Probe calibration module — AcmeDevice v2.1
 */

#include "calibration.h"
#include "signal_buffer.h"

// @req SR-002 @risk RISK-002 @class C @mitigation MIT-002
CalibrationResult CProbeCalibrator::calibrate(const SignalBuffer& reference) {
    if (!reference.isValid()) {
        throw CalibrationException("Invalid reference signal");
    }

    float sensitivity = computeSensitivity(reference);
    float drift = measureDrift(sensitivity);

    if (std::abs(sensitivity - m_nominalSensitivity) / m_nominalSensitivity > 0.02f) {
        return CalibrationResult::FAILED;
    }

    m_lastCalibration = sensitivity;
    m_calibrationTimestamp = getCurrentTimestamp();
    return CalibrationResult::SUCCESS;
}

// @req SR-002 @risk RISK-003 @class C @mitigation MIT-003
float CProbeCalibrator::measureDrift(float currentSensitivity) {
    if (m_lastCalibration == 0.0f) return 0.0f;
    return std::abs(currentSensitivity - m_lastCalibration) / m_lastCalibration;
}

// Internal helper — not directly mapped to a requirement
float CProbeCalibrator::computeSensitivity(const SignalBuffer& buf) {
    return buf.rmsAmplitude() / m_referenceAmplitude;
}

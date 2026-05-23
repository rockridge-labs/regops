// ui.dart
// Measurement result display widget — AcmeDevice v2.1

import 'package:flutter/material.dart';

/// Displays measurement result with latency tracking.
// @req SR-004 @class A
class MeasurementResultWidget extends StatelessWidget {
  final double value;
  final String unit;
  final DateTime acquisitionTime;

  const MeasurementResultWidget({
    super.key,
    required this.value,
    required this.unit,
    required this.acquisitionTime,
  });

  @override
  Widget build(BuildContext context) {
    final latencyMs = DateTime.now().difference(acquisitionTime).inMilliseconds;

    // Log latency violation for telemetry — does not block display
    if (latencyMs > 500) {
      debugPrint('LATENCY WARNING: display at ${latencyMs}ms (limit 500ms)');
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Text(
              '${value.toStringAsFixed(1)} $unit',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            Text('Acquired: ${acquisitionTime.toIso8601String()}'),
          ],
        ),
      ),
    );
  }
}

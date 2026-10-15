#pragma once
// Build only against a pinned, verified TFLM toolchain; no desktop Flex fallback.
#ifdef LIGHTNING_WITH_TFLM
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace lightning {
class MicroInference {
  tflite::MicroInterpreter& interpreter_;
public:
  explicit MicroInference(tflite::MicroInterpreter& interpreter) : interpreter_(interpreter) {}
  bool prepare() { return interpreter_.AllocateTensors() == kTfLiteOk; }
  bool predict(const float* values, std::size_t count, float& risk_score) {
    if (interpreter_.Reset() != kTfLiteOk) return false;
    auto* input = interpreter_.input(0);
    if (!input) return false;
    const auto expected = input->type == kTfLiteFloat32 ? input->bytes / sizeof(float) : input->bytes;
    if (count != expected) return false;
    if (input->type == kTfLiteFloat32) {
      for (std::size_t i = 0; i < count; ++i) {
        if (!std::isfinite(values[i])) return false;
        input->data.f[i] = values[i];
      }
    } else if (input->type == kTfLiteInt8 && input->params.scale > 0) {
      for (std::size_t i = 0; i < count; ++i) {
        if (!std::isfinite(values[i])) return false;
        auto q = std::round(values[i] / input->params.scale) + input->params.zero_point;
        input->data.int8[i] = static_cast<std::int8_t>(q < -128 ? -128 : q > 127 ? 127 : q);
      }
    } else return false;
    if (interpreter_.Invoke() != kTfLiteOk) return false;
    auto* output = interpreter_.output(0);
    if (output->type == kTfLiteFloat32 && output->bytes == sizeof(float)) risk_score = output->data.f[0];
    else if (output->type == kTfLiteInt8 && output->bytes == 1)
      risk_score = (output->data.int8[0] - output->params.zero_point) * output->params.scale;
    else return false;
    return std::isfinite(risk_score) && risk_score >= 0 && risk_score <= 1;
  }
};
}  // namespace lightning
#endif

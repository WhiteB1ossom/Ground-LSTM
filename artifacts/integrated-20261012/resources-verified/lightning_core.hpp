#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace lightning {
template <std::size_t Capacity, std::size_t Features> class Ring {
  std::array<std::array<float, Features>, Capacity> data_{};
  std::array<std::int64_t, Capacity> stamps_{};
  std::array<bool, Capacity> valid_{};
  std::size_t head_ = 0, size_ = 0;
public:
  bool append(std::int64_t timestamp, const std::array<float, Features>& values, bool valid) {
    if (timestamp < 0) return false;
    if (size_ && timestamp <= stamps_[(head_ + Capacity - 1) % Capacity]) return false;
    for (float x : values) if (!std::isfinite(x)) return false;
    data_[head_] = values; stamps_[head_] = timestamp; valid_[head_] = valid;
    head_ = (head_ + 1) % Capacity; if (size_ < Capacity) ++size_;
    return true;
  }
  void clear() { head_ = size_ = 0; }
  std::size_t size() const { return size_; }
  template <std::size_t Length> bool latest(float* output, std::int64_t period_ns) const {
    static_assert(Length <= Capacity, "Sequence exceeds ring");
    if (size_ < Length) return false;
    for (std::size_t i = 0; i < Length; ++i) {
      const auto slot = (head_ + Capacity - Length + i) % Capacity;
      if (!valid_[slot]) return false;
      if (i) {
        const auto previous = (slot + Capacity - 1) % Capacity;
        if (stamps_[slot] - stamps_[previous] != period_ns) return false;
      }
      for (std::size_t j = 0; j < Features; ++j) output[i * Features + j] = data_[slot][j];
    }
    return true;
  }
};

struct DecisionResult { bool available; bool alarm; int transition; };
class Decision {
  double on_, off_; unsigned required_, count_ = 0; bool active_ = false;
public:
  Decision(double on, double off, unsigned required) : on_(on), off_(off), required_(required) {}
  DecisionResult update(double score, bool available) {
    if (!available || !std::isfinite(score) || score < 0 || score > 1) {
      count_ = 0; return {false, active_, 0};
    }
    int transition = 0;
    if (active_ && score < off_) { active_ = false; transition = -1; }
    else if (!active_) {
      count_ = score >= on_ ? count_ + 1 : 0;
      if (count_ >= required_) { active_ = true; count_ = 0; transition = 1; }
    }
    return {true, active_, transition};
  }
};

// The adapter supplies sparse observations. 0=absent, 1=valid, 2=invalid.
template <std::size_t Sensors> class CausalCurrent {
  std::array<double, Sensors> values_{};
  std::array<std::int64_t, Sensors> observed_{};
  std::array<bool, Sensors> present_{}, good_{};
  std::int64_t last_update_ = -1;
  mutable std::int64_t last_sample_ = -1;
public:
  bool update(std::int64_t timestamp, const std::array<double, Sensors>& values,
              const std::array<int, Sensors>& modes, bool healthy = true) {
    if (timestamp < 0 || timestamp <= last_update_ || timestamp <= last_sample_) return false;
    for (int mode : modes) if (mode < 0 || mode > 2) return false;
    last_update_ = timestamp;
    for (std::size_t i = 0; i < Sensors; ++i) {
      if (!healthy || modes[i] != 0) {
        observed_[i] = timestamp; present_[i] = true;
        good_[i] = healthy && modes[i] == 1 && std::isfinite(values[i]);
        values_[i] = values[i];
      }
    }
    return true;
  }
  template <std::size_t Features> bool features(
      std::int64_t timestamp, const std::array<double, Sensors>& stale,
      const std::array<bool, Sensors>& critical,
      const std::array<double, Features>& fill, const std::array<double, Features>& offset,
      const std::array<double, Features>& scale, std::array<float, Features>& output) const {
    static_assert(Features == 3 * Sensors, "Current/missing/age contract required");
    if (timestamp < last_update_ || timestamp <= last_sample_) return false;
    last_sample_ = timestamp;
    bool valid = true;
    for (std::size_t i = 0; i < Sensors; ++i) {
      const double age = present_[i] ? static_cast<double>(timestamp - observed_[i]) / 1e9 : NAN;
      const bool missing = !present_[i] || !good_[i] || age < 0 || age >= stale[i];
      if (missing && critical[i]) valid = false;
      const double raw[3] = {missing ? NAN : values_[i], missing ? 1.0 : 0.0, age};
      for (std::size_t k = 0; k < 3; ++k) {
        const auto j = i + k * Sensors;
        const double x = std::isfinite(raw[k]) ? raw[k] : fill[j];
        output[j] = static_cast<float>((x - offset[j]) / scale[j]);
        if (!std::isfinite(output[j])) return false;
      }
    }
    return valid;
  }
};

// Board-specific readers and safety hardware remain explicit external adapters.
class HardwareActuator {
public:
  virtual ~HardwareActuator() = default;
  virtual bool advisory_only() const = 0;
};
class AdvisoryActuator final : public HardwareActuator {
public: bool advisory_only() const override { return true; }
};
}  // namespace lightning

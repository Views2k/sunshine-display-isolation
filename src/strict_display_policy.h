#pragma once

#include <chrono>
#include <string>
#include <string_view>
#include <vector>

namespace video::display_selection {
  inline bool pin_mapped_output(const std::string &mapped_output, std::vector<std::string> &names, int &index) {
    names.clear();
    index = -1;
    if (mapped_output.empty()) {
      return false;
    }
    names.emplace_back(mapped_output);
    index = 0;
    return true;
  }

  inline bool binding_matches(std::string_view mapped_output, std::string_view captured_output) {
    return !mapped_output.empty() && mapped_output == captured_output;
  }

  class recovery_budget {
  public:
    using clock = std::chrono::steady_clock;

    explicit recovery_budget(bool configured, clock::time_point started = clock::now()):
        bounded_(configured),
        deadline_(started + std::chrono::seconds(10)) {}

    bool expired(clock::time_point now = clock::now()) const {
      return bounded_ && now >= deadline_;
    }

  private:
    bool bounded_;
    clock::time_point deadline_;
  };
}

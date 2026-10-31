#include "strict_display_policy.h"

#include <algorithm>
#include <iostream>
#include <stdexcept>

namespace {
  void require(bool condition, const char *message) {
    if (!condition) {
      throw std::runtime_error(message);
    }
  }
}

int main() {
  using namespace video::display_selection;
  using namespace std::chrono_literals;

  try {
    std::vector<std::string> outputs {"physical", "old-virtual"};
    int index = 1;
    require(!pin_mapped_output("", outputs, index), "Missing identity must fail");
    require(outputs.empty() && index == -1, "Missing identity must discard stale output and index");

    require(pin_mapped_output("virtual-A", outputs, index), "Present identity must resolve");
    require(outputs == std::vector<std::string> {"virtual-A"} && index == 0, "Only the configured output may be selectable");
    for (int requested : {-100, 0, 1, 100}) {
      require(outputs[std::clamp(requested, 0, static_cast<int>(outputs.size()) - 1)] == "virtual-A", "Display switching must not escape the configured output");
    }

    require(pin_mapped_output("virtual-renumbered", outputs, index), "Renumbered identity must resolve again");
    require(outputs.front() == "virtual-renumbered", "Old GDI name must not override the new mapping");
    require(!binding_matches("virtual-renumbered", "virtual-A"), "Reused old GDI name must be rejected");
    require(!binding_matches("", "physical"), "Missing identity must not capture the primary output");
    require(!binding_matches("", ""), "Two empty names must not grant capture");
    require(!binding_matches("virtual-A", "virtual-B"), "Different identities must fail regardless of image dimensions");
    require(binding_matches("virtual-A", "virtual-A"), "Matching output must remain usable");

    require(!pin_mapped_output("", outputs, index), "Removal must fail even after a previous success");
    require(pin_mapped_output("returned-virtual", outputs, index), "Reappearance must use the current mapping");
    require(outputs.front() == "returned-virtual", "Reappearance must not restore the stale output");

    std::vector<std::string> other_outputs;
    int other_index = -1;
    require(pin_mapped_output("another-instance", other_outputs, other_index), "Second instance must resolve independently");
    require(outputs.front() == "returned-virtual", "One instance must not change another instance's selection");

    const auto start = recovery_budget::clock::time_point {};
    recovery_budget bounded(true, start);
    require(!bounded.expired(start + 9999ms), "Transient recovery must remain available inside its budget");
    require(bounded.expired(start + 10s), "Recovery retries must stop at the deadline");
    require(bounded.expired(start + 1h), "Repeated failures must not reset the deadline");
    recovery_budget legacy(false, start);
    require(!legacy.expired(start + 1h), "Unconfigured output behavior must retain its existing retry policy");

    std::cout << "Display selection regression checks passed\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}

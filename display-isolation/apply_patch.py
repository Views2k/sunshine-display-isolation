from pathlib import Path
import subprocess
import sys


UPSTREAM = "63d35f702ee9e362e43263742981836ec0710384"


def replace_once(text, old, new):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one source anchor, found {count}: {old[:100]!r}")
    return text.replace(old, new, 1)


def prepare(root):
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != UPSTREAM:
        raise RuntimeError("The source checkout does not match the reviewed upstream revision")
    dirty = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True)
    if dirty.strip():
        raise RuntimeError("The upstream checkout contains tracked changes")

    video_path = root / "src/video.cpp"
    windows_path = root / "src/platform/windows/display_base.cpp"
    video = video_path.read_text(encoding="utf-8")
    windows = windows_path.read_text(encoding="utf-8")
    video = replace_once(video, '#include "display_device.h"', '#include "display_device.h"\n#include "strict_display_policy.h"')
    windows = replace_once(windows, '#include "src/display_device.h"', '#include "src/display_device.h"\n#include "src/strict_display_policy.h"')

    begin = video.index("  void refresh_displays(")
    end = video.index("\n  /**\n   * @brief Run the shared display capture thread", begin)
    original_refresh = video[begin:end]
    refresh = original_refresh.replace("  void refresh_displays(", "  bool refresh_displays(", 1)
    refresh = refresh.replace("return;", "return true;")
    refresh = replace_once(
        refresh,
        "    const auto output_name {display_device::map_output_name(config::video.output_name)};",
        """    const auto output_name {display_device::map_output_name(config::video.output_name)};
    if (strict_output_configured()) {
      // Resolve the configured identity again on every recovery. Probe only this output.
      return display_selection::pin_mapped_output(output_name, display_names, current_display_index);
    }""",
    )
    if not refresh.endswith("  }\n"):
        raise RuntimeError("Unexpected display refresh function boundary")
    refresh = refresh[:-4] + "    return true;\n  }\n"
    strict_configuration = """  bool strict_output_configured() {
#ifdef _WIN32
    return !config::video.output_name.empty();
#else
    return false;
#endif
  }

"""
    comment_begin = video.rfind("  /**", 0, begin)
    if comment_begin < 0:
        raise RuntimeError("Missing display refresh documentation boundary")
    video = video[:comment_begin] + strict_configuration + video[comment_begin:begin] + refresh + video[end:]

    call = "refresh_displays(encoder.platform_formats->dev_type, display_names, display_p);"
    video = replace_once(
        video,
        "    " + call + "\n    auto disp = platf::display",
        """    if (!refresh_displays(encoder.platform_formats->dev_type, display_names, display_p)) {
      BOOST_LOG(error) << "Configured display is unavailable; capture was not started";
      return;
    }
    auto disp = platf::display""",
    )
    video = replace_once(
        video,
        """            while (capture_ctx_queue->running()) {
              // Release the display before reenumerating displays""",
        """            const display_selection::recovery_budget retry_budget {strict_output_configured()};
            while (capture_ctx_queue->running()) {
              if (capture_ctxs.empty() || retry_budget.expired()) {
                BOOST_LOG(error) << "Display recovery ended without an available configured output";
                return;
              }
              // Release the display before reenumerating displays""",
    )
    video = replace_once(
        video,
        "              " + call,
        """              if (!refresh_displays(encoder.platform_formats->dev_type, display_names, display_p)) {
                std::this_thread::sleep_for(200ms);
                continue;
              }""",
    )
    video = replace_once(
        video,
        """    while (encode_session_ctx_queue.running()) {
      // Refresh display names since a display removal might have caused the reinitialization
      """ + call,
        """    const display_selection::recovery_budget retry_budget {strict_output_configured()};
    while (encode_session_ctx_queue.running()) {
      if (retry_budget.expired()) {
        BOOST_LOG(error) << "Display recovery ended without an available configured output";
        return encode_e::error;
      }
      // Refresh display names since a display removal might have caused the reinitialization
      if (!refresh_displays(encoder.platform_formats->dev_type, display_names, display_p)) {
        std::this_thread::sleep_for(200ms);
        continue;
      }""",
    )
    if video.count("if (!refresh_displays(") != 3:
        raise RuntimeError("Every capture caller must handle an unavailable configured output")

    windows = replace_once(
        windows,
        "  capture_e display_base_t::capture(",
        """  namespace {
    bool output_matches_configuration(output_t &output) {
      if (config::video.output_name.empty()) {
        return true;
      }
      DXGI_OUTPUT_DESC desc {};
      if (!output || FAILED(output->GetDesc(&desc))) {
        return false;
      }
      return ::video::display_selection::binding_matches(
        display_device::map_output_name(config::video.output_name),
        utf_utils::to_utf8(desc.DeviceName)
      );
    }
  }

  capture_e display_base_t::capture(""",
    )
    windows = replace_once(
        windows,
        """    auto adjust_client_frame_rate = [&]() -> DXGI_RATIONAL {""",
        """    // Check the bound output again after backend initialization, before delivering frames.
    if (!output_matches_configuration(output)) {
      return capture_e::reinit;
    }
    auto adjust_client_frame_rate = [&]() -> DXGI_RATIONAL {""",
    )
    windows = replace_once(
        windows,
        """  int display_base_t::init(const ::video::config_t &config, const std::string &display_name) {
    std::once_flag windows_cpp_once_flag;""",
        """  int display_base_t::init(const ::video::config_t &config, const std::string &display_name) {
    if (!config::video.output_name.empty() &&
        !::video::display_selection::binding_matches(display_device::map_output_name(config::video.output_name), display_name)) {
      return -1;
    }
    std::once_flag windows_cpp_once_flag;""",
    )
    windows = replace_once(
        windows,
        """    if (!output) {
      BOOST_LOG(error) << "Failed to locate an output device"sv;
      return -1;
    }

    D3D_FEATURE_LEVEL featureLevels[] {""",
        """    if (!output) {
      BOOST_LOG(error) << "Failed to locate an output device"sv;
      return -1;
    }
    if (!output_matches_configuration(output)) {
      BOOST_LOG(error) << "Configured display changed during capture initialization";
      return -1;
    }

    D3D_FEATURE_LEVEL featureLevels[] {""",
    )
    return {
        video_path: video,
        windows_path: windows,
        root / "src/strict_display_policy.h": (Path(__file__).parent / "strict_display_policy.h").read_text(encoding="utf-8"),
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    edits = prepare(root)
    for path, content in edits.items():
        path.write_text(content, encoding="utf-8", newline="\n")
        print(path.relative_to(root).as_posix())

# Sunshine display isolation

A Windows fork of [Sunshine](https://github.com/LizardByte/Sunshine) that keeps each stream bound to its configured display.

Sunshine is developed by LizardByte and its contributors. Views2k maintains the display-isolation changes in this fork.

## What changed

When a display is configured, capture checks its identity during startup and recovery. After a desktop transition, it resolves that display again before resuming capture. Separate Sunshine instances retain their own configured targets.

The changes were made on October 30, 2026, against Sunshine revision `63d35f702ee9e362e43263742981836ec0710384`.

## Windows setup

1. Start with [Sunshine 2026.914.233613](https://github.com/LizardByte/Sunshine/releases/tag/v2026.914.233613) and configure the display to stream in its web interface.
2. Download the Windows update ZIP from [Releases](https://github.com/Views2k/sunshine-display-isolation/releases).
3. Stop the Sunshine instance being updated and back up its `sunshine.exe` and `zlib1.dll`.
4. Extract those two files into that instance's Sunshine folder, then start Sunshine and reconnect Moonlight.

For multiple instances, repeat the update for each instance. Keep each instance's existing configuration, pairing data, and assets.

See the [Sunshine documentation](https://docs.lizardbyte.dev/projects/sunshine/) for initial setup and configuration.

## Build and tests

The [Windows workflow](.github/workflows/build-windows.yml) records the dependencies and build commands. It compiles the display-selection tests, builds Sunshine, runs the existing display-configuration tests, checks runtime dependencies, and scans the resulting files.

The `display-isolation` directory contains the reviewed patch, its policy tests, and source verification. The patch is already applied to the source tree on this branch.

## License and credit

Distributed under [GPL-3.0](LICENSE). Upstream copyright and third-party notices are retained. See [NOTICE.md](NOTICE.md) for the changes maintained here.

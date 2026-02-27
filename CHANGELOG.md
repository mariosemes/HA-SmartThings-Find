# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2026-02-27

### Fixed
- **Location updates were silently breaking after the first HA polling cycle.**
  `async_add_listener()` returns an unsubscribe callable; it was incorrectly assigned
  to `self.async_update`, meaning the first time Home Assistant called `async_update`
  it accidentally unsubscribed the coordinator listener and stopped all location updates.
- **Battery sensors never subscribed to coordinator updates** and could show stale data
  independently of the location update cycle.
- **`get_device_location` returned `None` on exception** instead of a failure dict, causing
  `TypeError` crashes in entity property accessors (`available`, `latitude`, `state`, etc.)
  when a device fetch failed mid-cycle.
- **`extra_state_attributes` mutated live coordinator data** by writing `last_seen` directly
  into the shared dict, which could affect other entities reading the same device's data
  in the same cycle.
- Platform setup was wrapped in `async_create_task`, meaning failures during entity setup
  were silently swallowed and not propagated to the config entry.

### Improved
- **Parallel device fetching** via `asyncio.gather()` — all devices are now fetched
  concurrently instead of sequentially. On a 15-device setup this cuts the coordinator
  update time from ~15 seconds down to ~1-2 seconds.
- `DeviceTrackerEntity` and `DeviceBatterySensor` now both extend `CoordinatorEntity`,
  the canonical Home Assistant base for coordinator-backed entities. This correctly handles
  listener registration, cleanup on entity removal, and disables HA's redundant polling.
- Sub-device location (`get_sub_location`) is now computed once per coordinator cycle in
  `_handle_coordinator_update` and cached, rather than being re-evaluated separately for
  each of the four properties that needed it (`latitude`, `longitude`, `location_accuracy`,
  `extra_state_attributes`).
- Battery sensor now uses `native_value` and `_attr_native_unit_of_measurement` instead
  of the deprecated `state` / `unit_of_measurement` property pattern.
- Removed a redundant inner `if 'latitude' in op:` check inside a block already guarded
  by the same condition, along with an unreachable "no coordinates found" warning.

## [0.2.2] - 2025-01-01

### Fixed
- Use a dedicated `aiohttp` session with a browser User-Agent per config entry to prevent
  Samsung's servers from rejecting requests and to isolate cookie jars between entries.

## [0.2.1] - 2024-12-01

### Changed
- Forked from the original archived [Vedeneb/HA-SmartThings-Find](https://github.com/Vedeneb/HA-SmartThings-Find) project.
- Updated repository URLs and ownership to [@mariosemes](https://github.com/mariosemes).
- Replaced QR-code login with OAuth2 + manual JSESSIONID paste flow.

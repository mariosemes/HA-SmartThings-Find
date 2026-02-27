# SmartThings Find — Home Assistant Integration

<p align="center">
  <img src="media/screenshot_1.png" alt="SmartThings Find in Home Assistant" width="600"/>
</p>

<p align="center">
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/releases"><img src="https://img.shields.io/badge/version-0.2.3-blue" alt="Version"></a>
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/actions/workflows/validate.yaml"><img src="https://github.com/mariosemes/HA-SmartThings-Find/actions/workflows/validate.yaml/badge.svg" alt="HACS Validation"></a>
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange" alt="HACS: Custom"></a>
</p>

Track and manage your Samsung SmartTags and Samsung devices — phones, tablets, watches, and earbuds — directly from Home Assistant using the [SmartThings Find](https://smartthingsfind.samsung.com/) service.

> **🍴 Fork Notice** — This is a maintained fork of the original [Vedeneb/HA-SmartThings-Find](https://github.com/Vedeneb/HA-SmartThings-Find) project, which has been archived by its author. A huge thank you to **Vedeneb** for the original concept, the reverse-engineering work, and the solid foundation this project builds on.

---

## Features

For each registered Samsung device, the integration creates:

| Entity | Description |
|--------|-------------|
| `device_tracker` | GPS location with accuracy |
| `sensor` | Battery level *(SmartTags only; not supported for earbuds)* |
| `button` | Remotely ring the device |

**Notes:**
- Physical button presses on a SmartTag are **not** supported. Other integrations can handle that.
- Stopping a ring is **not** yet implemented (the SmartThings Find website API has limited support for this).

---

## Installation

### HACS (recommended)

Click the button below to add this repository directly to HACS, or manually add `https://github.com/mariosemes/HA-SmartThings-Find` as a custom integration repository.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mariosemes&repository=HA-SmartThings-Find&category=integration)

1. Search for **SmartThings Find** in HACS and install
2. Restart Home Assistant
3. Follow the [Setup](#setup) steps below

### Manual

1. Copy the `custom_components/smartthings_find` directory into your HA configuration directory
2. Restart Home Assistant
3. Follow the [Setup](#setup) steps below

---

## Setup

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smartthings_find)

Or go to **Settings → Devices & Services → Add Integration** and search for **SmartThings Find** *(do not confuse with the built-in SmartThings integration)*.

**Steps:**

1. Click the login link shown in the setup form — Samsung's login page will open in your browser
2. Sign in with your Samsung account
3. Once redirected to SmartThings Find, press **F12** to open DevTools
4. Go to **Application → Cookies → `https://smartthingsfind.samsung.com`**
5. Copy the value of the **`JSESSIONID`** cookie and paste it into the setup form
6. The integration validates the session and completes setup automatically

---

## Authentication & Session Lifetime

The integration uses Samsung's OAuth2 login flow. The `JSESSIONID` cookie is a one-time setup step — no credentials are stored.

The setup wizard records when the session was created so you can track its age under:
**Settings → Devices & Services → SmartThings Find → Download Diagnostics**

Community experience suggests sessions last **at least several weeks**, though Samsung does not officially document the expiry. When a session expires, Home Assistant will show a **persistent notification** — clicking it lets you paste a fresh `JSESSIONID` in under a minute, with no reinstall needed.

---

## Active vs. Passive Mode

| Mode | Behaviour | Battery impact |
|------|-----------|----------------|
| **Active** | Sends a location update request to the device before fetching | Higher |
| **Passive** | Fetches the last known location already stored in STF | Lower |

**Defaults:** Active mode is **on** for SmartTags, **off** for all other devices.

You can toggle per device type and adjust the update interval (default: **120 seconds**) under **Settings → Devices & Services → SmartThings Find → Configure**.

---

## Connectivity Notes

Ringing a SmartTag requires a Galaxy phone/tablet nearby to relay the command over Bluetooth. Without a nearby device, the ring request will silently fail — the location will still update if any Galaxy device is in range.

If ringing does not work from Home Assistant, test it on the [SmartThings Find website](https://smartthingsfind.samsung.com/) first. If it does not work there either, it is a network/proximity issue, not an integration bug. Note that the SmartThings **mobile app** uses a different backend than the website — always test on the website.

---

## Debugging

Add the following to `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.smartthings_find: debug
```

On each startup, the log will include the current session age:
```
Session age: 12d 3h (authenticated at 2026-02-13 08:51 UTC)
```

---

## ⚠️ Disclaimer

- **Unofficial API** — built by reverse-engineering the SmartThings Find web service. It may stop working if Samsung changes their backend.
- **Limited testing** — if you encounter issues, please [open an issue](https://github.com/mariosemes/HA-SmartThings-Find/issues).
- This project is not affiliated with or endorsed by Samsung or SmartThings.

---

## Roadmap

- [x] HACS support
- [x] Multiple Samsung accounts (multiple config entries)
- [x] Session age tracking via diagnostics
- [ ] Service call to ring a device
- [ ] Service call to stop ringing (for devices that support it)

---

## Contributing

Contributions are welcome — feel free to open issues or submit pull requests. See [CHANGELOG.md](CHANGELOG.md) for recent changes.

## License

MIT — see [LICENSE](LICENSE) for details.

# SmartThings Find — Home Assistant Integration

> ## DEPRECATED — 2026-03-31
>
> **This integration is deprecated due to breaking changes in Samsung's Find service.**
>
> In early 2026, Samsung completely rebuilt their SmartThings Find / Samsung Find platform. The old backend (`smartthingsfind.samsung.com`) with its long-lived session cookies has been replaced by a new REST API (`api.samsungfind.com`) that uses **JWT tokens with a 1-hour expiry and no refresh mechanism**.
>
> This means:
> - **Authentication expires every hour.** There is no way to automatically renew the token — Samsung deliberately does not provide a refresh token, a silent OAuth flow, or any other renewal mechanism. We investigated every possible approach (SSO cookies, SmartThings API bridge, Samsung Account SDK, OpenID Connect `prompt=none`, headless browser automation) and confirmed that Samsung's architecture makes long-lived sessions impossible.
> - **Re-authentication requires browser DevTools.** Users must open the Samsung Find website, open DevTools, and copy header values from the Network tab. This is not a reasonable experience for most Home Assistant users.
> - **Samsung can break this integration at any time.** The API is undocumented and was reverse-engineered from the Samsung Find web application. Samsung has no obligation to maintain compatibility.
>
> **The integration still works** — it just requires re-authentication roughly every hour. If you're comfortable with that workflow, you can continue using it. But we cannot recommend it for unattended operation and will not be actively developing new features.
>
> If Samsung introduces a proper OAuth2 flow with refresh tokens, or if the SmartThings API adds location data for SmartTags, this deprecation will be reconsidered.

<p align="left">
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/releases"><img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version"></a>
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/actions/workflows/validate.yaml"><img src="https://github.com/mariosemes/HA-SmartThings-Find/actions/workflows/validate.yaml/badge.svg" alt="HACS Validation"></a>
  <a href="https://github.com/mariosemes/HA-SmartThings-Find/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange" alt="HACS: Custom"></a>
</p>

Track and manage your Samsung SmartTags and Samsung devices — phones, tablets, watches, and earbuds — directly from Home Assistant using the [Samsung Find](https://samsungfind.samsung.com/) service.

> **Fork Notice** — This is a maintained fork of the original [Vedeneb/HA-SmartThings-Find](https://github.com/Vedeneb/HA-SmartThings-Find) project, which has been archived by its author.

---

## Features

For each registered Samsung device, the integration creates:

| Entity | Description |
|--------|-------------|
| `device_tracker` | GPS location with accuracy |
| `sensor` | Battery level |
| `button` | Remotely ring the device |

---

## Installation

### HACS (recommended)

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

Go to **Settings > Devices & Services > Add Integration** and search for **SmartThings Find**.

**Steps:**

1. Open [samsungfind.samsung.com](https://samsungfind.samsung.com/) in your browser and sign in with your Samsung account
2. Once the map loads with your devices, press **F12** to open DevTools
3. Go to the **Network** tab
4. Click on any device on the map (this triggers API requests)
5. Find any request to `api.samsungfind.com` and click on it
6. In **Request Headers**, copy these values:
   - `x-sec-sa-authtoken` — paste into the **Auth Token** field
   - `x-sec-sa-userid` — paste into the **User ID** field
   - `x-sec-sa-countrycode` — paste into the **Country Code** field
7. Click Submit — the integration validates the token and discovers your devices

---

## Authentication Limitations

Samsung's new Find API (launched early 2026) uses JWT tokens that **expire after 1 hour** with **no refresh mechanism**. This is a fundamental limitation of Samsung's architecture — not a bug in this integration.

When your token expires:
1. Home Assistant will show a **persistent notification** asking you to re-authenticate
2. Click the notification to open the re-authentication form
3. Follow the [Setup](#setup) steps again to paste a fresh token

We investigated every possible approach to extend token lifetime:
- Samsung SSO cookies do not enable silent OAuth renewal (Samsung requires interactive login)
- The SmartThings API does not expose location data for SmartTags
- SmartThings Personal Access Tokens (PATs) are not accepted by the Find API
- Samsung's OAuth does not support `prompt=none` (OpenID Connect silent auth)
- The Samsung Account SDK only exposes `signIn` (no token refresh or silent auth methods)

---

## Active vs. Passive Mode

| Mode | Behaviour | Battery impact |
|------|-----------|----------------|
| **Active** | Sends a location update request to the device before fetching | Higher |
| **Passive** | Fetches the last known location already stored | Lower |

**Defaults:** Active mode is **on** for SmartTags, **off** for all other devices.

Configure under **Settings > Devices & Services > SmartThings Find > Configure**.

---

## What Changed in v1.0.0

Samsung completely rebuilt their Find service:

| | Old (v0.2.x) | New (v1.0.0) |
|---|---|---|
| **API** | `smartthingsfind.samsung.com` | `api.samsungfind.com` |
| **Auth** | JSESSIONID cookie (lasted weeks) | JWT token (expires in 1 hour) |
| **Endpoints** | `.do` endpoints with CSRF tokens | REST API with JWT headers |
| **Token refresh** | Not needed (long-lived cookie) | Not possible (no refresh mechanism) |
| **Setup** | Copy cookie from Application tab | Copy headers from Network tab |

---

## Debugging

Add the following to `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.smartthings_find: debug
```

---

## Disclaimer

- **Unofficial API** — built by reverse-engineering the Samsung Find web service. It may stop working if Samsung changes their backend.
- **1-hour token expiry** — Samsung does not provide a way to refresh tokens automatically. This is unlikely to change unless Samsung opens a public API.
- This project is not affiliated with or endorsed by Samsung or SmartThings.

---

## Contributing

Contributions are welcome — feel free to open issues or submit pull requests. See [CHANGELOG.md](CHANGELOG.md) for recent changes.

If you find a way to extend the token lifetime or discover a Samsung API that supports proper OAuth2 refresh for Find data, please open an issue immediately!

## License

MIT — see [LICENSE](LICENSE) for details.

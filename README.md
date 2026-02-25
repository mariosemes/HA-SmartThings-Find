> **🍴 Fork Notice**
> This is a maintained fork of the original [Vedeneb/HA-SmartThings-Find](https://github.com/Vedeneb/HA-SmartThings-Find) project, which has been archived by its author. A huge thank you to **Vedeneb** for the original concept, design, and all the hard work reverse-engineering the SmartThings Find API — this project would not exist without that foundation. This fork aims to keep the integration working and continue improving it.

# SmartThings Find Integration for Home Assistant

This integration adds support for devices from Samsung SmartThings Find. While intended mainly for Samsung SmartTags, it also works with other devices, such as phones, tablets, watches and earbuds.

Currently the integration creates three entities for each device:
* `device_tracker`: Shows the location of the tag/device.
* `sensor`: Represents the battery level of the tag/device (not supported for earbuds!)
* `button`: Allows you to ring the tag/device.

![screenshot](media/screenshot_1.png)

This integration does **not** allow you to perform actions based on button presses on the SmartTag! There are other ways to do that.


## ⚠️ Warning/Disclaimer ⚠️

- **API Limitations**: Created by reverse engineering the SmartThings Find API, this integration might stop working at any time if changes occur on the SmartThings side.
- **Limited Testing**: The integration hasn't been thoroughly tested. If you encounter issues, please report them by creating an issue.
- **Feature Constraints**: The integration can only support features available on the [SmartThings Find website](https://smartthingsfind.samsung.com/). For instance, stopping a SmartTag from ringing is not possible due to API limitations (while other devices do support this; not yet implemented)

## Notes on authentication

The integration uses Samsung's OAuth2 login flow. After you sign in through a browser, you copy a single cookie value (`JSESSIONID`) from browser DevTools and paste it into Home Assistant. This is a one-time setup step.

The integration stores the time the session was created, so you can track how long a session stays valid (**Settings → Devices & Services → SmartThings Find → Download Diagnostics**). Community experience suggests sessions last **at least several weeks**, but the exact lifetime is not officially documented by Samsung.

As a precaution, a **re-auth flow** is implemented: if the session expires, Home Assistant will show a persistent notification. Clicking it lets you paste a fresh `JSESSIONID` without reinstalling or reconfiguring anything — the process takes less than a minute.

## Notes on connection to the devices

Being able to let a SmartTag ring depends on a phone/tablet nearby which forwards your request via Bluetooth. If your phone is not near your tag, you can't make it ring. The location should still update if any Galaxy device is nearby.

If ringing your tag does not work, first try to let it ring from the [SmartThings Find website](https://smartthingsfind.samsung.com/). If it does not work from there, it cannot work from Home Assistant either! Note that the SmartThings Mobile App uses a different backend than the website — just because ringing works in the app does not mean it works on the web. Always use the web version to test.

## Notes on active/passive mode

It is possible to configure whether to use the integration in **active** or **passive** mode. In passive mode the integration only fetches the last location that was already reported to STF. In active mode the integration sends a "request location update" command, causing the STF server to try to contact your device and push a fresh location. This has a bigger impact on battery and may occasionally wake up the screen of a phone or tablet.

By default, active mode is **enabled for SmartTags** and **disabled for all other devices**. You can change this on the integrations page by clicking `Configure`. The update interval (default: 120 seconds) can also be changed there.


## Installation Instructions

### Using HACS

1. Add this repository as a custom repository in HACS. Either by manually adding `https://github.com/mariosemes/HA-SmartThings-Find` with category `integration` or simply click the following button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mariosemes&repository=HA-SmartThings-Find&category=integration)

2. Search for "SmartThings Find" in HACS and install the integration
3. Restart Home Assistant
4. Proceed to [Setup instructions](#setup-instructions)

### Manual install

1. Download the `custom_components/smartthings_find` directory to your Home Assistant configuration directory
2. Restart Home Assistant
3. Proceed to [Setup instructions](#setup-instructions)

## Setup Instructions

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smartthings_find)

1. Go to the Integrations page
2. Search for "SmartThings *Find*" (**do not confuse with the built-in SmartThings integration!**)
3. Click the login link shown in the setup form — it will open Samsung's login page in your browser
4. Sign in with your Samsung account
5. Once redirected to SmartThings Find, press **F12** to open DevTools
6. Go to **Application → Cookies → https://smartthingsfind.samsung.com**
7. Copy the value of the **JSESSIONID** cookie and paste it into the setup form
8. The integration will validate the session and complete setup

## Debugging

To enable debug logging, add the following to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.smartthings_find: debug
```

The log will include the session age on every startup, e.g.:
```
Session age: 12d 3h (authenticated at 2026-02-13 08:51 UTC)
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome! Feel free to open issues or submit pull requests to help improve this integration.

## Support

For support, please create an issue on the GitHub repository.

## Roadmap

- ~~HACS support~~ ✅
- ~~Allow adding two instances of this integration (two Samsung Accounts)~~ ✅
- ~~Session age tracking via diagnostics~~ ✅
- Service to let a device ring
- Service to make a device stop ringing (for devices that support this feature)

## Disclaimer

This is a third-party integration and is not affiliated with or endorsed by Samsung or SmartThings.

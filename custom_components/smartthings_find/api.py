"""Samsung Find API client for api.samsungfind.com."""
import logging
import json
import base64
import time
from datetime import datetime, timezone

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import API_BASE_URL, BATTERY_LEVELS

_LOGGER = logging.getLogger(__name__)


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification (we only need exp/userId)."""
    try:
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except (IndexError, ValueError, json.JSONDecodeError) as err:
        raise ValueError(f"Invalid JWT token: {err}") from err


def get_login_url() -> str:
    """Return the Samsung Find login URL."""
    return "https://samsungfind.samsung.com"


class SamsungFindApiClient:
    """Client for the Samsung Find REST API.

    Samsung's Find API uses short-lived JWT tokens (1-hour expiry) with no
    refresh mechanism. When the token expires, the integration raises
    ConfigEntryAuthFailed to trigger Home Assistant's reauth flow.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth_token: str,
        user_id: str,
        country_code: str,
    ):
        self._session = session
        self._auth_token = auth_token
        self._user_id = user_id
        self._country_code = country_code
        self._token_expiry = self._extract_expiry(auth_token)

    @staticmethod
    def _extract_expiry(token: str) -> int:
        """Extract the exp claim from a JWT."""
        try:
            payload = decode_jwt_payload(token)
            return payload.get("exp", 0)
        except ValueError:
            return 0

    @property
    def is_token_expired(self) -> bool:
        """Check if the JWT token has expired (with 60s buffer)."""
        return time.time() >= (self._token_expiry - 60)

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def country_code(self) -> str:
        return self._country_code

    def _headers(self) -> dict:
        """Build the auth headers for API requests."""
        return {
            "x-sec-sa-authtoken": self._auth_token,
            "x-sec-sa-userid": self._user_id,
            "x-sec-sa-countrycode": self._country_code,
            "x-sec-find-client-type": "web",
            "Accept": "application/json, text/plain, */*",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated API request."""
        if self.is_token_expired:
            raise ConfigEntryAuthFailed(
                "JWT token has expired. Please re-authenticate in Settings > "
                "Devices & Services > Samsung Find."
            )

        url = f"{API_BASE_URL}{path}"
        headers = {**self._headers(), **kwargs.pop("headers", {})}

        async with self._session.request(
            method, url, headers=headers, **kwargs
        ) as resp:
            if resp.status in (401, 403):
                _LOGGER.warning(
                    "API returned %s for %s, token may be invalid", resp.status, path
                )
                raise ConfigEntryAuthFailed(
                    f"Samsung Find API returned {resp.status}. Please re-authenticate."
                )
            if resp.status != 200:
                text = await resp.text()
                _LOGGER.error("API error [%s] %s: %s", resp.status, path, text)
                raise Exception(f"API request failed [{resp.status}]: {text}")

            return await resp.json()

    # ── Device endpoints ──────────────────────────────────────────────

    async def get_device_details(self, device_id: str) -> dict:
        """Fetch detailed device info including friendly name and icon.

        Returns the device dict from GET /tag/devices/{deviceId} with:
        - label: user-given friendly name (e.g. "Peugeot SmartTag")
        - name: device type name (e.g. "Tag2(UWB)")
        - icons: dict with coloredIcon, dimmedIcon, etc.
        - deviceModel: str
        """
        try:
            data = await self._request("GET", f"/tag/devices/{device_id}")
            return data.get("item", data)
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.warning("Failed to fetch details for device %s: %s", device_id, err)
            return {}

    async def get_devices(self, device_type: str = "TAG") -> list[dict]:
        """Fetch the list of devices."""
        data = await self._request(
            "GET",
            "/devices",
            params={"userId": self._user_id, "type": device_type},
        )
        return data.get("items", [])

    async def get_all_devices(self) -> list[dict]:
        """Fetch TAG and FMM (phone/watch/tablet) devices."""
        tags = await self.get_devices("TAG")
        fmm = await self.get_devices("FMM")
        return tags + fmm

    async def get_device_location(self, device_id: str) -> dict:
        """Fetch the latest location for a device."""
        try:
            data = await self._request(
                "GET",
                "/tag/geolocations",
                params={
                    "deviceId": device_id,
                    "userId": self._user_id,
                },
            )
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Failed to fetch location for %s: %s", device_id, err)
            return self._empty_location(device_id)

        items = data.get("items", [])
        if not items:
            return self._empty_location(device_id)

        device_item = items[0]
        geolocations = device_item.get("geolocations", [])

        if not geolocations:
            return self._empty_location(device_id)

        # Find the most recent valid geolocation
        best_loc = None
        best_time = 0
        for loc in geolocations:
            if not loc.get("valid", False):
                continue
            update_time = loc.get("lastUpdateTime", 0)
            if update_time > best_time:
                best_time = update_time
                best_loc = loc

        if not best_loc:
            best_loc = geolocations[0]
            best_time = best_loc.get("lastUpdateTime", 0)

        lat = _safe_float(best_loc.get("latitude"))
        lon = _safe_float(best_loc.get("longitude"))
        accuracy = _safe_float(best_loc.get("accuracy"))
        battery = _parse_battery(best_loc.get("battery"))

        gps_date = None
        if best_time:
            gps_date = datetime.fromtimestamp(best_time / 1000, tz=timezone.utc)

        return {
            "dev_id": device_id,
            "location_found": lat is not None and lon is not None,
            "update_success": True,
            "location": {
                "latitude": lat,
                "longitude": lon,
                "gps_accuracy": accuracy,
                "gps_date": gps_date,
            },
            "battery": battery,
            "raw": best_loc,
        }

    async def ring_device(self, device_id: str) -> bool:
        """Ring a device."""
        try:
            await self._request(
                "POST",
                "/operation",
                json={
                    "deviceId": device_id,
                    "type": "RING",
                    "userId": self._user_id,
                },
            )
            return True
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Failed to ring device %s: %s", device_id, err)
            return False

    async def request_location_update(self, device_id: str) -> bool:
        """Request a fresh location update from a device (active mode)."""
        try:
            await self._request(
                "POST",
                "/operation",
                json={
                    "deviceId": device_id,
                    "type": "LOCATION",
                    "userId": self._user_id,
                },
            )
            return True
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Failed to request location for %s: %s", device_id, err)
            return False

    async def validate(self) -> bool:
        """Validate the current auth token by making a test API call."""
        try:
            await self._request("GET", "/sync-data/device")
            return True
        except ConfigEntryAuthFailed:
            return False
        except Exception:
            return False

    @staticmethod
    def _empty_location(device_id: str) -> dict:
        return {
            "dev_id": device_id,
            "location_found": False,
            "update_success": False,
            "location": {
                "latitude": None,
                "longitude": None,
                "gps_accuracy": None,
                "gps_date": None,
            },
            "battery": None,
            "raw": {},
        }


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_battery(raw) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        mapped = BATTERY_LEVELS.get(raw.upper())
        if mapped is not None:
            return mapped
        try:
            return int(raw)
        except ValueError:
            _LOGGER.warning("Unknown battery level: %s", raw)
            return None
    return None


def get_device_name(device: dict, details: dict | None = None) -> str:
    """Extract a human-readable device name."""
    if details:
        label = details.get("label")
        if label:
            return label
        name = details.get("name")
        if name:
            return name

    metadata = device.get("metadata", {})
    vendor = metadata.get("vendor", {})
    model_name = vendor.get("modelName", "")
    if model_name:
        return model_name

    identifier = device.get("identifier", "")
    device_type = device.get("type", "Unknown")
    if identifier:
        return f"{device_type} {identifier}"
    return f"{device_type} {device.get('deviceId', 'Unknown')[:8]}"


def get_device_icon(details: dict | None) -> str | None:
    if not details:
        return None
    icons = details.get("icons", {})
    return icons.get("coloredIcon")


def get_battery_from_device(device: dict) -> int | None:
    metadata = device.get("metadata", {})
    battery_info = metadata.get("battery", {})
    return _parse_battery(battery_info.get("level"))

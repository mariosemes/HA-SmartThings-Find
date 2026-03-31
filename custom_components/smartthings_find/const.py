DOMAIN = "smartthings_find"

# Samsung Find API
API_BASE_URL = "https://api.samsungfind.com"

# Config entry data keys
CONF_AUTH_TOKEN = "auth_token"
CONF_USER_ID = "user_id"
CONF_COUNTRY_CODE = "country_code"

# Options
CONF_ACTIVE_MODE_SMARTTAGS = "active_mode_smarttags"
CONF_ACTIVE_MODE_OTHERS = "active_mode_others"

CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT = True
CONF_ACTIVE_MODE_OTHERS_DEFAULT = False

CONF_UPDATE_INTERVAL = "update_interval"
CONF_UPDATE_INTERVAL_DEFAULT = 120

# Battery level mapping (Samsung API returns text levels)
BATTERY_LEVELS = {
    'FULL': 100,
    'MEDIUM': 50,
    'LOW': 15,
    'VERY_LOW': 5
}

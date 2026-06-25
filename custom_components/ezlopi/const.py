
DOMAIN = "ezlopi"
EZLOPI_API_URL_BASE = "https://api-cloud.ezlo.com/v1/request"
# v4 REST login endpoint. Returns the JWT at the top level ({"token": ...}),
# unlike the legacy v1 envelope which wrapped it in {"data": {"token": ...}}.
EZLOPI_LOGIN_URL = "https://api-cloud.ezlo.com/api/v4/login/3/sessions"
# v4 REST controller listing. GET with the JWT in the `x-access-token` header;
# returns {"controllers": [...], "pagination": {...}} with no envelope (the
# legacy v1 call wrapped it in {"data": {"controllers": [...]}}).
EZLOPI_CONTROLLER_LIST_URL = "https://api-cloud.ezlo.com/api/v4/controller_list/3/controllers"
EZLOPI_API = "EZLOPI_API"
WS_API = "ws_api"
LOCK = "lock"
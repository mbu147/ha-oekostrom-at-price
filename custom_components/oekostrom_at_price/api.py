"""Client for the mein.oekostrom.at customer portal (JSON API behind api-proxy.php)."""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime

import aiohttp

BASE_URL = "https://mein.oekostrom.at"
PROXY_URL = f"{BASE_URL}/wp-content/plugins/oekostrom-kundenportal/includes/api-proxy.php"
PORTAL_NAME = "OEKOSTROM"
_LOGGER = logging.getLogger(__name__)


class OekostromAuthError(Exception):
    """Login failed."""


class OekostromApiError(Exception):
    """Unexpected API response."""


class OekostromClient:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._session_guid: str | None = None
        self._acc_id: int | None = None
        self._cus_id: int | None = None

    async def _call(self, endpoint: str, token: str, body: dict):
        params = {
            "api": "sdk-prod",
            "endpoint": endpoint,
            "token": token,
            "get_from_cache": "false",
            "save_to_cache": "false",
        }
        async with self._session.post(
            PROXY_URL,
            params=params,
            json=body,
            headers={"Referer": f"{BASE_URL}/"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_login(self) -> None:
        async with self._session.get(
            f"{BASE_URL}/", timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            html = await resp.text()
        match = re.search(r'proxy_login_token\s*=\s*"([^"]+)"', html)
        if not match:
            raise OekostromApiError("proxy_login_token not found")

        data = await self._call(
            "UserLogin",
            match.group(1),
            {
                "Username": self._username,
                # The portal frontend sends the MD5 hex digest (spark-md5), not the plain password.
                "Password": hashlib.md5(self._password.encode("utf-8")).hexdigest(),
                "PortalName": PORTAL_NAME,
            },
        )
        guid = data.get("SessionGUID") if isinstance(data, dict) else None
        if not guid:
            _LOGGER.warning("Login rejected: %s", data if isinstance(data, dict) and len(str(data)) < 200 else type(data))
            raise OekostromAuthError("Login failed")
        self._session_guid = guid

        accounts = [a for a in data.get("AccountIds", []) if a.get("AccType") == "Strom"]
        active = [a for a in accounts if a.get("AccState") == "A"] or accounts
        if not active:
            raise OekostromApiError("No electricity account found")
        self._acc_id = active[0]["AccId"]
        self._cus_id = active[0]["CusId"]

    async def _price_infos(self) -> list[dict]:
        return await self._call(
            "GetPriceInfos",
            self._session_guid,
            {
                "SessionGUID": self._session_guid,
                "PortalName": PORTAL_NAME,
                "AccID": str(self._acc_id),
                "CusID": str(self._cus_id),
            },
        )

    async def async_get_current_price(self) -> dict:
        """Return the price entry valid today (Amount = gross ct/kWh)."""
        if not self._session_guid:
            await self.async_login()
        try:
            infos = await self._price_infos()
        except (aiohttp.ClientError, ValueError):
            infos = None
        if not isinstance(infos, list):
            # Session probably expired
            await self.async_login()
            infos = await self._price_infos()
        if not isinstance(infos, list):
            raise OekostromApiError("Unexpected GetPriceInfos response")

        today = date.today()
        for entry in infos:
            start = datetime.strptime(entry["BDate"], "%d.%m.%Y").date()
            end = datetime.strptime(entry["EDate"], "%d.%m.%Y").date()
            if start <= today <= end:
                return entry
        raise OekostromApiError("No price entry for today")

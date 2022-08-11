from homeassistant.core import HomeAssistant
from systemair.saveconnect import SaveConnect


class SaveConnectAPI:
    """API for the SaveConnect Interface."""

    def __init__(self,
                 hass: HomeAssistant,
                 email: str,
                 password: str,
                 ws_enabled: bool,
                 refresh_token_interval: int,
                 loop
                 ) -> None:
        """Init SaveConnect API."""
        self._hass = hass

        self._sc = SaveConnect(
            email=email,
            password=password,
            ws_enabled=ws_enabled,
            update_interval=0,
            refresh_token_interval=refresh_token_interval,
            loop=loop
        )
        self.online = False

    @property
    def user_mode(self):
        return self._sc.user_mode

    async def test_connection(self) -> bool:
        """Test connectivity to the SaveConnect API is OK."""
        self.online = True  # TODO
        return True  # await self._sc.test_connectivity()

    async def auth(self) -> bool:
        return await self._sc.login()

    async def get_devices(self, update=True, fetch_device_info=False):
        res = await self._sc.get_devices(update=update, fetch_device_info=fetch_device_info)
        return res

    async def update_device_info(self, devices):
        await self._sc.update_device_info(devices)

    async def read_data(self, device) -> bool:
        return await self._sc.read_data(device=device)

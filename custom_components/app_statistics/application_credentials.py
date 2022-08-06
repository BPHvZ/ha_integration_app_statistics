"""application_credentials platform the App Statisitcs OAuth integration."""
from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant
import oauth2client


AUTHORIZATION_SERVER = AuthorizationServer(
    oauth2client.GOOGLE_AUTH_URI, oauth2client.GOOGLE_TOKEN_URI
)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AUTHORIZATION_SERVER

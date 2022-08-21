"""A textual widget used to display environment information.
"""
import random
from typing import Optional

from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widget import Widget
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.as_api import AsApi, AsApiRv

from squeck import common
from squeck.environment import Environment
from squeck.access_token import AccessToken

_KEY_STYLE: Style = Style(color="orange_red1", bold=True)
_KEY_VALUE_STYLE: Style = Style(color="bright_white")
_VALUE_ERROR_STYLE: Style = Style(color="bright_red", italic=True)


class EnvWidget(Widget):  # type: ignore
    """Displays the environment."""

    as_access_token: Optional[str] = None
    dm_access_token: Optional[str] = None

    def __init__(self, environment_name: str) -> None:
        super().__init__()
        self.environment_name = environment_name
        self.environment = Environment(environment_name)

        self.as_api: Optional[AsApi] = None
        if self.environment.as_api():
            self.as_api = AsApi()
            self.as_api.set_api_url(self.environment.as_api(), verify_ssl_cert=False)
        self.dm_api: Optional[AsApi] = None
        if self.environment.dm_api():
            self.dm_api = DmApi()
            self.dm_api.set_api_url(self.environment.dm_api(), verify_ssl_cert=False)

        self.panel_style: Style = Style(color="grey54", bgcolor="black")

    def on_mount(self) -> None:
        """Widget initialisation."""
        # Set an interval timer - we check the AS and DM APIs
        # regularly trying to get the version of each.
        # Randomly set between 10 and 30 seconds.
        interval: int = random.randint(10, 30)
        self.set_interval(interval, self.refresh)

    def render(self) -> Panel:
        """Render the widget."""

        # Set the URL for this environment.
        # Get access tokens (using anything we have)
        self.as_access_token = AccessToken.get_as_access_token(
            self.environment, prior_token=self.as_access_token
        )
        self.dm_access_token = AccessToken.get_dm_access_token(
            self.environment, prior_token=self.dm_access_token
        )

        # Get the version of the DM API and the AS API
        as_api_version: str = "Not available"
        as_api_version_style: Style = _VALUE_ERROR_STYLE
        if self.as_api:
            as_ret_val: AsApiRv = self.as_api.get_version()
            if as_ret_val.success:
                as_api_version = f"{as_ret_val.msg['version']}"
                as_api_version_style = _KEY_VALUE_STYLE
        as_api_version_value: Text = Text(as_api_version, style=as_api_version_style)

        dm_api_version: str = "Not available"
        dm_api_version_style: Style = _VALUE_ERROR_STYLE
        if self.dm_api:
            dm_ret_val: DmApiRv = self.dm_api.get_version()
            if dm_ret_val.success:
                dm_api_version = f"{dm_ret_val.msg['version']}"
                dm_api_version_style = _KEY_VALUE_STYLE
        dm_api_version_value: Text = Text(dm_api_version, style=dm_api_version_style)

        # Information is presented in a table.
        table: Table = Table(
            show_header=False,
            collapse_padding=True,
            box=None,
        )
        table.add_column("Key", style=_KEY_STYLE, no_wrap=True, justify="right")
        table.add_column("Value", style=_KEY_VALUE_STYLE, no_wrap=True)

        # The 'Authentication host'
        kc_host = Text(
            f"{self.environment.keycloak_hostname()}", style=_KEY_VALUE_STYLE
        )

        # The API lines are also dynamically styled.
        as_hostname: Optional[str] = self.environment.as_hostname()
        if as_hostname:
            as_hostname_text: Text = Text(as_hostname + " ", style=_KEY_VALUE_STYLE)
            if self.as_access_token:
                as_hostname_text.append(common.TICK)
            else:
                as_hostname_text.append(common.CROSS)
        else:
            as_hostname_text = Text("Undefined", style=_VALUE_ERROR_STYLE)

        dm_hostname: Optional[str] = self.environment.dm_hostname()
        if dm_hostname:
            dm_hostname_text: Text = Text(dm_hostname + " ", style=_KEY_VALUE_STYLE)
            if self.dm_access_token:
                dm_hostname_text.append(common.TICK)
            else:
                dm_hostname_text.append(common.CROSS)
        else:
            dm_hostname_text = Text("Undefined", style=_VALUE_ERROR_STYLE)

        table.add_row("Auth", kc_host)
        table.add_row("AS", as_hostname_text)
        table.add_row("v", as_api_version_value)
        table.add_row("DM", dm_hostname_text)
        table.add_row("v", dm_api_version_value)

        return Panel(
            table,
            title=self.environment_name,
            title_align="right",
            box=box.ASCII,
            style=self.panel_style,
            padding=0,
            height=7,
        )

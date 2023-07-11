from flet import (
    AppBar,
    IconButton,
    PopupMenuButton,
    PopupMenuItem,
    Divider,
    Row,
    Text,
    VerticalDivider,
    Image,
    AlertDialog,
    TextButton,
    MainAxisAlignment,
    Icon,
    Theme,
)
from flet_core.colors import SURFACE_VARIANT
from flet_core.icons import (
    LIGHT_MODE,
    DARK_MODE,
    HOME,
    BUG_REPORT,
    HELP,
    PALETTE,
    DOWNLOAD,
)
from utils.preferences import AccentColor
from utils.functions import check_update
import asyncio


class TFAExtractionAppBar(AppBar):
    def __init__(self, **kwargs):
        self.page = kwargs["page"]
        del kwargs["page"]
        actions = []
        actions.extend(
            [
                IconButton(
                    icon=DOWNLOAD,
                    on_click=self.go_to_update_page,
                    visible=False,
                    tooltip="A newer version is available.",
                ),
                IconButton(
                    data="theme_switcher",
                    icon=DARK_MODE if self.page.theme_mode == "LIGHT" else LIGHT_MODE,
                    on_click=self.change_theme,
                    tooltip="Change theme",
                ),
                PopupMenuButton(
                    icon=PALETTE,
                    items=[
                        PopupMenuItem(
                            data=color,
                            content=Row(
                                controls=[
                                    Icon(PALETTE, color=color.value),
                                    Text(
                                        value=" ".join(
                                            [
                                                w.capitalize()
                                                for w in color.value.split("_")
                                            ]
                                        )
                                    ),
                                ]
                            ),
                            on_click=self.change_color,
                        )
                        for color in AccentColor
                    ],
                ),
                VerticalDivider(width=3, visible=False),
                PopupMenuButton(
                    data="other-buttons",
                    items=[
                        PopupMenuItem(
                            data="discord",
                            content=Row(
                                controls=[
                                    Image(
                                        (
                                            "assets/icons/brands/discord-mark-black.png"
                                            if self.page.theme_mode == "LIGHT"
                                            else "assets/icons/brands/discord-mark-white.png"
                                        ),
                                        width=19,
                                    ),
                                    Text("Discord"),
                                ]
                            ),
                            on_click=self.go_url,
                        ),
                        PopupMenuItem(
                            data="github",
                            content=Row(
                                controls=[
                                    Image(
                                        (
                                            "assets/icons/brands/github-mark-black.png"
                                            if self.page.theme_mode == "LIGHT"
                                            else "assets/icons/brands/github-mark-white.png"
                                        ),
                                        width=19,
                                    ),
                                    Text("Github"),
                                ]
                            ),
                            on_click=self.go_url,
                        ),
                        PopupMenuItem(
                            data="paypal",
                            content=Row(
                                controls=[
                                    Image(
                                        "assets/icons/brands/paypal-mark.png", width=19
                                    ),
                                    Text("Paypal"),
                                ]
                            ),
                            on_click=self.go_url,
                        ),
                        Divider(),
                        PopupMenuItem(
                            icon=BUG_REPORT,
                            data="discord",
                            text="Report a bug",
                            on_click=self.go_url,
                        ),
                        PopupMenuItem(
                            icon=HELP, text="About", on_click=self.open_about
                        ),
                    ],
                    tooltip="Others",
                ),
            ]
        )
        actions.extend(kwargs.get("actions", []))
        super().__init__(
            leading_width=40,
            bgcolor=SURFACE_VARIANT,
            actions=actions,
            center_title=True,
            **kwargs,
        )
        asyncio.create_task(self.check_for_update())

    async def check_for_update(self):
        if (await check_update(self.page.VERSION)) is not None:
            self.page.appbar.actions[0].visible = True
            self.page.snack_bar.content.value = "A new update is available"
            self.page.snack_bar.bgcolor = "yellow"
            self.page.snack_bar.open = True
            await self.page.update_async()

    async def go_to_update_page(self, _):
        await self.page.launch_url_async(await check_update(self.page.VERSION))

    async def change_theme(self, _):
        self.page.theme_mode = "light" if self.page.theme_mode == "dark" else "dark"
        for action in self.actions:
            if action.data == "theme_switcher":
                action.icon = (
                    DARK_MODE if self.page.theme_mode == "light" else LIGHT_MODE
                )
            if action.data == "other-buttons":
                for item in action.items:
                    if item.data in ["discord", "github"] and item.content is not None:
                        item.content.controls[0].src = (
                            f"assets/icons/brands/{item.data}-mark-black.png"
                            if self.page.theme_mode == "light"
                            else f"assets/icons/brands/{item.data}-mark-white.png"
                        )
        self.page.preferences.theme = self.page.theme_mode
        self.page.preferences.save()
        await self.page.update_async()

    async def go_url(self, event):
        urls = {
            "discord": "https://discord.gg/duuFEsFWk5",
            "github": "https://github.com/Sly0511/TroveBuilds",
            "paypal": "https://www.paypal.com/paypalme/waterin",
        }
        await self.page.launch_url_async(urls[event.control.data])

    async def open_about(self, event):
        self.dlg = AlertDialog(
            modal=True,
            title=Text("About"),
            actions=[
                TextButton("Close", on_click=self.close_dlg),
            ],
            actions_alignment=MainAxisAlignment.END,
            content=Text(
                "This application was developed by Sly. Interface design improved by Cr0nicl3 D3str0y3r.\n\nI am coding this as an hobby with the goal of"
                " achieving greater front-end building skills, at the same time I also improve code"
                " making and organization skills\n\nI have the goal to not only build something"
                " that is usable but mostly updatable with little effort or code knowledge"
                " this however may be a challenge if newer updates come with changes on behavior of"
                " previous content.\n\nI don't promise to keep this up to date forever, but as long as"
                " I am around I should be able to.\n\nThanks for using my application. <3"
            ),
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )
        self.page.dialog = self.dlg
        self.dlg.open = True
        await self.page.update_async()

    async def close_dlg(self, e):
        self.dlg.open = False
        await self.page.update_async()

    async def change_color(self, event):
        color = event.control.data
        self.page.theme = Theme(color_scheme_seed=color)
        self.page.preferences.accent_color = color
        self.page.preferences.save()
        await self.page.update_async()

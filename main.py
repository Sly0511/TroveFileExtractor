from flet import app, Page, Theme, Column

from interface import Interface
from utils.controls import TFAExtractionAppBar
from utils.preferences import Preferences
from pathlib import Path


class Extractor:
    def run(self):
        app(target=self.start, assets_dir="assets")

    async def start(self, page: Page):
        page.preferences = Preferences.load_from_json(Path("preferences.json"))
        page.title = "Trove File Archive Extractor"
        page.theme_mode = page.preferences.theme
        page.theme = Theme(color_scheme_seed=str(page.preferences.accent_color))
        page.appbar = TFAExtractionAppBar(page=page)
        page.window_min_width = 1600
        page.window_min_height = 900
        page.window_width = 1600
        page.window_height = 900
        interface = Interface(page)
        await page.add_async(Column(controls=[interface.main]))


if __name__ == "__main__":
    AppObj = Extractor()
    AppObj.run()

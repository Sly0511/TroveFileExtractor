import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from flet import app, Page, Theme, Column, SnackBar, Text

from interface import Interface
from utils.controls import TFAExtractionAppBar
from utils.preferences import Preferences


class Extractor:
    def run(self):
        app(target=self.start, assets_dir="assets")

    async def start(self, page: Page):
        APPDATA = Path(os.environ.get("APPDATA"))
        app_data = APPDATA.joinpath("Trove/sly.dev/TroveFileExtractor")
        logs = app_data.joinpath("logs")
        logs.mkdir(parents=True, exist_ok=True)
        latest_log = logs.joinpath("latest.log")
        dated_log = logs.joinpath(datetime.now().strftime("%Y-%m-%d %H-%M-%S.log"))
        targets = (
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(latest_log),
            logging.FileHandler(dated_log)
        )
        logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=targets)
        page.preferences = Preferences.load_from_json(app_data.joinpath("preferences.json"))
        page.title = "Trove File Archive Extractor"
        page.theme_mode = page.preferences.theme
        page.theme = Theme(color_scheme_seed=str(page.preferences.accent_color))
        page.appbar = TFAExtractionAppBar(page=page)
        page.window_min_width = 1600
        page.window_min_height = 900
        page.window_width = 1600
        page.window_height = 900
        page.snack_bar = SnackBar(content=Text())
        interface = Interface(page)
        await page.add_async(Column(controls=[interface.main]))

if __name__ == "__main__":
    AppObj = Extractor()
    AppObj.run()

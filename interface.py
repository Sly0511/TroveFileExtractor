import asyncio
import json
import os

from flet import (
    ResponsiveRow,
    Column,
    Row,
    DataTable,
    DataColumn,
    DataRow,
    DataCell,
    Text,
    TextField,
    ElevatedButton,
    Switch,
    ProgressRing,
    ProgressBar,
    Dropdown,
    dropdown,
    MainAxisAlignment
)

from pathlib import Path
from datetime import datetime
from utils.controls import ScrollingFrame
from utils import tasks
from utils.extractor import find_changes, find_all_indexes
from json import load
from humanize import naturalsize
from utils.trove import GetTroveLocations


class Interface:
    def __init__(self, page):
        self.page = page
        self.tfi_list = []
        self.main = ResponsiveRow(alignment=MainAxisAlignment.START)
        self.setup_controls()

    def setup_controls(self):
        self.trove_locations = list(GetTroveLocations())
        locations = self.page.preferences.directories
        if self.trove_locations:
            directory = self.trove_locations[0]
            if locations.extract_from is None:
                locations.extract_from = directory[1]
            if locations.extract_to is None:
                locations.extract_to = directory[1].joinpath("extracted")
            if locations.changes_from is None:
                locations.changes_from = directory[1].joinpath("extracted")
            if locations.changes_to is None:
                locations.changes_to = directory[1].joinpath("changes")
        self.extract_from = TextField(
            label="Trove directory:",
            value=locations.extract_from,
            height=55,
            col=6
        )
        self.extract_to = TextField(
            label="Extract to:",
            value=locations.extract_to,
            height=55
        )
        self.changes_to = TextField(
            label="Save changes to:",
            value=locations.changes_to,
            height=55
        )
        self.changes_from = TextField(
            label="Get changes from:",
            value=locations.changes_from,
            height=55
        )
        self.main_controls = ResponsiveRow(
            controls=[
                Column(
                    controls=[
                        ResponsiveRow(
                            controls=[
                                self.extract_from,
                                Dropdown(
                                    value=locations.extract_from,
                                    options=[
                                        dropdown.Option(
                                            key=location[1],
                                            text=f"{location[0]} - {str(location[1].name)}"
                                        )
                                        for location in self.trove_locations
                                    ],
                                    col=6
                                )
                            ],
                        ),
                        Row(
                            controls=[
                                Row(
                                    controls=[
                                        Switch(
                                            on_change=self.switch_advanced_mode
                                        ),
                                        Text("Advanced Settings")
                                    ]
                                ),
                                Row(
                                    controls=[
                                        Switch(),
                                        Text("Performance Mode")
                                    ]
                                )
                            ],
                            col=6
                        ),
                        Column(
                            controls=[
                                self.extract_to
                            ],
                            col=12
                        ),
                        ResponsiveRow(
                            controls=[
                                Column(
                                    controls=[
                                        self.changes_to
                                    ],
                                    visible=not self.page.preferences.advanced_mode,
                                    col=6
                                ),
                                Column(
                                    controls=[
                                        self.changes_from
                                    ],
                                    visible=not self.page.preferences.advanced_mode,
                                    col=6
                                )
                            ]
                        )
                    ],
                    col=6
                ),
                ResponsiveRow(
                    controls=[
                        ElevatedButton(
                            "Refresh lists",
                            col=6
                        ),
                        ElevatedButton(
                            "Extract changed files",
                            col=6
                        ),
                        ElevatedButton(
                            "Extract selected directories",
                            col=6
                        ),
                        ElevatedButton(
                            "Extract all",
                            col=6
                        )
                    ],
                    col=6
                )
            ]
        )
        self.directory_progress = Row(controls=[ProgressRing(), Text("Loading directories...\nThis may take a minute")])
        self.files_progress = Row(controls=[ProgressRing(), Text("Loading files...\nThis may take a minute")])
        self.directory_list = DataTable(
            columns=[
                DataColumn(Text("Path")),
                DataColumn(Text("Size")),
                DataColumn(Text("Changed files"))
            ],
            data_row_height=30,
            visible=False
        )
        self.files_list = DataTable(
            columns=[
                DataColumn(Text("Path")),
                DataColumn(Text("Size"))
            ],
            data_row_height=30,
            visible=False
        )
        self.metrics = Column(
            controls=[
                Row(
                    controls=[
                        Text("Update Size:"),
                        Text(naturalsize(0, gnu=True))
                    ]
                )
            ]
        )
        self.main.controls.extend(
            [
                Column(
                    controls=[
                        self.main_controls
                    ]
                ),
                Column(
                    controls=[
                        Text(f"Directory List", size=20),
                        self.directory_progress,
                        ScrollingFrame(self.directory_list, height=500),
                    ],
                    height=600,
                    col=6,
                    alignment=MainAxisAlignment.START
                ),
                Column(
                    controls=[
                        Text("Changed/Added Files List", size=20),
                        self.files_progress,
                        ScrollingFrame(self.files_list, height=500)
                    ],
                    height=600,
                    col=6,
                    alignment=MainAxisAlignment.START
                ),

            ]
        )
        self.refresh_lists.cancel()


    def get_trove_directories(self):
        ...

    async def switch_advanced_mode(self, event):
        self.page.preferences.advanced_mode = event.control.value
        self.setup_controls()
        await self.page.update_async()

    async def directory_selection(self, event):
        event.control.selected = not event.control.selected
        for row in self.files_list.rows:
            if row.data.archive.index == event.control.data:
                row.visible = event.control.selected
        await self.files_list.update_async()
        await self.directory_list.update_async()

    async def refresh_directories(self, _):
        self.refresh_lists.start()

    @tasks.loop(seconds=1)
    async def refresh_lists(self):
        try:
            # Disable controls throughout the application
            self.directory_list.rows.clear()
            self.files_list.rows.clear()
            self.directory_progress.visible = True
            self.directory_list.visible = False
            self.files_progress.visible = True
            self.files_list.visible = False
            await self.page.update_async()
            # Get changes
            hashes = json.load(open("hashes.json"))  # dict()
            changed_files = []
            indexes = [[index, len(index.files_list), 0] for index in find_all_indexes(Path("PTS"), hashes, False)]
            for i, file in enumerate(find_changes(Path("PTS"), Path("test"), hashes)):
                # break  # TODO: Remove this for prod
                changed_files.append(file)
            changed_files.sort(key=lambda x: [x.archive.index.path, x.path])
            for file in changed_files:
                for index in indexes:
                    if index[0] == file.archive.index:
                        index[2] += 1
                        break
            # Add changes refreshing logic
            indexes.sort(key=lambda x: [-x[2], str(x[0].directory)])
            for index, files_count, changes_count in indexes:
                self.directory_list.rows.append(
                    DataRow(
                        data=index,
                        cells=[
                            DataCell(
                                Text(
                                    str(index.directory.relative_to(Path("PTS"))),
                                    color="green" if changes_count else None,
                                    size=12
                                )
                            ),
                            DataCell(
                                Text(
                                    naturalsize(sum([f["size"] for f in index.files_list]), gnu=True),
                                    color="green" if changes_count else None,
                                    size=12
                                )
                            ),
                            DataCell(
                                Text(
                                    changes_count,
                                    color="green" if changes_count else None,
                                    size=12
                                )
                            )
                        ],
                        selected=bool(changes_count),
                        on_select_changed=self.directory_selection
                    )
                )
            if changed_files:
                for file in changed_files:
                    self.files_list.rows.append(
                        DataRow(
                            data=file,
                            cells=[
                                DataCell(
                                    Text(
                                        file.path.relative_to(Path("PTS")),
                                        color=file.color
                                    )
                                ),
                                DataCell(
                                    Text(
                                        naturalsize(file.size, gnu=True),
                                        color=file.color
                                    )
                                )
                            ]
                        )
                    )
            else:
                self.files_list.rows.append(
                    DataRow(
                        cells=[
                            DataCell(Text("No changed directories found.")),
                            DataCell(Text(""))
                        ]
                    )
                )
            self.metrics.controls[0].controls[1].value = naturalsize(sum([f.size for f in changed_files]), gnu=True)
            # Re enable controls
            self.directory_progress.visible = False
            self.directory_list.visible = True
            self.files_progress.visible = False
            self.files_list.visible = True
            await self.directory_list.update_async()
            await self.files_list.update_async()
            await self.page.update_async()
            self.refresh_lists.cancel()
        except Exception as e:
            print(e)

import asyncio
import json
from pathlib import Path
from datetime import datetime

from flet import (
    ResponsiveRow,
    Column,
    Row,
    DataTable,
    DataColumn,
    DataRow,
    DataCell,
    Text,
    ElevatedButton,
    Switch,
    ProgressRing,
    Dropdown,
    dropdown,
    MainAxisAlignment,
    FilePicker,
    ProgressBar,
    AlertDialog,
    IconButton,
    TextField,
    icons
)
from humanize import naturalsize

from utils import tasks
from utils.controls import PathField
from utils.extractor import find_changes, find_all_indexes
from utils.trove import GetTroveLocations
from utils.functions import throttle


class Interface:
    def __init__(self, page):
        self.page = page
        self.tfi_list = []
        self.main = ResponsiveRow(alignment=MainAxisAlignment.START)
        self.setup_controls()

    def setup_controls(self):
        self.trove_locations = list(GetTroveLocations())
        self.locations = self.page.preferences.directories
        if self.trove_locations:
            directory = self.trove_locations[0]
            if self.locations.extract_from is None:
                self.locations.extract_from = directory[1]
            if self.locations.extract_to is None:
                self.locations.extract_to = directory[1].joinpath("extracted")
            if self.locations.changes_to is None:
                self.locations.changes_to = directory[1].joinpath("changes")
        self.extract_from = PathField(
            data="extract_from",
            label="Trove directory:",
            value=self.locations.extract_from,
            on_change=self.avoid_text_edit,
            # on_submit=self.set_text_directory,
            col=10
        )
        self.extract_to = PathField(
            data="extract_to",
            label="Extract to:",
            value=self.locations.extract_to,
            on_change=self.avoid_text_edit,
            # on_submit=self.set_text_directory,
            col=11
        )
        self.changes_to = PathField(
            data="changes_to",
            label="Save changes to:",
            value=self.locations.changes_to,
            on_change=self.avoid_text_edit,
            # on_submit=self.set_text_directory,
            disabled=not self.page.preferences.advanced_mode,
            col=11
        )
        self.changes_to_pick = IconButton(
            icons.FOLDER,
            data="changes_to",
            on_click=self.pick_directory,
            col=1,
            disabled=not self.page.preferences.advanced_mode,
        )
        self.extract_changes_button = ElevatedButton(
            "Extract changed files",
            on_click=self.extract_changes,
            disabled=True,
            col=6
        )
        self.extract_selected_button = ElevatedButton(
            "Extract selected directories",
            on_click=self.extract_selected,
            disabled=True,
            col=6
        )
        self.extract_all_button = ElevatedButton(
            "Extract all",
            on_click=self.extract_all,
            disabled=True,
            col=6
        )
        self.directory_dropdown = Dropdown(
            value=(
                self.locations.extract_from
                if self.locations.extract_from in [x[1] for x in self.trove_locations] else
                "none"
            ),
            options=[
                dropdown.Option(
                    key=location[1],
                    text=f"{location[0]} - {str(location[1].name)}"
                )
                for location in self.trove_locations
            ] + [dropdown.Option(key="none", text="Custom", disabled=True)],
            on_change=self.change_directory_dropdown,
            col=6
        )
        self.main_controls = ResponsiveRow(
            controls=[
                ResponsiveRow(
                    controls=[
                        ResponsiveRow(
                            controls=[
                                ResponsiveRow(
                                    controls=[
                                        IconButton(
                                            icons.FOLDER,
                                            data="extract_from",
                                            on_click=self.pick_directory,
                                            col=2
                                        ),
                                        self.extract_from,
                                    ],
                                    vertical_alignment="center",
                                    col=6
                                ),
                                self.directory_dropdown
                            ],
                        ),
                        ResponsiveRow(
                            controls=[
                                IconButton(
                                    icons.FOLDER,
                                    data="extract_to",
                                    on_click=self.pick_directory,
                                    col=1
                                ),
                                self.extract_to,
                            ],
                            vertical_alignment="center",
                            col=12
                        ),
                        ElevatedButton(
                            "Refresh lists",
                            on_click=self.refresh_directories,
                            col=4
                        ),
                        Row(
                            controls=[
                                Switch(
                                    value=self.page.preferences.advanced_mode,
                                    on_change=self.switch_advanced_mode
                                ),
                                Text("Advanced Settings")
                            ],
                            col=4
                        ),
                        Row(
                            controls=[
                                Switch(
                                    value=self.page.preferences.performance_mode,
                                    on_change=self.switch_performance_mode
                                ),
                                Text("Performance Mode")
                            ],
                            col=4
                        ),
                    ],
                    col=6
                ),
                ResponsiveRow(
                    controls=[
                        ResponsiveRow(
                            controls=[
                                ResponsiveRow(
                                    controls=[
                                        self.changes_to_pick,
                                        self.changes_to,
                                    ],
                                    vertical_alignment="center"
                                ),
                            ]
                        ),
                        self.extract_changes_button,
                        self.extract_selected_button,
                        self.extract_all_button
                    ],
                    col=6
                )
            ]
        )
        self.directory_progress = Row(
            controls=[
                ProgressRing(),
                Text("Loading directories...\nThis may take a minute")
            ],
            visible=False
        )
        self.files_progress = Row(
            controls=[
                ProgressRing(),
                Text("Loading files...\nThis may take a minute")
            ],
            visible=False
        )
        self.directory_list = DataTable(
            columns=[
                DataColumn(Text("Path"), on_sort=self.sort_by_path),
                DataColumn(Text("Size"), on_sort=self.sort_by_size),
                DataColumn(Text("Changed files"), on_sort=self.sort_by_changes)
            ],
            column_spacing=15,
            heading_row_height=35,
            data_row_height=25,
            sort_column_index=2,
            visible=False
        )
        self.files_list = DataTable(
            columns=[
                DataColumn(Text("Path")),
                DataColumn(Text("Size"))
            ],
            column_spacing=15,
            heading_row_height=35,
            data_row_height=25,
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
        self.extraction_progress = Column(
            controls=[
                Row(
                    controls=[
                        Text("Extractor Idle"),
                        Text("")
                    ],
                    expand=False
                ),
                ProgressBar(
                    height=30,
                    value=0
                )
            ],
            horizontal_alignment="center",
            disabled=True
        )
        self.select_all_button = ElevatedButton(
            "Select all",
            on_click=self.select_all,
            disabled=True
        )
        self.unselect_all_button = ElevatedButton(
            "Unselect all",
            on_click=self.unselect_all,
            disabled=True
        )
        self.main.controls = [
            Column(
                controls=[
                    self.main_controls
                ]
            ),
            Column(
                controls=[
                    self.extraction_progress
                ]
            ),
            Column(
                controls=[
                    Row(
                        controls=[
                            Text(f"Directory List", size=20),
                            self.select_all_button,
                            self.unselect_all_button
                        ]
                    ),
                    self.directory_progress,
                    Column(controls=[self.directory_list], height=475, scroll="auto")
                ],
                height=475,
                col=6,
                alignment=MainAxisAlignment.START
            ),
            Column(
                controls=[
                    Text("Changed/Added Files List", size=20),
                    self.files_progress,
                    Column(controls=[self.files_list], height=475, scroll="auto")
                ],
                height=475,
                col=6,
                alignment=MainAxisAlignment.START
            ),
        ]

    async def select_all(self, event):
        for row in self.directory_list.rows:
            row.selected = True
        await self.page.update_async()

    async def unselect_all(self, event):
        for row in self.directory_list.rows:
            row.selected = False
        await self.page.update_async()

    @throttle
    async def avoid_text_edit(self, event):
        event.control.value = getattr(self.locations, event.control.data)
        event.control.border_color = "red"
        event.control.error_text = "Please use directory selection button"
        await event.control.update_async()
        await asyncio.sleep(3)
        event.control.border_color = None
        event.control.error_text = None
        await event.control.update_async()

    async def sort_by_path(self, event):
        self.main.disabled = True
        await self.page.update_async()
        await asyncio.sleep(0.5)
        self.directory_list.rows.sort(key=lambda x: x.data.path, reverse=not event.ascending)
        self.directory_list.sort_ascending = event.ascending
        self.directory_list.sort_column_index = event.column_index
        self.main.disabled = False
        await self.page.update_async()

    async def sort_by_size(self, event):
        self.main.disabled = True
        await self.page.update_async()
        await asyncio.sleep(0.5)
        self.directory_list.rows.sort(
            key=lambda x: sum([f["size"] for f in x.data.files_list]),
            reverse=not event.ascending
        )
        self.directory_list.sort_ascending = event.ascending
        self.directory_list.sort_column_index = event.column_index
        self.main.disabled = False
        await self.page.update_async()

    async def sort_by_changes(self, event):
        self.main.disabled = True
        await self.page.update_async()
        await asyncio.sleep(0.5)
        self.directory_list.rows.sort(
            key=lambda x: int(x.cells[event.column_index].content.value),
            reverse=not event.ascending
        )
        self.directory_list.sort_ascending = event.ascending
        self.directory_list.sort_column_index = event.column_index
        self.main.disabled = False
        await self.page.update_async()

    async def pick_directory(self, event):
        file_picker = FilePicker(data=event.control.data, on_result=self.set_directory)
        self.page.overlay.append(file_picker)
        await self.page.update_async()
        await file_picker.get_directory_path_async(initial_directory=event.control.data)

    async def set_directory(self, event):
        if event.path is None:
            return
        if event.control.data == "extract_from":
            known_directories = [
                "audio",
                "blueprints",
                "fonts",
                "languages",
                "models",
                "movies",
                "particles",
                "prefabs",
                "shadersunified",
                "textures",
                "ui"
            ]
            for directory in known_directories:
                if not Path(event.path).joinpath(directory).exists():
                    self.page.snack_bar.content.value = "Please select a valid trove directory"
                    self.page.snack_bar.bgcolor = "red"
                    self.page.snack_bar.open = True
                    return await self.page.update_async()
            self.directory_dropdown.value = Path(event.path)
        setattr(self.locations, event.control.data, Path(event.path))
        control = getattr(self, event.control.data)
        setattr(control, "value", Path(event.path))
        self.page.preferences.save()
        await self.page.update_async()

    async def set_text_directory(self, event):
        if not event.control.value:
            return
        setattr(self.locations, event.control.data, Path(event.control.value))
        control = getattr(self, event.control.data)
        setattr(control, "value", Path(event.control.value))
        self.page.preferences.save()
        await self.page.update_async()

    async def change_directory_dropdown(self, event):
        new_path = Path(event.control.value)
        old_path = Path(self.extract_from.value)
        self.extract_from.value = str(new_path)
        for field in self.locations.__fields__:
            path = getattr(self.locations, field)
            if old_path <= path:
                set_path = new_path.joinpath(path.relative_to(old_path))
                setattr(self.locations, field, set_path)
                setattr(getattr(self, field), "value", set_path)
        self.page.preferences.save()
        await self.page.update_async()

    async def switch_advanced_mode(self, event):
        if event.control.value:
            if not self.page.preferences.dismissables.advanced_mode:
                await self.warn_advanced_mode()
        self.page.preferences.advanced_mode = event.control.value
        self.changes_to.disabled = not event.control.value
        self.changes_to_pick.disabled = not event.control.value
        self.page.preferences.save()
        await self.page.update_async()

    async def switch_performance_mode(self, event):
        if event.control.value:
            if not self.page.preferences.dismissables.performance_mode:
                await self.warn_performance_mode()
        self.page.preferences.performance_mode = event.control.value
        self.page.preferences.save()

    async def directory_selection(self, event):
        event.control.selected = not event.control.selected
        for row in self.files_list.rows:
            if row.data is not None:
                if row.data.archive.index == event.control.data:
                    row.visible = event.control.selected
        selected_indexes = [r.data for r in self.directory_list.rows if r.selected]
        changes = [f for f in self.changed_files if f.archive.index in selected_indexes]
        changes_size = sum([f.size for f in changes])
        selected_size = sum([f["size"] for r in self.directory_list.rows for f in r.data.files_list if r.selected])
        all_size = sum([f["size"] for r in self.directory_list.rows for f in r.data.files_list])
        self.extract_changes_button.text = f"Extract Changes [{naturalsize(changes_size, gnu=True)}]"
        self.extract_selected_button.text = f"Extract Selected [{naturalsize(selected_size, gnu=True)}]"
        self.extract_all_button.text = f"Extract All [{naturalsize(all_size, gnu=True)}]"
        await self.page.update_async()

    async def refresh_directories(self, _):
        self.main.disabled = True
        self.refresh_lists.start()

    @tasks.loop(seconds=1)
    async def refresh_lists(self):
        try:
            self.directory_list.rows.clear()
            self.files_list.rows.clear()
            self.extract_changes_button.disabled = False
            self.extract_selected_button.disabled = False
            self.directory_progress.visible = True
            self.directory_list.visible = False
            self.files_progress.visible = True
            self.files_list.visible = False
            await self.page.update_async()
            await asyncio.sleep(0.5)
            self.hashes = dict()
            if self.page.preferences.performance_mode:
                hashes_path = self.locations.extract_from.joinpath("hashes.json")
                if hashes_path.exists():
                    self.hashes = json.loads(hashes_path.read_text())
            self.changed_files = []
            indexes = [[index, len(index.files_list), 0] for index in find_all_indexes(self.locations.extract_from, self.hashes, False)]
            for i, file in enumerate(
                find_changes(
                    self.locations.extract_from, self.locations.extract_to, self.hashes)
            ):
                self.changed_files.append(file)
            if self.changed_files:
                self.changed_files.sort(key=lambda x: [x.archive.index.path, x.path])
                for file in self.changed_files:
                    for index in indexes:
                        if index[0] == file.archive.index:
                            index[2] += 1
                            break
            else:
                self.extract_changes_button.disabled = True
                self.extract_selected_button.disabled = True
            indexes.sort(key=lambda x: [-x[2], str(x[0].directory)])
            for index, files_count, changes_count in indexes:
                self.directory_list.rows.append(
                    DataRow(
                        data=index,
                        cells=[
                            DataCell(
                                Text(
                                    str(index.directory.relative_to(self.locations.extract_from)),
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
                        on_select_changed=self.directory_selection,
                    )
                )
            if len(self.changed_files) > 2000:
                self.files_list.rows.append(
                    DataRow(
                        cells=[
                            DataCell(Text("Too many changes to be displayed.", color="red")),
                            DataCell(Text(""))
                        ]
                    )
                )
            elif len(self.changed_files) == 0:
                self.files_list.rows.append(
                    DataRow(
                        cells=[
                            DataCell(Text("No changed files found.")),
                            DataCell(Text(""))
                        ]
                    )
                )
                self.extract_changes_button.disabled = True
            else:
                for file in self.changed_files:
                    self.files_list.rows.append(
                        DataRow(
                            data=file,
                            cells=[
                                DataCell(
                                    Text(
                                        file.path.relative_to(self.locations.extract_from),
                                        color=file.color,
                                        size=12
                                    )
                                ),
                                DataCell(
                                    Text(
                                        naturalsize(file.size, gnu=True),
                                        color=file.color,
                                        size=12
                                    )
                                )
                            ]
                        )
                    )
                self.extract_changes_button.disabled = False
            selected_indexes = [r.data for r in self.directory_list.rows if r.selected]
            changes = [f for f in self.changed_files if f.archive.index in selected_indexes]
            changes_size = sum([f.size for f in changes])
            selected_size = sum([f["size"] for r in self.directory_list.rows for f in r.data.files_list if r.selected])
            all_size = sum([f["size"] for r in self.directory_list.rows for f in r.data.files_list])
            self.extract_changes_button.text = f"Extract Changes [{naturalsize(changes_size, gnu=True)}]"
            self.extract_selected_button.text = f"Extract Selected [{naturalsize(selected_size, gnu=True)}]"
            self.extract_all_button.text = f"Extract All [{naturalsize(all_size, gnu=True)}]"
            self.metrics.controls[0].controls[1].value = naturalsize(sum([f.size for f in self.changed_files]), gnu=True)
            self.extract_changes_button.disabled = False
            self.extract_selected_button.disabled = False
            self.select_all_button.disabled = False
            self.unselect_all_button.disabled = False
            self.extract_all_button.disabled = False
            self.directory_progress.visible = False
            self.directory_list.visible = True
            self.files_progress.visible = False
            self.files_list.visible = True
            self.main.disabled = False
            await self.page.update_async()
            self.refresh_lists.cancel()
        except Exception as e:
            print(e)

    async def warn_advanced_mode(self):
        task_lines = [
            "Advanced mode allows for people to have old vs new changed files in a separate directory",
            "This will provide a better way to compare updates whilst having no real hustle to separate these changes",
            "Eliminating the need of 1gb folders for each update and keeping it streamlined to the true changes"
        ]
        task = "\n\n".join(task_lines)
        dlg = AlertDialog(
            modal=False,
            title=Text("Advanced mode enabled"),
            content=Text(task),
            actions=[
                ElevatedButton("Don't show again", on_click=self.am_dont_show),
                ElevatedButton("Ok", on_click=self.close_dlg)
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        await self.page.update_async()

    async def warn_performance_mode(self):
        task_lines = [
            "Performance mode is a very sensitive mode, it will create a cache of some of the file's data and improve "
            "performance of changes detection beyond imaginable",
            "But it comes with the caveat that it will have the wrong results if you use any other tool, "
            "this is because it won't have the information that an extraction or update happened, so when trying to "
            "track changes through this cache it will assume a state that may not match."
            "If you only plan to use this tool as your only extraction method, you may enable this with no worry"
            "If you plan on using any other extraction method however, be weary of the issues this cache may present "
            "to the accuracy of change tracking."
            "Even out of performance mode, this app will most likely manage faster speeds than other methods (I know "
            "of)."
        ]
        task = "\n\n".join(task_lines)
        dlg = AlertDialog(
            modal=False,
            title=Text("Performance mode enabled"),
            content=Text(task),
            actions=[
                ElevatedButton("Don't show again", on_click=self.pm_dont_show),
                ElevatedButton("Ok", on_click=self.close_dlg)
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        await self.page.update_async()

    async def pm_dont_show(self, _):
        self.page.preferences.dismissables.performance_mode = True
        self.page.preferences.save()
        self.page.dialog.open = False
        await self.page.update_async()

    async def am_dont_show(self, _):
        self.page.preferences.dismissables.advanced_mode = True
        self.page.preferences.save()
        self.page.dialog.open = False
        await self.page.update_async()

    async def close_dlg(self, _):
        self.page.dialog.open = False
        await self.page.update_async()

    async def warn_extraction(self, extraction_type: str):
        task = f"Do you really wish to extract {extraction_type} from {self.locations.extract_from} into {self.locations.extract_to}"
        if self.page.preferences.advanced_mode:
            task += f"\nWhilst keeping track of changes in a versioned folder in {self.locations.changes_to}"
        dlg = AlertDialog(
            modal=False,
            title=Text("Extraction confirmation"),
            content=Text(task),
            actions=[
                ElevatedButton("Cancel", on_click=self.close_dlg),
                ElevatedButton("Confirm extraction", data=extraction_type, on_click=self.extract),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        await self.page.update_async()

    async def extract_changes(self, _):
        await self.warn_extraction("changes")

    async def extract_selected(self, _):
        await self.warn_extraction("selected")

    async def extract_all(self, _):
        await self.warn_extraction("all")

    async def extract(self, event):
        self.page.dialog.open = False
        self.main.disabled = True
        await self.page.update_async()
        await asyncio.sleep(0.5)
        if event.control.data == "changes":
            dated_folder = self.locations.changes_to.joinpath(datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
            old_changes = dated_folder.joinpath("old")
            new_changes = dated_folder.joinpath("new")
            dated_folder.mkdir(parents=True, exist_ok=True)
            old_changes.mkdir(parents=True, exist_ok=True)
            new_changes.mkdir(parents=True, exist_ok=True)
            selected_indexes = [r.data for r in self.directory_list.rows if r.selected]
            changes = [f for f in self.changed_files if f.archive.index in selected_indexes]
            total = len(changes)
            # This in case they want to re-run the extraction, possible
            with open(old_changes.joinpath("hashes.json"), "w+") as f:
                f.write(json.dumps(self.hashes, indent=4))
            for i, file in enumerate(changes, 1):
                old_pro = self.extraction_progress.controls[1].value
                i += 1
                if old_pro != (progress := round(i/total*100)/100):
                    self.extraction_progress.controls[0].controls[0].value = f"[{round(progress * 100, 2)}%] Extracting changes:"
                    self.extraction_progress.controls[0].controls[1].value = file.name
                    self.extraction_progress.controls[1].value = progress
                    await self.extraction_progress.update_async()
                    await asyncio.sleep(0.1)
                if self.page.preferences.advanced_mode:
                    # Keep an old copy for comparisons
                    file.copy_old(self.locations.extract_from, self.locations.extract_to, old_changes)
                    # Add changes
                    file.save(self.locations.extract_from, new_changes)
                    # Save into extracted location
                    file.save(self.locations.extract_from, self.locations.extract_to)
                index_relative_path = file.archive.index.path.relative_to(self.locations.extract_from)
                archive_relative_path = file.archive.path.relative_to(self.locations.extract_from)
                self.hashes[str(index_relative_path)] = file.archive.index.content_hash
                self.hashes[str(archive_relative_path)] = file.archive.content_hash
            with open(self.locations.extract_from.joinpath("hashes.json"), "w+") as f:
                f.write(json.dumps(self.hashes, indent=4))
        elif event.control.data in ["all", "selected"]:
            if event.control.data == "all":
                indexes = [r.data for r in self.directory_list.rows]
            elif event.control.data == "selected":
                indexes = [r.data for r in self.directory_list.rows if r.selected]
            number_of_files = sum([len(index.files_list) for index in indexes])
            i = 0
            for index in indexes:
                index_relative_path = index.path.relative_to(self.locations.extract_from)
                self.hashes[str(index_relative_path)] = index.content_hash
                for archive in index.archives:
                    archive_relative_path = archive.path.relative_to(self.locations.extract_from)
                    self.hashes[str(archive_relative_path)] = archive.content_hash
                    for file in archive.files():
                        old_pro = self.extraction_progress.controls[1].value
                        i += 1
                        if old_pro != (progress := round(i/number_of_files*100)/100):
                            self.extraction_progress.controls[0].controls[0].value = f"[{round(progress * 100, 2)}%] Extracting {event.control.data}:"
                            self.extraction_progress.controls[0].controls[1].value = file.name
                            self.extraction_progress.controls[1].value = progress
                            await self.extraction_progress.update_async()
                            await asyncio.sleep(0.1)
                        file.save(self.locations.extract_from, self.locations.extract_to)
            with open(self.locations.extract_from.joinpath("hashes.json"), "w+") as f:
                f.write(json.dumps(self.hashes, indent=4))
        self.extraction_progress.controls[0].controls[0].value = "Extractor Idle"
        self.extraction_progress.controls[0].controls[1].value = ""
        self.page.snack_bar.content.value = "Extraction Complete"
        self.page.snack_bar.bgcolor = "green"
        self.page.snack_bar.open = True
        await self.page.update_async()
        # Refresh changes
        self.refresh_lists.start()

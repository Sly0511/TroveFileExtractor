import winreg
from pathlib import Path
from vdf import parse


hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
nodes = ["WOW6432Node\\"]
trove_path = "Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
trove_key = "Glyph Trove"
trove_install_value = "InstallLocation"
steam_path = "Valve\\"
steam_key = "Steam"
steam_install_value = "InstallPath"
steam_trove_id = "304050"


def GetKeys(key, path, look_for):
    i = 0
    while True:
        try:
            subkey = winreg.EnumKey(key, i)
            if subkey.startswith(look_for):
                yield path + subkey + "\\"
        except WindowsError:
            break
        i += 1


def SearchGlyphRegistry():
    for hive in hives:
        for node in nodes:
            try:
                look_path = "SOFTWARE\\" + node + trove_path
                registry_key_path = winreg.OpenKeyEx(hive, look_path)
                keys = GetKeys(registry_key_path, look_path, trove_key)
                for Key in keys:
                    yield winreg.OpenKeyEx(hive, Key)
            except WindowsError:
                ...


def SearchSteamRegistry():
    for hive in hives:
        for node in nodes:
            try:
                look_path = "SOFTWARE\\" + node + steam_path
                registry_key_path = winreg.OpenKeyEx(hive, look_path)
                keys = GetKeys(registry_key_path, look_path, steam_key)
                for key in keys:
                    yield winreg.OpenKeyEx(hive, key)
            except WindowsError:
                ...


def GetTroveLocations():
    for key in SearchGlyphRegistry():
        try:
            game_path = winreg.QueryValueEx(key, trove_install_value)[0]
        except WindowsError:
            continue
        yield ["Glyph", Path(game_path)]
    steam_path = None
    for key in SearchSteamRegistry():
        try:
            steam_path = Path(winreg.QueryValueEx(key, steam_install_value)[0])
        except WindowsError:
            continue
    if steam_path is not None and steam_path.exists():
        config_path = steam_path.joinpath("config/libraryfolders.vdf")
        config = parse(open(config_path))
        library_folders = [
            Path(v["path"]).joinpath("steamapps\common\Trove\Games\Trove")
            for v in config["libraryfolders"].values()
            if isinstance(v, dict)
        ]
        servers = ["Live", "PTS"]
        for library in library_folders:
            for server in servers:
                game_path = library.joinpath(server)
                exe_path = game_path.joinpath("Trove.exe")
                if exe_path.exists():
                    yield ["Steam", game_path]

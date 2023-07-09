from cx_Freeze import setup, Executable
from main import (
    AUTHOR,
    NAME,
    TECH_NAME,
    VERSION,
    DESCRIPTION,
    ICON,
    COPYRIGHT,
    APP_ID
)

build_exe_options = {
    "excludes": [
        "wheel",
        "cx_Freeze",
    ],
    "include_files": [
        ("assets/", "assets/"),
        ("README.md", "README.md"),
        ("LICENSE", "LICENSE"),
    ],
    "optimize": 2,
}

bdist_msi_options = {
    "target_name": TECH_NAME,
    "upgrade_code": APP_ID,
    "add_to_path": False,
    "install_icon": ICON,
    "all_users": True,
}

options = {"build_exe": build_exe_options, "bdist_msi": bdist_msi_options}

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    url=f"https://github.com/Sly0511/{TECH_NAME}",
    description=NAME,
    options=options,
    executables=[
        Executable(
            "main.py",
            target_name=f"{TECH_NAME}.exe",
            icon=ICON,
            base="Win32GUI",
            copyright=f"{AUTHOR} {COPYRIGHT}",
            shortcut_name=NAME,
            shortcut_dir="DesktopFolder",
        )
    ],
)

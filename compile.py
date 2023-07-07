from cx_Freeze import setup, Executable


# Metadata
author = "sly.dev"
name = "Trove File Extractor"
tech_name = "TroveFileExtractor"
version = "1.0.0"
description = "A tool for extraction of Trove Archive files"
icon = "assets/favicon.ico"
copyright = "2023-Present"
app_id = "{0b903f43-d5d0-4852-80e6-25715762039f}"

build_exe_options = {
    "excludes": [
        "wheel",
        "cx_Freeze",
    ],
    "include_files": [
        ("assets/", "assets/"),
        ("README.md", "README.md"),
    ]
}

bdist_msi_options = {
    'target_name': "TroveFileExtractor.msi",
    'upgrade_code': app_id,
    'add_to_path': False,
    'install_icon': icon,
    'all_users': True,
}

options = {
    'build_exe': build_exe_options,
    'bdist_msi': bdist_msi_options
}

setup(
    name=name,
    version=version,
    author=author,
    url=f"https://github.com/Sly0511/{tech_name}",
    description=name,
    options=options,
    executables=[
        Executable(
            "main.py",
            target_name=f"{tech_name}.exe",
            icon=icon,
            base="Win32GUI",
            copyright=f"{author} {copyright}",
            shortcut_name=name,
            shortcut_dir="DesktopFolder",
        )
    ],
)

from __future__ import annotations

import re
import zlib
from enum import Enum
from pathlib import Path
from typing import Generator, Optional

from binary_reader import BinaryReader
from copy import copy
from hashlib import md5


archive_id = re.compile(r"^archive(\d+)")


class FileStatus(Enum):
    unchanged = "Unchanged"
    added = "Added"
    changed = "Changed"
    removed = "Removed"


class TroveFile:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)
        self._content: Optional[bytes] = None
        self._content_hash: Optional[str] = None
        self._status: Optional[FileStatus] = None

    @classmethod
    def parse_obj(cls, data):
        return cls(**data)

    @property
    def status(self):
        return self._status

    @property
    def color(self):
        if self.status == FileStatus.unchanged:
            return None
        if self.status == FileStatus.added:
            return "green"
        if self.status == FileStatus.changed:
            return "yellow"
        if self.status == FileStatus.removed:
            return "red"

    @property
    def content_hash(self):
        if self._content is None:
            _ = self.content
        return self._content_hash

    @property
    def content(self):
        if self._content is None:
            reader = BinaryReader(self.archive.content)
            reader.seek(self.offset)
            self._content = reader.read_bytes(self.size)
            self._content_hash = md5(self.content).hexdigest()
        return self._content

    def extracted_path(self, opath: Path, path: Path) -> Path:
        return path.joinpath(self.path.relative_to(opath))

    def extract_to_path(self, opath: Path, path: Path) -> Path:
        return path.joinpath(self.path.relative_to(opath))

    def compare(self, opath: Path, path: Path) -> FileStatus:
        extracted_file = self.extracted_path(opath, path)
        if not extracted_file.exists():
            self._status = FileStatus.added
        elif self.content_hash == md5(extracted_file.read_bytes()).hexdigest():
            self._status = FileStatus.unchanged
        else:
            self._status = FileStatus.changed
        return self.status

    def save(self, opath: Path, path: Path):
        path_to_save = self.extract_to_path(opath, path)
        parent = path_to_save.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        with open(path_to_save, "wb") as f:
            f.write(self.content)


class TFArchive:
    def __init__(self, index: TFIndex, path: Path):
        self.index = index
        self.directory = path.parent
        self.path = path
        self.id = int(archive_id.search(path.stem).group(1))
        self._content = None
        self._content_hash: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, TFIndex):
            return False
        return self.path == other.path

    def __ne__(self, other):
        return not self.__eq__(other)

    def __int__(self):
        return self.id

    def __str__(self):
        return f"<path={str(self.path)}>"

    def __repr__(self):
        return self.__str__()

    @property
    def content_hash(self):
        if self._content is None:
            _ = self.content
        return self._content_hash

    @property
    def content(self):
        if self._content is None:
            data = zlib.decompressobj(wbits=zlib.MAX_WBITS)
            self._content = data.decompress(self.path.read_bytes())
            self._content_hash = md5(self._content).hexdigest()
        return self._content

    def files(self) -> Generator[TroveFile]:
        for file in self.index.files_list:
            if file["archive_index"] == int(self):
                copy_file = copy(file)
                copy_file["archive"] = self
                yield TroveFile.parse_obj(copy_file)


class TFIndex:
    def __init__(self, file: Path):
        self.directory = file.parent
        self.path = file
        self._files = []
        self._content = None
        self._content_hash: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, TFIndex):
            return False
        return self.path == other.path

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f"<path={str(self.path)}>"

    def __repr__(self):
        return self.__str__()

    @property
    def content_hash(self):
        if self._content is None:
            _ = self.content
        return self._content_hash

    @property
    def content(self):
        if self._content is None:
            self._content = self.path.read_bytes()
            self._content_hash = md5(self._content).hexdigest()
        return self._content

    @property
    def archives(self) -> Generator[TFArchive]:
        for archive in self.directory.glob("*.tfa"):
            yield TFArchive(self, archive)

    @property
    def files_list(self) -> list[dict]:
        if not self._files:
            self._files.extend(
                list(self.get_files_list())
            )
        return self._files

    def get_files_list(self) -> Generator[dict]:
        reader = BinaryReader(self.content)
        while reader.pos() < reader.size():
            file = dict()
            file["name"] = reader.read_str(ReadVarInt7Bit(reader, reader.pos()))
            file["path"] = self.directory.joinpath(file["name"])
            file["archive_index"] = ReadVarInt7Bit(reader, reader.pos())
            file["offset"] = ReadVarInt7Bit(reader, reader.pos())
            file["size"] = ReadVarInt7Bit(reader, reader.pos())
            file["hash"] = ReadVarInt7Bit(reader, reader.pos())
            yield file


def find_all_indexes(path: Path, hashes: dict, track_changes=True) -> Generator[TFIndex]:
    for index_file in path.rglob("index.tfi"):
        index = TFIndex(index_file)
        if not track_changes:
            yield index
            continue
        hash = hashes.get(str(index.path.relative_to(path)))
        if hash is None or index.content_hash != hash:
            yield index


def find_all_archives(path: Path, hashes: dict) -> Generator[TFArchive]:
    for index in find_all_indexes(path, hashes):
        for archive in index.archives:
            opath = archive.path.relative_to(path)
            hash = hashes.get(opath)
            if hash is None or archive.content_hash != hash:
                yield archive


def find_all_files(path: Path, hashes: dict) -> Generator[TroveFile]:
    for archive in find_all_archives(path, hashes):
        for i, file in enumerate(archive.files()):
            yield file


def find_changes(archive_path: Path, extracted_path: Path, hashes: dict) -> Generator[TroveFile]:
    for file in find_all_files(archive_path, hashes):
        if file.compare(archive_path, extracted_path) in [
            FileStatus.added,
            FileStatus.changed
        ]:
            yield file


def ReadVarInt7Bit(buffer: BinaryReader, pos):
    result = 0
    shift = 0
    while 1:
        buffer.seek(pos)
        b = buffer.read_bytes()
        for i, byte in enumerate(b):
            result |= ((byte & 0x7f) << shift)
            pos += 1
            if not (byte & 0x80):
                result &= (1 << 32) - 1
                result = int(result)
                return result
            shift += 7
            if shift >= 64:
                raise Exception('Too many bytes when decoding varint.')

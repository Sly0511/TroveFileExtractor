from __future__ import annotations

import asyncio
import random
import re
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from typing import TypeVar, Literal, Generic, Callable, overload, Union

from binary_reader import BinaryReader
from pydantic import BaseModel


archive_id = re.compile(r"^archive(\d+)")


T = TypeVar("T", bool, Literal[True], Literal[False])


class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self):
        return "..."


class ExponentialBackoff(Generic[T]):
    def __init__(self, base: int = 1, *, integral: T = False):
        self._base: int = base
        self._exp: int = 0
        self._max: int = 10
        self._reset_time: int = base * 2**11
        self._last_invocation: float = time.monotonic()
        rand = random.Random()
        rand.seed()
        self._randfunc: Callable[..., Union[int, float]] = (
            rand.randrange if integral else rand.uniform
        )

    @overload
    def delay(self: ExponentialBackoff[Literal[False]]) -> float:
        ...

    @overload
    def delay(self: ExponentialBackoff[Literal[True]]) -> int:
        ...

    @overload
    def delay(self: ExponentialBackoff[bool]) -> Union[int, float]:
        ...

    def delay(self) -> Union[int, float]:
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation
        if interval > self._reset_time:
            self._exp = 0
        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2**self._exp)


def compute_timedelta(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.now(timezone.utc)
    return max((dt - now).total_seconds(), 0)


class TFArchive:
    def __init__(self, index: "TFIndex", file: Path):
        self.index = index
        self.directory = file.parent
        self.path = file
        self.id = int(archive_id.search(file.stem).group(1))
        self.content = file.read_bytes()
        #self.read_file_content()

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

    def read_file_content(self):
        reader = BinaryReader(self.content)
        data = zlib.decompressobj(wbits=zlib.MAX_WBITS)
        reader = BinaryReader(data.decompress(reader.buffer()))
        for file in self.index.files:
            if file.archive_index == int(self):
                reader.seek(file.offset)
                if file.size > 0:
                    file.content = reader.read_byte=s(file.size)
                else:
                    file.content = b""


class TroveFile(BaseModel):
    name: str
    path: Path
    archive_index: int
    offset: int
    size: int
    hash: str
    content: Optional[bytes] = None


class TFIndex:
    def __init__(self, file: Path):
        self.directory = file.parent
        self.path = file
        self.content = file.read_bytes()
        self.archives: list[TFArchive] = []
        self.read_archives()
        self.read_files()

    def __eq__(self, other):
        if not isinstance(other, TFIndex):
            return False
        return self.path == other.path

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f"<path={str(self.path)} files={len(self.files)}>"

    def __repr__(self):
        return self.__str__()

    def read_archives(self):
        self.archives.clear()
        for tfa in FindTFA(self.directory):
            self.archives.append(TFArchive(self, tfa))


    def read_files(self):
        reader = BinaryReader(self.content)
        while reader.pos() < reader.size():
            file = {}
            file["name"] = reader.read_str(ReadVarInt7Bit(reader, reader.pos())[0])
            file["path"] = self.directory.joinpath(file["name"])
            file["archive_index"] = ReadVarInt7Bit(reader, reader.pos())[0]
            file["offset"] = ReadVarInt7Bit(reader, reader.pos())[0]
            file["size"] = ReadVarInt7Bit(reader, reader.pos())[0]
            file["hash"] = ReadVarInt7Bit(reader, reader.pos())[0]


def FindTFA(directory: Path):
    if directory.is_file():
        raise Exception("Please give a directory, not a file.")
    for tfa in directory.glob("*.tfa"):
        yield tfa


def FindTFI(directory: Path):
    if directory.is_file():
        raise Exception("Please give a directory, not a file.")
    i = 0  # TODO: Remove this in prod
    for tfi in directory.rglob("*.tfi"):
        i += 1  # TODO: Remove this in prod
        yield TFIndex(tfi)
        if i == 4:  # TODO: Remove this in prod
            break  # TODO: Remove this in prod


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
                return (result, pos)
            shift += 7
            if shift >= 64:
                raise Exception('Too many bytes when decoding varint.')
    return result


def throttle(actual_handler, data={}, delay=0.5):
    """Throttles a function from running using python's memory gimmicks.

    This solves a race condition for searches to the database and loading data into the UI.
    Now you see Python will use that dict object for all the functions that run this decorator.
    Which means all delay times are shared, not ideal but saves the time of setting up the variables.
    Ideally I would not rely on this Python gimmick as it might change in the future.
    If for some reason this stopped working, check if python still defines and uses same dict object upon...
    ...function definition.

    I did not get a degree, don't sue me"""

    async def wrapper(*args, **kwargs):
        """Simple filter for queries that shouldn't run."""

        data["last_change"] = datetime.utcnow().timestamp()
        await asyncio.sleep(delay)
        if (
            datetime.utcnow().timestamp() - data["last_change"]
            >= delay - delay * 0.1
        ):
            await actual_handler(*args, **kwargs)

    return wrapper


def long_throttle(actual_handler, data={}, delay=1.5):
    """Throttles a function from running using python's memory gimmicks.

    This solves a race condition for searches to the database and loading data into the UI.
    Now you see Python will use that dict object for all the functions that run this decorator.
    Which means all delay times are shared, not ideal but saves the time of setting up the variables.
    Ideally I would not rely on this Python gimmick as it might change in the future.
    If for some reason this stopped working, check if python still defines and uses same dict object upon...
    ...function definition.

    I did not get a degree, don't sue me"""

    async def wrapper(*args, **kwargs):
        """Simple filter for queries that shouldn't run."""

        data["last_change"] = datetime.utcnow().timestamp()
        await asyncio.sleep(delay)
        if (
            datetime.utcnow().timestamp() - data["last_change"]
            >= delay - delay * 0.1
        ):
            await actual_handler(*args, **kwargs)

    return wrapper

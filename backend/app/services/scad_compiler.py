"""Компиляция SCAD-кода в STL и измерение сетки (инфраструктура).

Блокирующий I/O (subprocess openscad, парсинг STL) выносится из потока
события через asyncio.to_thread. Домен получает только чистые метрики
(app.domain.engine.scad_metrics.MeshMeasurements).

Порядок поиска бинарника: APP_OPENSCAD_BIN -> backend/vendor/openscad-*
(ставится scripts/download_openscad.ps1) -> PATH -> Program Files.
"""

import asyncio
import hashlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.domain.engine.scad_metrics import MeshMeasurements

_CREATE_NO_WINDOW = 0x08000000
_STDERR_TAIL_CHARS = 500

# include/use/import/surface тянут внешние файлы — изоляция ФС сервера
_FILE_IO_PATTERN = re.compile(
    r"(^\s*(include|use)\s*<)|(\b(import|surface)\s*\()", re.MULTILINE
)


class ScadUnavailableError(Exception):
    """Бинарник OpenSCAD не найден или SCAD-режим выключен конфигом."""


class ScadCompileError(Exception):
    """Код отклонён санитизацией либо компиляция завершилась ошибкой."""


@dataclass(frozen=True)
class CompiledStl:
    code_hash: str
    stl_bytes: bytes
    compile_ms: int


@lru_cache(maxsize=1)
def resolve_openscad_binary() -> str | None:
    """Автопоиск бинарника; результат кэшируется на процесс."""
    candidates: list[str] = []
    if settings.openscad_bin:
        candidates.append(settings.openscad_bin)
    # backend/vendor/openscad-<version>/ — новейшая версия первой
    vendor_root = Path(__file__).resolve().parents[2] / "vendor"
    if vendor_root.is_dir():
        names = (
            ["openscad.com", "openscad.exe"]
            if sys.platform == "win32"
            else ["openscad"]
        )
        for entry in sorted(vendor_root.glob("openscad-*"), reverse=True):
            candidates.extend(str(entry / name) for name in names)
    for name in ("openscad", "openscad.com"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    if sys.platform == "win32":
        candidates.append(r"C:\Program Files\OpenSCAD\openscad.com")
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def is_available() -> bool:
    """Capability-флаг для /scad/capability и скрытия SCAD-режимов фронтом."""
    return settings.openscad_enabled and resolve_openscad_binary() is not None


def _validate_code(code: str) -> None:
    if not code.strip():
        raise ScadCompileError("Пустой scad_code")
    size = len(code.encode("utf-8"))
    if size > settings.scad_max_code_bytes:
        raise ScadCompileError(
            f"Код SCAD {size} байт превышает лимит {settings.scad_max_code_bytes}"
        )
    if settings.scad_block_file_io and _FILE_IO_PATTERN.search(code):
        raise ScadCompileError("include/use/import/surface запрещены в scad_code")


@lru_cache(maxsize=4)
def _backend_flags(binary: str) -> tuple[str, ...]:
    """Флаг ядра рендера: сборки >=2024 получают --backend=Manifold
    (CGAL 2021.01 рендерит реальные детали минутами, Manifold — секунды)."""
    try:
        if sys.platform == "win32":
            proc = subprocess.run(  # noqa: S603
                [binary, "--version"],
                capture_output=True,
                timeout=10,
                creationflags=_CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.run(  # noqa: S603
                [binary, "--version"],
                capture_output=True,
                timeout=10,
            )
        output = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    except (subprocess.TimeoutExpired, OSError):
        return ()
    match = re.search(r"20\d{2}", output)
    if match and int(match.group(0)) >= 2024:
        return ("--backend=Manifold",)
    return ()


def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
    """Убивает процесс-дерево: на Windows потомки держат дескрипторы
    stdout/stderr родителя и переживают proc.kill()."""
    if sys.platform == "win32":
        subprocess.run(  # noqa: S603 — служебный вызов taskkill
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
        )
    else:
        proc.kill()


def _compile_sync(code: str) -> CompiledStl:
    _validate_code(code)
    binary = resolve_openscad_binary()
    if binary is None:
        raise ScadUnavailableError(
            "Бинарник OpenSCAD не найден (APP_OPENSCAD_BIN, backend/vendor, "
            "PATH, Program Files); выполните scripts/download_openscad.ps1"
        )
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="qcs-scad-") as tmp:
        tmp_dir = Path(tmp)
        scad_path = tmp_dir / "part.scad"
        stl_path = tmp_dir / "part.stl"
        err_path = tmp_dir / "stderr.log"
        scad_path.write_text(code, encoding="utf-8")
        command = [
            binary,
            *_backend_flags(binary),
            # CLI по умолчанию выгружает ASCII STL (~660 байт/фасет) — в ~6.5×
            # тяжелее бинарного (50 байт/фасет) при той же сетке; без binstl
            # лимит APP_SCAD_MAX_STL_MB срабатывает на текстовый объём, а не на
            # сложность модели. Обе vendor-сборки (2021.01 и 2026.11) поддерживают.
            "--export-format",
            "binstl",
            "-o",
            str(stl_path),
            str(scad_path),
        ]
        popen_kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            popen_kwargs["start_new_session"] = True
        # stderr в файл, не в pipe: после kill дерева нечему «висеть» на чтении
        started = time.perf_counter()
        with open(err_path, "wb") as err_file:
            proc = subprocess.Popen(  # noqa: S603 — путь из доверенного конфига
                command, stdout=err_file, stderr=err_file, **popen_kwargs
            )
            try:
                returncode = proc.wait(timeout=settings.openscad_timeout_s)
            except subprocess.TimeoutExpired as exc:
                _kill_tree(proc)
                proc.wait(timeout=10)
                raise ScadCompileError(
                    f"Компиляция OpenSCAD превысила {settings.openscad_timeout_s} с "
                    "— упростите модель (снизьте $fn, меньше булевых операций) "
                    "или увеличьте APP_OPENSCAD_TIMEOUT_S"
                ) from exc
        compile_ms = int((time.perf_counter() - started) * 1000)
        stderr = err_path.read_bytes().decode("utf-8", "replace").strip()
        if returncode != 0 or not stl_path.is_file():
            detail = stderr[-_STDERR_TAIL_CHARS:] if stderr else "без вывода stderr"
            raise ScadCompileError(f"Ошибка компиляции OpenSCAD: {detail}")
        stl_bytes = stl_path.read_bytes()
    if len(stl_bytes) > settings.scad_max_stl_mb * 1024 * 1024:
        raise ScadCompileError(
            f"STL больше лимита {settings.scad_max_stl_mb} МБ — снизьте "
            "$fn (обычно достаточно 72–256) или $fs, сократите число "
            "булевых операций; лимит меняется APP_SCAD_MAX_STL_MB"
        )
    return CompiledStl(code_hash=code_hash, stl_bytes=stl_bytes, compile_ms=compile_ms)


@lru_cache(maxsize=32)
def _compile_cached(code: str) -> CompiledStl:
    """LRU по тексту кода: поворот ползунка Customizer бьёт в кэш."""
    return _compile_sync(code)


def _measure_sync(stl_bytes: bytes) -> MeshMeasurements:
    import trimesh

    mesh = trimesh.load_mesh(io.BytesIO(stl_bytes), file_type="stl")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    if mesh is None or len(mesh.faces) == 0:
        raise ScadCompileError("Пустой меш: модель не содержит геометрии")
    extents = mesh.extents
    return MeshMeasurements(
        extents_mm=(float(extents[0]), float(extents[1]), float(extents[2])),
        volume_mm3=abs(float(mesh.volume)),
        area_mm2=float(mesh.area),
    )


async def compile_and_measure(code: str) -> tuple[CompiledStl, MeshMeasurements]:
    """Компилирует код и меряет STL; блокирущие шаги — в рабочем потоке."""
    compiled = await asyncio.to_thread(_compile_cached, code)
    measurements = await asyncio.to_thread(_measure_sync, compiled.stl_bytes)
    return compiled, measurements

#!/usr/bin/env python3

import json
import os
import pathlib
import shlex
import sys
import urllib.request
from urllib.parse import urlparse


CE_URL = os.environ.get(
    "CE_URL",
    "http://localhost:10240",
).rstrip("/")

COMPILER_ID = os.environ.get(
    "CE_COMPILER_ID",
    "custom-clang-22-1-8",
)


def fail(message: str) -> None:
    print(f"Compiler Explorer: {message}", file=sys.stderr)
    sys.exit(1)


def normalize(path: pathlib.Path) -> pathlib.Path:
    try:
        return path.resolve(strict=True)
    except FileNotFoundError:
        return path.resolve()


def load_compile_commands(
    path: pathlib.Path,
) -> list[dict]:
    if not path.exists():
        fail(f"compile_commands.json not found: {path}")

    try:
        with path.open() as f:
            return json.load(f)
    except Exception as exc:
        fail(f"could not read {path}: {exc}")


def find_compile_entry(
    source_file: pathlib.Path,
    commands: list[dict],
) -> dict | None:
    wanted = normalize(source_file)

    for entry in commands:
        directory = pathlib.Path(entry["directory"])

        file_path = pathlib.Path(entry["file"])

        if not file_path.is_absolute():
            file_path = directory / file_path

        if normalize(file_path) == wanted:
            return entry

    return None


def make_absolute(
    value: str,
    directory: pathlib.Path,
) -> str:
    path = pathlib.Path(value)

    if path.is_absolute():
        return str(path)

    return str((directory / path).resolve())


def compile_arguments(entry: dict) -> list[str]:
    if "arguments" in entry:
        return list(entry["arguments"])

    if "command" in entry:
        return shlex.split(entry["command"])

    return []


def extract_flags(
    entry: dict,
    source_file: pathlib.Path,
) -> list[str]:
    args = compile_arguments(entry)

    if not args:
        return []

    directory = pathlib.Path(entry["directory"])

    # First argument is normally clang++, g++, etc.
    args = args[1:]

    result: list[str] = []

    i = 0

    while i < len(args):
        arg = args[i]

        # Remove compile-only option.
        if arg in ("-c", "--compile"):
            i += 1
            continue

        # Remove output filename.
        if arg == "-o":
            i += 2
            continue

        if arg.startswith("-o") and len(arg) > 2:
            i += 1
            continue

        # Remove dependency-generation output options.
        if arg in ("-MF", "-MT", "-MQ"):
            i += 2
            continue

        # Remove actual source filename.
        candidate = pathlib.Path(arg)

        if not arg.startswith("-"):
            if not candidate.is_absolute():
                candidate = directory / candidate

            if normalize(candidate) == normalize(source_file):
                i += 1
                continue

        # Handle -Ifoo
        if arg.startswith("-I") and len(arg) > 2:
            include = arg[2:]

            result.append("-I" + make_absolute(include, directory))

            i += 1
            continue

        # Handle:
        #
        #   -I foo
        #   -isystem foo
        #   -iquote foo
        #
        if arg in ("-I", "-isystem", "-iquote"):
            if i + 1 >= len(args):
                break

            result.append(arg)

            result.append(
                make_absolute(
                    args[i + 1],
                    directory,
                )
            )

            i += 2
            continue

        result.append(arg)
        i += 1

    return result


def quote_flags(flags: list[str]) -> str:
    return " ".join(shlex.quote(flag) for flag in flags)


def create_ce_state(
    source: str,
    options: str,
) -> dict:
    return {
        "sessions": [
            {
                "id": 1,
                "language": "c++",
                "source": source,
                "compilers": [
                    {
                        "id": COMPILER_ID,
                        "options": options,
                    }
                ],
            }
        ]
    }


def create_shortlink(state: dict) -> str:
    payload = json.dumps(state).encode("utf-8")

    request = urllib.request.Request(
        f"{CE_URL}/api/shortener",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            result = json.loads(response.read().decode("utf-8"))

    except Exception as exc:
        fail(f"could not contact Compiler Explorer at {CE_URL}: {exc}")

    returned_url = result.get("url")

    if not returned_url:
        fail(f"unexpected shortener response: {result}")

    #
    # The shortener might return an absolute URL.
    # Keep the /z/<id> part but force our local CE host.
    #
    parsed = urlparse(returned_url)

    if parsed.path.startswith("/z/"):
        return CE_URL + parsed.path

    return returned_url


def notify_relay(url: str) -> None:
    data = json.dumps({"url": url}).encode("utf-8")

    request = urllib.request.Request(
        "http://127.0.0.1:8123/update",
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=2,
        ):
            pass

    except Exception:
        fail("CE tab relay is not running. Start tools/ce-tab.py first.")


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: ce-open.py <source-file> <compile_commands.json>")

    source_file = pathlib.Path(sys.argv[1]).resolve()

    compile_commands = pathlib.Path(sys.argv[2]).resolve()

    if not source_file.exists():
        fail(f"source file not found: {source_file}")

    try:
        source = source_file.read_text()
    except Exception as exc:
        fail(f"could not read source: {exc}")

    commands = load_compile_commands(compile_commands)

    entry = find_compile_entry(
        source_file,
        commands,
    )

    if entry is None:
        print(
            "Compiler Explorer: no compile_commands entry found; using fallback flags.",
            file=sys.stderr,
        )

        options = "-O3 -std=c++23"

    else:
        flags = extract_flags(
            entry,
            source_file,
        )

        options = quote_flags(flags)

    print(f"Compiler Explorer file: {source_file}")

    print(f"Compiler Explorer flags: {options}")

    state = create_ce_state(
        source,
        options,
    )

    url = create_shortlink(state)

    print(f"Compiler Explorer URL: {url}")

    notify_relay(url)


if __name__ == "__main__":
    main()

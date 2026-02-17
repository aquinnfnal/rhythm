#!/usr/bin/env python3

import sys
import time
from datetime import datetime, timedelta
import re
import importlib.util
from pathlib import Path
from typing import Dict, List, Callable
import traceback


# ANSI helpers
CLEAR = "\033[2J\033[H"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

def parse_time_string(s: str) -> int:
    """
    Parse a time string of the form:
      XXhXXmXXs (any subset allowed)
    and return total seconds.
    """
    pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')
    m = pattern.match(s)
    if not m:
        raise ValueError(f"Invalid delay format: {s}")

    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def sleep_with_status(seconds: float, update_interval: float = 5, status_text=None):
    """
    Sleep for `seconds`, printing status messages showing:
      - current time
      - scheduled wake-up time

    Parameters
    ----------
    seconds : float
        Total number of seconds to sleep.
    update_interval : float
        How often (in seconds) to print status updates.
        Default is 60 seconds. Set to None to print only start/end.
    """
    start = datetime.now()
    end = start + timedelta(seconds=seconds)

    

    remaining = seconds
    while remaining > 0:
        if update_interval is None:
            time.sleep(remaining)
            break

        if remaining > 0:
            now = datetime.now()
            print(f"{CLEAR}{BLUE}")
            if status_text is not None:
                print(f"[sleep] {status_text}")
            print(f"[sleep] Started sleep at {start:%Y-%m-%d %H:%M:%S}")
            print(f"[sleep] Time now is      {now:%Y-%m-%d %H:%M:%S}")
            print(f"[sleep] Will wake at     {end:%Y-%m-%d %H:%M:%S}")
            print(f"[sleep] Total duration:  {seconds:.1f} seconds")
            

        chunk = min(update_interval, remaining)
        time.sleep(chunk)
        remaining -= chunk


    print(f"{GREEN}[sleep] Woke up at {datetime.now():%Y-%m-%d %H:%M:%S}{RESET}")



def load_functions_from_sources(source_files: List[Path]) -> Dict[str, Callable]:
    """
    Dynamically import each source file and collect all callable
    objects defined at module scope.
    """
    functions = {}

    for src in source_files:
        spec = importlib.util.spec_from_file_location(src.stem, src)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj):
                functions[name] = obj

    return functions


def parse_sources_file(path: Path) -> List[Path]:
    """
    Each line is a relative path to a Python file.
    """
    sources = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sources.append(path.parent / line)
    return sources


def parse_aliases_file(path: Path) -> Dict[str, Dict]:
    """
    Each line:
      alias function_name [arg1 arg2 ...]
    """
    aliases = {}

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            alias = parts[0]
            func_name = parts[1]
            args = parts[2:]

            aliases[alias] = {
                "func": func_name,
                "args": args,
            }

    return aliases

def log_error(exception_text):
    with open("rrun_error_log.txt",'a') as write_file:
        now = datetime.now()
        log_txt = f"[{now:%Y-%m-%d %H:%M:%S}] {exception_text} \n"
        write_file.write(log_txt)
        print(f"{RED}{log_txt}{RESET}")

def main():
    if len(sys.argv) < 2:
        print("Usage: script.py alias1+alias2+... [extra_args...]")
        sys.exit(1)

    cwd = Path.cwd()

    sources_file = cwd / "rhythm_sources.txt"
    aliases_file = cwd / "rhythm_aliases.txt"

    if not sources_file.exists():
        raise FileNotFoundError("rhythm_sources.txt not found")
    if not aliases_file.exists():
        raise FileNotFoundError("rhythm_aliases.txt not found")

    # Parse config files
    source_paths = parse_sources_file(sources_file)
    alias_map = parse_aliases_file(aliases_file)

    # Load all functions
    functions = load_functions_from_sources(source_paths)

    # Parse command line
    alias_chain_txt = sys.argv[1]
    alias_chain = alias_chain_txt.split("+")
    extra_args = sys.argv[2:]

    for alias in alias_chain:
        # Handle delay aliases: d1h30m, d45s, etc.
        if alias.startswith("d"):
            try:
                delay_seconds = parse_time_string(alias[1:])
                print(f"[rhythm] Delaying for {delay_seconds} seconds")
                sleep_with_status(delay_seconds,
                              status_text = f"Current test plan: {alias_chain_txt}")
                continue
            except ValueError:
                #If parse_time_string throws a ValueError, just treat as if it's a non-delay alias.
                pass

        if alias not in alias_map:
            raise KeyError(f"Unknown alias: {alias}")

        func_name = alias_map[alias]["func"]
        base_args = alias_map[alias]["args"]

        if func_name not in functions:
            raise KeyError(f"Function '{func_name}' not found in source files")
            

        func = functions[func_name]

        # Combine alias args + CLI args
        final_args = base_args + extra_args

        print(f"[rhythm] Running {func_name}({', '.join(final_args)})")
        try:
            func(*final_args)
        except Exception:
            stack_trace = traceback.format_exc()
            log_error(f"The following error occured while running {alias} as part of {alias_chain_txt}:\n {stack_trace}")


if __name__ == "__main__":
    main()

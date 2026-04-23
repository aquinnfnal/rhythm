#!/usr/bin/env python3

import sys
import time
from datetime import datetime, timedelta
import re
import importlib.util
from pathlib import Path
from typing import Dict, List, Callable
import traceback

import rhythm.rhythm_globals as rg

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


def interpret_str(s):
    """Parse a string into an int if possible, otw a float, otw a string"""
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s  # Not a number

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



def load_functions_from_source_files(source_files: List[Path]) -> Dict[str, Callable]:
    """
    Given a list of paths to individual Python files, import all functions from within those files.
    NOTE: This does not allow much flexibility in inter-module imports. Should really
    only be used for isolated functions.
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


def load_functions_from_source_modules(source_modules: List[str]) -> Dict[str, Callable]:
    """
    Given a list of qualified source module paths, import all functions from within those files.
    NOTE: Needs to be in some kind of well-defined module for this to work. 
    """
    functions = {}

    # 1) Ensure cwd (project root) is on sys.path
    parent_dir = Path.cwd().parents[0]
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))


    # 2) Import modules properly
    for modname in source_modules:
        module = importlib.import_module(modname)

        # 3) Collect functions defined in THIS module only
        for name, obj in vars(module).items():
            if callable(obj) and getattr(obj, "__module__", None) == module.__name__:
                functions[name] = obj

    return functions


def parse_sources_file(path: Path) -> List[Path]:
    """
    Each line is a relative path to a Python file.
    """
    source_files = []
    source_modules = []
    
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith(".py"):
                source_files.append(path.parent / line)
            else:
                source_modules.append(line)
    return (source_modules, source_files)


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
    source_modules, source_files = parse_sources_file(sources_file)
    alias_map = parse_aliases_file(aliases_file)

    # Load all functions
    functions = load_functions_from_source_files(source_files)
    functions.update(load_functions_from_source_modules(source_modules))

    # Parse command line
    rhythm_args = []
    for i in range(1,len(sys.argv)):
        if sys.argv[i].startswith("-"):
            rhythm_args.append(sys.argv[i])
        else:
            #The alias chain is the first arg that doesn't start with a dash.
            alias_chain_txt = sys.argv[i]
            extra_args = [ interpret_str(x) for x in sys.argv[(i+1):] ]
            break
    
    for rarg in rhythm_args:
        if rarg == "-s":
            rg.GLOBAL_SKIP_SIMULATION = True
        else:
            raise KeyError(f"Unknown rhythm argument {rarg}")

        
    alias_chain = alias_chain_txt.split("+")
        
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
        final_args_str = [str(x) for x in final_args]

        print(f"[rhythm] Running {func_name}({', '.join(final_args_str)})")
        try:
            func(*final_args)
        except Exception:
            stack_trace = traceback.format_exc()
            log_error(f"The following error occured while running {alias} as part of {alias_chain_txt}:\n {stack_trace}")


if __name__ == "__main__":
    main()

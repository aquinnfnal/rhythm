import threading
import traceback
import queue
import time
import json
import os
import sys
from typing import Any, Callable, Dict, List, Tuple, Optional
from rhythm_utils import *
import inspect

# ---------- Result object ----------


class Result:

    def __init__(self,function, args, argnames, kwargs={}, return_value=None,
                 exception=None,runtime_sec=None, status=None):
        self.function = function
        self.args = args
        self.argnames = argnames #Argument names, used for building a table.
        self.kwargs = kwargs
        self.return_value = return_value
        self.exception = exception
        self.runtime_sec = runtime_sec
        self.status = status

    def as_dict(self):
        return {"function": self.function,
                "args"    : self.args,
                "argnames": self.argnames,
                "kwargs"  : self.kwargs,
                "return_value": self.return_value,
                "exception" : self.exception,
                "runtime_sec": self.runtime_sec}


# ---------- Campaign class ----------

class Campaign:
    def __init__(
        self,
        jobs: List[Tuple[Callable, tuple, dict]],
        run_dir: str,
        MAX_JOBS: int = 4,
    ):
        self.jobs = jobs
        self.run_dir = run_dir
        self.MAX_JOBS = MAX_JOBS
        self.campaign_duration = None

        os.makedirs(run_dir, exist_ok=True)

        self.job_queue = queue.Queue()
        self.results_lock = threading.Lock()

        self.results: Dict[str, List[Result]] = {}
        self.job_status = {}  # job_id -> status string
        self.job_meta = {}    # job_id -> (func_name, args, kwargs)

        self.total_jobs = len(jobs)
        self.completed_jobs = 0
        self.stop_dashboard = threading.Event()

        for i, (func, args, kwargs) in enumerate(jobs):
            job_id = i
            self.job_queue.put(job_id)
            self.job_status[job_id] = "QUEUED"
            self.job_meta[job_id] = (func, args, kwargs)

    # ---------- Worker thread ----------

    def _worker(self):
        while True:
            try:
                job_id = self.job_queue.get_nowait()
            except queue.Empty:
                return

            func, args, kwargs = self.job_meta[job_id]
            func_name = func.__name__
            func_sig = inspect.signature(func)
            argnames = list(func_sig.parameters.keys())

            # If the user puts in None for kwargs, we can interpret
            # that as an empty mapping (avoiding errors).
            if kwargs is None:
                kwargs = {}

            self.job_status[job_id] = "RUNNING"
            start = time.time()

            result = Result(
                function=func_name,
                args=args,
                argnames=argnames,
                kwargs=kwargs)

            try:
                result.return_value = func(*args, **kwargs)
            except Exception as e:
                result.exception = repr(e)
                traceback.print_exc()
            finally:
                result.runtime_sec = time.time() - start
                result.status = "COMPLETED" if result.exception is None else "FAILED"

            with self.results_lock:
                self.results.setdefault(func_name, []).append(result)
                self.completed_jobs += 1
                self.job_status[job_id] = "COMPLETED" if result.exception is None else "FAILED"

            self.job_queue.task_done()

    # ---------- Dashboard ----------

    def _dashboard(self):
        while not self.stop_dashboard.is_set():
            self._render_dashboard()
            time.sleep(1)
        self._render_dashboard(final=True)

    def _render_dashboard(self, final=False):
        # ANSI helpers
        CLEAR = "\033[2J\033[H"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        RED = "\033[91m"
        RESET = "\033[0m"

        lines = [CLEAR]
        lines.append(f"Campaign started at: {self.campaign_start_datetime}")
        lines.append(f"          It is now: {str_datetimestamp()}")
        lines.append(f"Campaign status  {self.completed_jobs}/{self.total_jobs} completed\n")

        for job_id in range(self.total_jobs):
            status = self.job_status[job_id]
            func, args, _ = self.job_meta[job_id]

            if status == "QUEUED":
                color = BLUE
            elif status == "RUNNING":
                color = YELLOW
            elif status == "COMPLETED":
                color = GREEN
            else:
                color = RED

            lines.append(
                f"{color}[{job_id:03d}] {status:<10} "
                f"{func.__name__}{args}{RESET}"
            )

        if final:
            lines.append("\nCampaign finished.\n")

        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()

    # ---------- Run campaign ----------

    def run(self) -> Dict[str, List[Result]]:
        self.campaign_start = time.time()
        self.campaign_start_datetime = str_datetimestamp()

        dashboard_thread = threading.Thread(target=self._dashboard, daemon=True)
        dashboard_thread.start()

        

        workers = [
            threading.Thread(target=self._worker)
            for _ in range(self.MAX_JOBS)
        ]

        for w in workers:
            w.start()

        for w in workers:
            w.join()

        self.stop_dashboard.set()
        dashboard_thread.join()

        self._save_results()

        #If some runs failed, find out why.
        for result_list in self.results.values():
            for r in result_list:
                if r.status == "FAILED":
                    print(f"ERROR: {r.function} with args {r.args} failed due to {r.exception}")
        
        self.campaign_duration = format_hms(time.time() - self.campaign_start)
        print(f"Total campaign took: {self.campaign_duration}")
        return self.results

    # ---------- Persistence ----------

    def _save_results(self):
        serializable = {
            func: [r.as_dict() for r in results]
            for func, results in self.results.items()
        }

        out_path = os.path.join(self.run_dir, "results.json")
        with open(out_path, "w") as f:
            json.dump(serializable, f, indent=2)


    def _load_results(self, filename: str = "results.json") -> None:
        """
        Load results from disk and populate self.results.

        Inverse of _save_results(). Reconstructs Result objects from JSON.
        """

        path = os.path.join(self.run_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"No saved results found at {path}")

        with open(path, "r") as f:
            raw = json.load(f)

        results: Dict[str, List[Result]] = {}

        for func_name, result_list in raw.items():
            results[func_name] = []
            for rdict in result_list:
                # Only pass fields that Result actually defines
                result = Result(
                    function=rdict.get("function", func_name),
                    args=tuple(rdict.get("args", [])),
                    argnames=tuple(rdict.get("argnames",[])),
                    kwargs=dict(rdict.get("kwargs", {})),
                    return_value=rdict.get("return_value"),
                    exception=rdict.get("exception"),
                    runtime_sec=rdict.get("runtime_sec"),
                )
                results[func_name].append(result)

        self.results = results

        return self.results




    def create_scalar_table(self, fmt: str = "ascii") -> str:
        """
        Generate a formatted summary table of campaign results.

        Parameters
        ----------
        fmt : {"ascii", "csv", "markdown", "raw"}
            Output format. Default is "ascii".

        Assumes each Result.return_value is a dict:
            {str result_name: numeric_value}

        Returns
        -------
        str
            The formatted table.
        """

        fmt = fmt.lower()
        if fmt not in {"ascii", "csv", "markdown", "raw"}:
            raise ValueError(f"Unsupported format: {fmt}")

        # ---- Flatten results into rows ----
        rows = []
        all_result_keys = set()

        for func_name, result_list in self.results.items():
            for r in result_list:
                result_dict = r.return_value if isinstance(r.return_value, dict) else {}
                all_result_keys.update(result_dict.keys())

                rows.append({
                    "function": func_name,
                    "argnames": r.argnames,
                    "args": self._format_args(r.args, r.kwargs),
                    "results": result_dict,
                })

        if not rows:
            return "<no results>"

        if fmt == "raw":
            return rows

        # ---- Column logic ----
        show_function_col = len(self.results) > 1
        result_keys = sorted(all_result_keys)

        # ---- Sort rows ----
        if show_function_col:
            rows.sort(key=lambda r: (r["function"], r["args"]))
        else:
            rows.sort(key=lambda r: r["args"])

        # ---- Headers ----
        headers = []
        if show_function_col:
            headers.append("Function")
            
        #Note this strategy for printing the header relies on the fact that we are
        #only running a single function with a fixed # of args.
        for argname in rows[0]["argnames"]:
            if self._printable_argname(argname):
                headers.append(argname)
        #headers.append("Arguments")
        headers.extend(result_keys)

        # ---- Build table matrix ----
        table = [headers]

        for row in rows:
            line = []
            if show_function_col:
                line.append(row["function"])

            for arg in row["args"].split(','):
                line.append(arg)
            #line.append(row["args"].split(","))

            for key in result_keys:
                val = row["results"].get(key, "")
                if isinstance(val, float):
                    line.append(f"{val:.6g}")
                else:
                    line.append(str(val))

            table.append(line)

        # ---- Emit formats ----
        if fmt == "ascii":
            return self._emit_ascii_table(table)

        if fmt == "markdown":
            return self._emit_markdown_table(table)

        if fmt == "csv":
            return self._emit_csv(table)

    def _format_args(self, args, kwargs) -> str:
        parts = [repr(a) for a in args]
        for k, v in kwargs.items():
            if self._printable_argname(k):
                parts += [f"{k}={v!r}"]
        return ", ".join(parts)


    def _printable_argname(self,argname):
        """Returns true if this argument should be printed (most args)
           Returns false for meta arguments like "quiet" and "interactive" """
        if "quiet" in argname or "interactive" in argname:
            return False
        else:
            return True

    def _emit_ascii_table(self, table) -> str:
        print(table)
        col_widths = [
            max(len(str(row[i])) for row in table)
            for i in range(len(table[0]))
        ]

        def sep(char="-"):
            return "+" + "+".join(char * (w + 2) for w in col_widths) + "+"

        lines = [sep()]
        for i, row in enumerate(table):
            lines.append(
                "| " + " | ".join(
                    str(cell).ljust(col_widths[j])
                    for j, cell in enumerate(row)
                ) + " |"
            )
            if i == 0:
                lines.append(sep("="))
        lines.append(sep())

        return "\n".join(lines)


    def _emit_markdown_table(self, table) -> str:
        lines = []
        header = table[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")

        for row in table[1:]:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")

        return "\n".join(lines)


    def _emit_csv(self, table) -> str:
        def escape(cell: str) -> str:
            cell = str(cell)
            if "," in cell or '"' in cell:
                cell = '"' + cell.replace('"', '""') + '"'
            return cell

        lines = []
        for row in table:
            lines.append(",".join(escape(c) for c in row))

        return "\n".join(lines)

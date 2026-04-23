import threading
import traceback
import queue
import time
import json
import os
import sys
from typing import Any, Callable, Dict, List, Tuple, Optional
import math
from collections import defaultdict, Counter
from rhythm.rhythm_utils import *
import inspect

# ---------- Result object ----------


class Result:

    def __init__(self,function, args, argnames, kwargs={}, return_value=None,
                 exception=None,runtime_sec=None, status=None, timestamp=None):
        self.function = function
        self.args = args
        self.argnames = argnames #Argument names, used for building a table.
        self.kwargs = kwargs
        self.return_value = return_value
        self.exception = exception
        self.runtime_sec = runtime_sec
        self.status = status
        self.timestamp = timestamp

    def as_dict(self):
        return {"function": self.function,
                "args"    : self.args,
                "argnames": self.argnames,
                "kwargs"  : self.kwargs,
                "return_value": self.return_value,
                "exception" : self.exception,
                "runtime_sec": self.runtime_sec,
                "timestamp" : self.timestamp}



# ---------- Specification class ----------


class Specification:
    """
    Specification for a single Figure of Merit (FoM).

    Parameters
    ----------
    name : str
        Key name in Result.return_value.
    spec_min : Optional[float]
        Minimum acceptable value.
    spec_max : Optional[float]
        Maximum acceptable value.
    corners : Optional[List[str]]
        String representation of keywords that must be in the corner's arg string to match to that corner.
    note : Optional[str]
        Optional descriptive text.
    """

    def __init__(
        self,
        name: str,
        spec_min: Optional[float] = None,
        spec_max: Optional[float] = None,
        corners: Optional[str] = None,
        note: Optional[str] = None,
    ):
        self.name = name
        self.spec_min = spec_min
        self.spec_max = spec_max
        self.corners = corners 
        self.note = note

        if spec_min is None and spec_max is None:
            raise ValueError(
                f"Specification '{name}' must define at least one of spec_min or spec_max."
            )

    def __repr__(self):
        return (
            f"Specification(name={self.name!r}, "
            f"min={self.spec_min}, max={self.spec_max}, "
            f"corners={self.corners})"
        )

    def short_str(self):
        if self.spec_max is None:
            return f"{self.name} > {si_fmt(self.spec_min)}"
        elif self.spec_min is None:
            return f"{self.name} < {si_fmt(self.spec_max)}"
        else:
            return f"{si_fmt(self.spec_min)} < {self.name} < {si_fmt(self.spec_max)}"


    def check_spec(self, value):
        isPass = True
        if self.spec_min is not None and value < self.spec_min:
            isPass = False
        if self.spec_max is not None and value > self.spec_max:
            isPass = False
        return isPass
        
    def match_corner(self, corner_str):
        """Returns True if this spec applies to a corner with the given corner_str. 
           We expect that corners is a string containing a set of tokens joined by AND, OR, NOT, and parentheses"""

        if self.corners is None:
            return True
        
        tokens = self.corners.split()

        expr = []
        for tok in tokens:
            if tok == "AND":
                expr.append("and")
            elif tok == "OR":
                expr.append("or")
            elif tok == "NOT":
                expr.append("not")
            elif tok in {"(",")"}:
                expr.append(tok)
            else:
                #Assume this token is a keyword:
                expr.append(f'("{tok}" in corner_str)')

        expr_str = " ".join(expr)
        #print(f"<DBG> {expr_str}")
        result = eval(expr_str) #user inputs are trusted completely.
        return result
                
    
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

        self.key_args = None #List of indices of args that are important to list in the table.

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
            timestamp = str_datetimestamp()

            result = Result(
                function=func_name,
                args=args,
                argnames=argnames,
                timestamp=timestamp,
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

        queued_count = 0
        running_count = 0

        for job_id in range(self.total_jobs):
            status = self.job_status[job_id]
            func, args, _ = self.job_meta[job_id]

            if self.total_jobs < 40:

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
                    f"{func.__name__}({self.key_args_str(args)}){RESET}"
                )
            else:
                if status == "QUEUED":
                    queued_count += 1
                elif status == "RUNNING":
                    running_count += 1

        if self.total_jobs >= 40:
            lines.append(f"\n{BLUE}[{queued_count} QUEUED] {GREEN}[{running_count} RUNNING]")

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
        try:
            with open(out_path, "w") as f:
                json.dump(serializable, f, indent=2, default = lambda o: o.__dict__)
        except TypeError as e:
            print("ERROR: Rhythm could not save results in JSON format, likely because one of the arguments or return values of your function is not JSON serializable.")
            print(e)


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




    def create_scalar_table(self, fmt: str = "ascii", result_keys=None) -> str:
        """
        Generate a formatted summary table of campaign results.

        Parameters
        ----------
        fmt : {"ascii", "csv", "markdown", "raw"}
            Output format. Default is "ascii".

        Assumes each Result.return_value is a dict:
            {str result_name: numeric_value}

        result_keys: Optional list of result names to be included in the table.
                     If not supplied, ALL results will be included in the table.

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
                    "argnames": self.key_args_str(r.argnames),
                    "args": self.key_args_str(r.args), #Don't print kwargs in this table.
                    "results": result_dict,
                })

        if not rows:
            return "<no results>"

        if fmt == "raw":
            return rows

        # ---- Column logic ----
        show_function_col = len(self.results) > 1
        if result_keys is None:
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

        #Find the argnames to print in the table header.
        #Note:
        # - We print argnames only up to the length of args. There may be more argnames,
        #   but if an arg value wasn't passed to the argname it must be a default setting
        #   and thus unimportant to print.
        # - This strategy for printing the header relies on the fact that we are
        #   only running a single function with a fixed # of args.
        print(rows[0]["args"].split(','))
        print(rows[0]["argnames"].split(','))
        num_args = len(rows[0]["args"].split(','))
        for i in range(num_args):
            argname = rows[0]["argnames"].split(',')[i]
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
                if isinstance(val, float) and (fmt == "ascii" or fmt == "markdown"):
                    line.append(si_fmt(val))
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



    def compute_stats(self, specs=None):
        """
        Compute statistics for numeric results across all runs.

        Parameters
        ----------
        specs : dict or None
            Optional spec dictionary of the form:
            { "result_name": [min_val, max_val] }
            Either min_val or max_val may be None.

        Returns
        -------
        dict
            {
              function_name: {
                  result_name: {
                      "mean": float,
                      "std": float,
                      "min": float,
                      "max": float,
                      "spec_min": float or None,
                      "spec_max": float or None,
                      "spec_pass": bool or None
                  },
                  ...
              },
              ...
            }
        """
        specs = specs or {}
        stats = {}

        for func_name, result_list in self.results.items():
            values_by_key = defaultdict(list)

            for res in result_list:
                ret = res.return_value
                if not isinstance(ret, dict):
                    continue

                for key, value in ret.items():
                    if isinstance(value, (int, float)):
                        values_by_key[key].append(value)

            func_stats = {}

            for key, values in values_by_key.items():
                if not values:
                    continue

                mean = sum(values) / len(values)

                if len(values) > 1:
                    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                    std = math.sqrt(var)
                else:
                    std = 0.0

                vmin = min(values)
                vmax = max(values)

                spec_min, spec_max = specs.get(key, (None, None))

                if spec_min is None and spec_max is None:
                    spec_pass = None
                else:
                    spec_pass = True
                    if spec_min is not None and vmin < spec_min:
                        spec_pass = False
                    if spec_max is not None and vmax > spec_max:
                        spec_pass = False

                func_stats[key] = {
                    "mean": mean,
                    "std": std,
                    "min": vmin,
                    "max": vmax,
                    "spec_min": spec_min,
                    "spec_max": spec_max,
                    "spec_pass": spec_pass,
                }

            stats[func_name] = func_stats

        return stats


    def stats_table(self, specs=None, float_format="{:.6g}"):
        """
        Print statistics in table form, including min/max and spec compliance.

        Parameters
        ----------
        specs : dict or None
            Spec dictionary passed through to compute_stats().
        float_format : str
            Format string for floating-point values.
        """
        stats = self.compute_stats(specs=specs)

        return_str = ""

        for func_name, func_stats in stats.items():
            if not func_stats:
                continue

            return_str += f"\n=== Statistics for {func_name} ===\n"

            # Column widths
            name_width = max(len(name) for name in func_stats.keys())
            num_cols = ["Mean", "Std Dev", "Min", "Max"]
            COL_WIDTH = 10
            #widths = {col: len(col)+2 for col in num_cols}
            spec_width = len("Spec")
            pass_width = len("Pass")

            #for vals in func_stats.values():
                #for col, key in zip(num_cols, ["mean", "std", "min", "max"]):
                #    widths[col] = max(
                #        widths[col],
                #        len(float_format.format(vals[key]))
                #    )

             #   if vals["spec_min"] is not None or vals["spec_max"] is not None:
             #       spec_str = f"[{vals['spec_min']},{vals['spec_max']}]"
             #       spec_width = max(spec_width, len(spec_str))
             #       pass_width = max(pass_width, len("PASS"))

            # Header
            header = (
                f"{'Result':<{COL_WIDTH}}"
                f"{'Mean':>{COL_WIDTH}}"
                f"{'StdDev':>{COL_WIDTH}}"
                f"{'Min':>{COL_WIDTH}}"
                f"{'Max':>{COL_WIDTH}}"
            )

            if specs:
                header += (
                    f"  {'Spec':^{COL_WIDTH}}  "
                    f"{'Pass':^{COL_WIDTH}}"
                )

            return_str += header +"\n"
            return_str += "-" * len(header) + "\n"

            # Rows
            for name, vals in func_stats.items():
                row = ""
                row += f"{name:<{COL_WIDTH}}"
                for valname in ["mean", "std", "min", "max"]:
                    row += f"{si_fmt(vals[valname]):>{COL_WIDTH}}"
                

                if specs:
                    if vals["spec_min"] is None and vals["spec_max"] is None:
                        spec_str = ""
                        pass_str = ""
                    else:
                        spec_str = f"[{vals['spec_min']},{vals['spec_max']}]"
                        pass_str = "PASS" if vals["spec_pass"] else "FAIL"

                    row += (
                        f"  {spec_str:^{spec_width}}  "
                        f"{pass_str:^{pass_width}}"
                    )

                return_str += row + "\n"

        return return_str



    def check_specs(self, specs) -> Dict[str, Dict]:
        """
        Evaluate a list of Specification objects against Campaign.results.

        Matching rule:
            A Result matches a corner if and only if the corner string
            appears in Campaign._format_args(args, kwargs) for that Result.

        Returns a readable report.
        """

        # Gracefully accept lists or single specs
        if type(specs) == Specification:
            specs = [specs]
        
        spec_results = ""

        # Flatten results from all function runs into a single list.
        all_results = []
        for _, res_list in self.results.items():
            all_results.extend(res_list)
            
        for spec in specs:
            spec_name = spec.name

            #For each corner, we will assemble a corner_info dict containing:
            #  - corner_name: The name of the corner.
            #  - result: PASS, FAIL, N/A, etc.
            #  - value: Value of the FoM in the corner
            #  - min_margin: positive margin is it is above the min, negative margin is below the min
            #  - max_margin: positive margin is below the max, negative margin is above the max.
            corner_reports = []


            # For each result in the list...
            for r in all_results:
                corner_str = self._format_args(r.args,r.kwargs)
                spec_applies_this_corner = True

                # 1) Check to make sure that this spec applies to this corner.
                if not spec.match_corner(corner_str):
                    spec_applies_this_corner = False

                corner_info = {"corner_name": corner_str,
                               "result"     : None,
                               "value"      : None,
                               "min_margin" : None,
                               "max_margin" : None}
                        
                if not spec_applies_this_corner:
                    corner_info["result"] = "N/A"

                return_dict = r.return_value

                # 2) Check to make sure we got a valid return_dict from this corner
                if not isinstance(return_dict,dict) or spec_name not in return_dict:
                    corner_info["result"] = "Missing Data!"

                # 3) Try to get the value from this corner. 
                try:
                    val = float(return_dict[spec_name])
                    corner_info["value"] = val
                except ValueError:
                    corner_info["result"] = "Malformed Data!"

                # 3.5) If we already have a result at this point, it must be an invalid or N/A corner,
                #      so we pre-emptively return and append it to the list.
                if corner_info["result"] is not None:
                    corner_reports.append(corner_info)
                    continue

                # 4) Evaluate whether this corner value is considered a pass or not.
                corner_pass = True
                if spec.spec_min is not None:
                    corner_info["min_margin"] = val - spec.spec_min
                    if corner_info["min_margin"] < 0:
                        corner_pass = False

                if spec.spec_max is not None:
                    corner_info["max_margin"] = spec.spec_max - val
                    if corner_info["max_margin"] < 0:
                        corner_pass = False


                if corner_pass:
                    corner_info["result"] = "PASS"
                else:
                    corner_info["result"] = "FAIL"

                corner_reports.append(corner_info)

            spec_results += self._generate_spec_summary(spec, corner_reports) + "\n"

        return spec_results



    def _generate_spec_summary(self, spec,  corner_reports):
        """Generate a summary of whether a specification was met across corners.
           spec = Specification object
           corner_reports = info on whether each corner was passed, generated by self.check_specs()
        """
        
        summary = "\nSpecification: " + spec.short_str()

        if spec.corners is not None:
            summary += f" for corners matching {spec.corners}\n"
        else:
            summary += "\n"

        # count frequencies of each result.
        counts = Counter(d["result"] for d in corner_reports)

        # build summary string
        summary += "Results: " + " ".join(f"{v}x {k}" for k, v in counts.items()) +"\n"

        if all((d["result"] == "N/A") for d in corner_reports):
            summary += "Overall Result: N/A\n"
            #Nothing else to compute
            return summary
        if all((d["result"] == "PASS" or d["result"] == "N/A") for d in corner_reports):
            summary += "Overall Result: PASS\n"
        else:
            summary += "Overall Result: FAIL\n"

        # After evaluating all the results, we go back through corner_reports to find the corner
        # with the worst margin.
        # (Obviously if all results are none, it's impossible to generate a worst corner)
        if not any([c["value"] is not None for c in corner_reports]):
            return summary
        
        worst_margin = None
        worst_corner_idx = None

        #print(corner_reports)
        
        for i in range(len(corner_reports)):
            min_margin = corner_reports[i]["min_margin"]
            max_margin = corner_reports[i]["max_margin"]
            if min_margin is not None and (worst_margin is None or min_margin < worst_margin):
                worst_margin = min_margin
                worst_corner_idx = i
            if max_margin is not None and (worst_margin is None or max_margin < worst_margin):
                worst_margin = max_margin
                worst_corner_idx = i
        worst_corner_val = corner_reports[worst_corner_idx]["value"]
        worst_corner_name = corner_reports[worst_corner_idx]["corner_name"]

        summary += f"(Worst Corner was {worst_corner_name} with {spec.name}={si_fmt(worst_corner_val)})"

        return summary


    def key_args_str(self,args):
        if self.key_args is None:
            return self._format_args(args,{})
        else:
            key_args_list = [str(args[i]) for i in self.key_args]
            return ", ".join(key_args_list)


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
        #print(table)
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

        return "\n".join(lines) + "\n"


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

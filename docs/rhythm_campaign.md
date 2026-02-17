# Rhythm Campaigns

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

Campaigns run multiple jobs in parallel threads with a live dashboard. 

Rhythm Campaigns take three arguments:

- jobs: A list of jobs, where each job is a three-element tuple containing:
  - <Callable> the Python function that will run the job.
  - <tuple> a tuple containing \*args for the job.
  - <dict>  a dictionary of \*\*kwargs for the job.
- run_dir: String run directory for the Campaign, where top-level results will be saved.
- MAX_JOBS: Maximum number of jobs that are allowed to run simultaneously.

## Run a Campaign

**run() -> Dict[str, List[Result]]**
Spawns worker threads up to MAX_JOBS, periodically prints ANSI dashboard, and saves `results.json`. Logs failures with exceptions. 
At the end of the Campaign, Campaign.results will contain a dictionary where each function name is mapped to a list of Result() objects representing the results of each time that simulation function was run.

**_load_results(filename="results.json") -> same structure as run()**
Re-creates Result objects from JSON. 

## Post Processing

The most common practice is for simulation functions to return a dictionary of the different results that they generate, and Campaigns have special functions for printing / postprocessing these results, assuming that they come in dictionary form. These functions include:

**create_scalar_table(fmt="ascii", result_keys=None) -> str**
Formats a summary table (ASCII/CSV/Markdown/raw) of numeric/dict returns. Supports showing function + arguments + selected result keys. 

**compute_stats(specs=None)**
Aggregates mean, std, min/max for numeric values across runs. Accepts optional specs dict { result_name: [min, max] }. 

**stats_table(specs=None, float_format="{:.6g}")**
Emits a human-readable table of stats and spec PASS/FAIL. 

## Result Class

Per-job results are stored in a Result class. Holds per-job metadata: function name, args/kwargs, return value (often dict), exception string if any, runtime seconds, and status (COMPLETED/FAILED). 
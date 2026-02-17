# Quick Start

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

Some quick examples to get you started running Rhythm recipes.

## Prerequisites

- **Cadence OCEAN** must be installed and on `PATH`. Rhythm checks for `ocean` before running. 
- A valid **`cds.lib`** for your project. Pass it to `Recipe.set_cdslib(...)`.
- Make sure you have Python 3 and the Rhythm modules available on your path. 

## Simple Example Recipe

```python
from rhythm_recipe import Recipe

tb = Recipe()
tb.set_rundir("demo_run")                    # creates ./demo_run
tb.set_cdslib("/path/to/cds.lib")           # required

# Add stages (see docs/stages.md)
tb.load_stage(("variables", {"VDD": 1.2}))  # desVar("VDD" 1.2)
tb.load_stage(("stimulus", "input.scs"))    # copies into run dir + sets stimulusFile(...)
tb.load_stage(("ocnSnip", "analysis('tran ?stop \"100u\")")))
tb.load_stage(("saveResults", [("Vout", "VT", "/dut/out")]))
tb.load_stage_printWaves([("Vout", "VT", "/dut/out")])

tb.run(quiet=False)

# Use the parsed waveforms
wf = tb.waves.get("Vout")
print("Vout @ 50us =", wf.value_at(50e-6))
```

**Tip:** By default Rhythm writes a compiled OCEAN script to ./<rundir>/compiled_recipe.ocn

## Options for Post-analysis

### Scalars

If you printed scalars using `load_stage_printScalars([...])`, they will be saved to a text file, and you can also read them back into Python for further analysis:

```python
scalars = tb.get_scalar_results("scalar_results.txt")
print(scalars.Vout)   # access via attribute (SimpleNamespace)
```

### ViVA

You can invoke ViVA at the end of your test:

```python
tb.launch_viva()
```



## Simple Example Campaign`

```python
from rhythm_campaign import Campaign

def run_one_corner(vdd, temp, quiet=True):
    tb = Recipe()
    tb.set_rundir(f"batch/corner_vdd{vdd}_t{temp}")
    tb.set_cdslib("/path/to/cds.lib")
    tb.load_stage(("variables", {"VDD": vdd, "TEMP": temp}))
    tb.load_stage(("ocnSnip", "analysis('tran ?stop \"100u\")")))
    tb.load_stage(("saveResults", [("Vout", "VT", "/dut/out")]))
    tb.load_stage_printWaves([("Vout", "VT", "/dut/out")])
    tb.run(quiet=quiet)
    # Return a dict of results (Campaign expects serializable return values)
    return {"Vout@50us": tb.waves.get("Vout").value_at(50e-6)}

jobs = [
    (run_one_corner, (1.1, 25), {"quiet": True}),
    (run_one_corner, (1.2, 25), {"quiet": True}),
    (run_one_corner, (1.3, 25), {"quiet": True}),
]

camp = Campaign(jobs=jobs, run_dir="batch", MAX_JOBS=4)
results = camp.run()

print(camp.create_scalar_table("ascii", result_keys=["Vout@50us"]))
```

**Notes:**
- Each job is specified as a tuple: `(callable, args_tuple, kwargs_dict)`
- Each Campaign accepts a list of jobs and runs them with a worker pool, never exceeding `MAX_JOBS` threads.
- **Tip:** A typical job consumes 4 licenses (2x base, 2x multi-thread), so a Campaign will use `4*MAX_JOBS` licenses at its peak.
- Results (the return values from each job) are persisted to run_dir/results.json
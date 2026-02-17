# Rhythm Recipes

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

Represents a single simulation “recipe”: a sequence of stages that compile into an OCEAN script and get executed.

## Setup

**set_rundir(rundir, local_results=True)**
Creates ./<rundir>, stores full path, and prepares for compilation. 

**set_cdslib(cdslib_path)**
Required to run; passed to ocean -cdslib. 

## Stage Loading

See [stages](</docs/stages.md>).


## Results Specification Format

Rhythm recognizes results that are specified as a 3-tuple or 4-tuple with the following elements:

1. Name
2. Type ("VT", "IDC", etc.)
3. Path (i.e. "/dut/Vout")
4. (Optional) sample time *or* custom save statement. If a 4th entry is specified as a number, it is treated as a time to sample the result. Otherwise, this entry can be used to inject a custom save statement for a more complex result. 


**Examples:**

```python
simple_result = ("Vout_preamp", "VDC", "/Vout_preamp")

simple_sampled_result = ("Vout_preamp", "VT", "/Vout_preamp", 899e-9)

result_with_custom_expression = ("cds_2_int",None,None, "value(getData(\"cds.Nsamp2:gds\" ?result \"tranOpTimed\" ) 200n )
```

You can reuse the same results list for `saveResults`, `printScalars`, `plot`, or `printWaves`. (Printing or plotting requires that the signal has already been saved.)

## Compile & Run

**run(interactive=False, quiet=False)**
Validates preconditions (rundir, cdslib, ocean on PATH), runs OCEAN, tails the log in a separate xterm unless quiet=True, checks for basic Spectre errors (e.g., DC convergence SPECTRE-16080), and executes post-run tasks such as waveform parsing. 

## Results & Analysis Helpers

**get_scalar_results(filename="scalar_results.txt") -> SimpleNamespace**
Convenience wrapper around scalar_results_to_dict(...). 

**scalar_results_to_dict(filename="scalar_results.txt") -> dict**
Parses name/value pairs from the scalar file. 

**launch_viva()**
Tries to open ViVA with -datadir <resultsDir> if discoverable.

## Tips and Best Practices

- **Stage Libraries** - It is highly recommended to create a shared stage library that can be referenced by each test in your testbench. 
- **Order matters:** Typically set variables first, then stimulus, then analyses (via ocnSnip), then saves/prints. 1
- **Quiet mode:** tb.run(quiet=True) suppresses the separate xterm tail -f window; otherwise Rhythm spawns a live log viewer. 
- **Compiled recipes:** By default Rhythm writes a compiled OCEAN script to `./<rundir>/compiled_recipe.ocn`. If Rhythm is not doing what you expect, first check this recipe.
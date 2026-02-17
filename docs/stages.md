# Rhythm Stage Commands

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

These commands are used to create test stages in Rhythm. There are two ways to use a stage command:

1) Directly call the function.

```
tb.load_stage_ocnScript("my_script.ocn")
```

2) Call *load_stage* with a tuple of the command name and its arguments.

```
my_stage = ("ocnScript", "my_script.ocn")
tb.load_stage(my_stage)
```


## ocnScript

Loads an OCEAN script from file.

**Method:** ```tb.load_stage_ocnScript()```

**Arguments:** (str) path to .ocn file.

## ocnSnip

Loads a snippet of OCEAN code.

**Method:** ```tb.load_stage_ocnSnip()```

**Arguments:** (str) snippet of OCEAN code.

## variables

Given a dictionary which maps variable names (str) to values (num), this function will generate a set of desVar() commands.

**Method:** ```tb.load_stage_variables()```

**Arguments:** (dict) variable names (str) -> variable values (num)

## stimulus

Use a .scs file as a stimulus for the testbench. The stimulus file will be copied into the run directory. 

**Method:** ```tb.load_stage_stimulus()```

**Arguments:** (str) path to .scs file.

## saveResults

Save a set of currents and voltages.

**Method:** ```tb.load_stage_saveResults()```

**Arguments:** (list) results_list, a list of tuples with the entries (1) Name, (2) Type (IDC, IT, etc), and (3) hierarchical path to the node under test.

Example of results_list:
```
results_list = [("VDDA_tot", "IDC", "/Vsrc_VDDA/V0/PLUS"),
                ("VDDD_tot", "IDC", "/Vsrc_VDDD/V0/PLUS"),
                ("VDDA_preamp", "IDC", "/pa/VDDA"),
                ("VDDA_mirror", "IDC", "/mirror/VDDA")]

```
**Note:** This command alone will not output or print anything, only save the results in the results database. If the results are scalars, the same list can be passed to ```tb.load_printScalars()```

## printScalars

Print a set of scalar results.

**Method:** ```tb.load_stage_printScalars()```

**Arguments:** (list) results_list, a list of tuples with the entries (1) Name, (2) Type (IDC, IT, etc), and (3) hierarchical path to the node under test. See **saveResults** for an example.

**Note:** Results must have been saved before they can be printed. Include ```tb.load_saveResults()``` if needed.

## printWaves

Writes multiple waveforms to waves.txt in “engineering” notation and schedules a post-run task to parse into a `WaveformSet`.

**Method:** ```tb.load_stage_printWaves()```

**Arguments:** Results list

## plot

Plot functions.

**Method:** ```tb.load_stage_plot()```

**Arguments:** Results list

## spectreSnip

Inject a Spectre snippet directly into the `.scs` file (using `stimulusFile(...)` hack). 

**Method:** ```tb.load_stage_spectreSnip()```

**Arguments:** (string) snippet of Spectre code
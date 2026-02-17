# Rhythm Runner

Make your life simple, and run your tests from the command line with aliases!

## Setup

Create **rhythm_sources.txt**, a file which lists all the files that contain your rhythm recipes:

Example:
```
test_scripts/sim_dc_bias.py
test_scripts/sim_shutdown_power.py
```

Create **rhythm_aliases.txt**, a file which lists aliases, plus the function name (from one of your source files) that should be invoked for each alias.

```
sdpow	run_sim_shutdown_power
xsdpow 	campaign_sim_shutdown_power
dc	run_sim_dc_bias
xdc	campaign_sim_dc_bias
```

## Run Scripts

Now you can invoke your DC testbench with:

```python3 /path/to/rhythm_run.py dc```

You can also add the following line to your `~/.bashrc`:

```alias rrun="python3 /path/to/rhythm_run.py"```

So now all you have to do is:

```rrun dc```

**Tips:**
- Rhythm aliases can be followed by a series of string arguments followed by spaces. 
- You can also cause Rhythm to *wait* for a set number of hours/minutes/seconds before executing a script with the special alias `dXXhXXmXXs`.
- You can also chain multiple aliases/tests together with a "+" sign.
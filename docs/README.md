# Rhythm

**Rhythm** is a small Python framework that automates Cadence Spectre simulations from the command line.
Instead of creating an ADE testbench, you'll write a **Rhythm Recipe**, a short, readable Python script that contains each step needed to test your circuit from setting up libraries and stimulus waveforms to setting up analyses and reading the results (in Rhythm, these steps are called **stages**). Need to run more than one simulation? Use a **Rhythm Campaign** to easily sweep across corners and test conditions with a live dashboard and multithreading support. 

## Why Rhythm?

- **Perfect Testbench Introspection** – No more hunting through menus to find which setting is different: your testbench is just a simple text script. If you want to compare two testbenches to find out why they give different results, it’s trivial. 
- **Results Reproducibility** – Easily save your historical testbenches so you can re-run them in the future. 
- **Ease of Sharing Knowledge (Including w/ AI)** – Need to know how to do something in your testbench? You don’t need screenshots and step-by-step instructions (which might become obsolete next time Cadence updates anyhow). Just share a simple command. You can also directly ask Gemini for OCEAN commands. (Other AI products don’t seem to be as good.)
- **Automatic Results Exporting and Processing** – With OCEAN print statements and Python, you have an automatic way to spit out the results you care about at the end of a sim run and process / graph them with all the power available to Python. No more repetitive saving curves from ViVA and struggling with the formatting.
- **Duplicate Testbenches / Workflows with Ease** – If you want to set up a new testbench, it’s easy to copy from the old one and have it work the same way. No more going through menus.
- **Scheduling Delayed or Sequential Runs** – Run simulations at night, or schedule one simulation after the other. 


## Rhythm Documentation

- [Quick Start](</docs/quick_start.md>)
- [Rhythm Recipes](</docs/rhythm_recipe.md>)
- [Rhythm Stages](</docs/stages.md>)
- [Rhythm Campaign](</docs/rhythm_campaign.md>)
- [Rhythm Runner](</docs/rhythm_run.md>)
- [To-Do List](</docs/TODO.md>)

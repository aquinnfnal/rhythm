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


## Prerequisites

- **Cadence OCEAN** must be installed and on `PATH`. Rhythm checks for `ocean` before running. 
- A valid **`cds.lib`** for your project. Later, you will pass it to `Recipe.set_cdslib(...)`.
- Python 3 (recommended version 3.12) 

## Installing Rhythm 

**Normal Users:**

```
pip install git+https://github.com/SpacelyProject/py-libs-common
```

**Developers:**
First ```git clone``` rhythm to your local system, and then;

```
pip install -e /path/to/rhythm
```

## Getting Started 

To use Rhythm, you will need to write a **rhythm testbench**, a collection of Python files and OCEAN snippets that describes how to test your specific circuit. Your testbench will consist of **recipes** which tell Rhythm how to run one specific simulation, and **Campaigns** which combine a set of related recipes that can be run in parallel, for example to test a circuit over multiple corners. Once you write your testbench, you will run it and view the results.

There are different ways to organize and run your testbench depending on the features you desire. Here are some recommended patterns. 

- [The Simplest Rhythm Testbench](</docs/testbench/simple.md>): Everything in one Python file!
- [Running Testbenches with the Runner](</docs/testbench/rrun.md>): Use simple aliases on the command line to easily run tests. 
- [Organize Your Testbench as a Module](</docs/testbench/module.md>): For larger testbenches that are split across multiple files, this makes relative imports easy.
- [Dispatchers and Environments](</docs/testbench/dispatcher.md>): A way to make tests more flexible, i.e. for parametric sweeps.



## Learn More

The following documents contain additional information on sub-modules of Rhythm:

- [Rhythm Recipes](</docs/rhythm_recipe.md>)
- [Rhythm Stages](</docs/stages.md>)
- [Rhythm Campaign](</docs/rhythm_campaign.md>)
- [To-Do List](</docs/TODO.md>)

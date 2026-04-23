# Complex Testbenches 

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

If your testbench has a lot of files that import from each other, it is best to structure it as a module -- this basically just means putting an **__init__.py** file in every folder that contains at least one source code file. 

Now you should be able to import files based on their relative location within your testbench folder, i.e.

```
from myTestbench.src.sim_dc_bias import sim_dc_bias
```

You can also put these path names inside your **rhythm_sources.txt** and rrun will be able to import them. 
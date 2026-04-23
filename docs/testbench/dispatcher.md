# Dispatcher Functions

[(Click to return to Rhythm Docs Overview)](</docs/README.md>)

The basic idea:
1. Each of your test functions (ac, dc, tran, etcetera) should be written to accept a single argument, **env**, which is an Environment() class (this could just be a simple namespace). All the variables and config information the test needs to run will be obtained from fields of **env**.
2. Create a dispatcher function which sets up an **env** object according to your requirements and then passes it to the appropriate sim function to run it. 
3. Pass arguments to the dispatcher function which describe the test to be run. 


**Why this works:** Let's say you want to sweep an extra variable, or you want to sweep variables in a different way (monte carlo vs corner sims vs parametric analysis). Instead of needing to go back and modify all the arguments of all of your sim functions, you can just modify how the dispatcher works (or make a new dispatcher).
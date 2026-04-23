#
#  Rhythm Recipe
#
#
# This file defines the Rhythm Recipe class, which represents a specific test
# we want to run. It provides specific convenience methods to set up a recipe,
# import OCEAN files, and run. 
import os
import csv
import sys
import re
import subprocess
import datetime
import shutil
from types import SimpleNamespace
from rhythm.rhythm_logger import RhythmLogger
from rhythm.rhythm_utils import *
from rhythm.rhythm_waveforms import Waveform, WaveformSet
import rhythm.rhythm_globals as rg

# Define hooks
#RHYTHM_VARIABLES_HOOK = "$RHYTHM_VARIABLES"
#RHYTHM_SAVE_HOOK = "$RHYTHM_SAVE"
#RHYTHM_POST_HOOK = "$RHYTHM_POST"
#RHYTHM_STIMULUS_HOOK = "$RHYTHM_STIMULUS"


class Recipe():


    def __init__(self):
        self.rundir = None         #Run directory (within CWD)
        self.full_rundir = None    #Fully-qualified path to run directory
        self.log = RhythmLogger() 
        self.ocn_script = ""
        self.cdslib = None         #cds.lib file
        self.setup_scripts = []    #Scripts that should be sourced before running simulations (i.e. setup.csh)
        self.post_run_tasks = []
        self.waves = None
        self.spectreSnip_count = 0 #Number of Spectre snippets injected in this recipe. Used for file indexing.

        #Portions of the OCEAN script that rhythm can generate.
        #self.rhythm_variables_script = ""
        #self.rhythm_stimulus_script = ""
        #self.rhythm_save_script = ""
        #self.rhythm_post_script = ""

    ###################################
    # Rhythm Simulation Setup Methods #
    ###################################

    def set_rundir(self,rundir, local_results=True):
        """Sets the directory in which the Recipe will run.
           If this directory does not already exist, it is created."""
        self.rundir = rundir
        self.full_rundir = os.path.join(os.getcwd(),self.rundir)
        os.makedirs(self.full_rundir, exist_ok=True)

        if local_results:
            pass #self.ocn_script = f"resultsDir( \"{self.rundir}\" )" + self.ocn_script
        

    def set_cdslib(self,cdslib):
        """Specifies the cds.lib file to use for this run."""
        self.cdslib = cdslib

    def add_setup_script(self, new_script):
        self.setup_scripts.append(new_script)

    
    ##########################
    # Stage Loading Methods  #
    ##########################

    def clear(self):
        """Clear all loaded stages."""
        self.post_run_tasks=[]
        self.ocn_script = ""
        self.waves = None

    def load_stage(self, stage_tuple):
        if stage_tuple[0] == "ocnScript":
            self.load_stage_ocnScript(stage_tuple[1])
        elif stage_tuple[0] == "ocnSnip":
            self.load_stage_ocnSnip(stage_tuple[1])
        elif stage_tuple[0] == "variables":
            self.load_stage_variables(stage_tuple[1])
        elif stage_tuple[0] == "stimulus":
            self.load_stage_stimulus(stage_tuple[1])
        elif stage_tuple[0] == "saveResults":
            self.load_stage_saveResults(stage_tuple[1])
        elif stage_tuple[0] == "printScalars":
            self.load_stage_printScalars(stage_tuple[1])
        elif stage_tuple[0] == "printCSV":
            self.load_stage_printCSV(stage_tuple[1])
        else:
            self.log.error(f"Unable to load stage. Don't recognize stage type {stage_tuple[0]}")
            

    def load_stage_ocnScript(self, ocn_file):
        with open(ocn_file, 'r') as read_file:
            ocn_file_text = read_file.read()
        self.ocn_script += "\n"+ocn_file_text+"\n"

    def load_stage_ocnSnip(self, ocn_snip):
        self.ocn_script += "\n"+ocn_snip+"\n"


    def load_stage_variables(self, variable_dict):
        """Given a dictionary which maps variable names (str) to values (num), 
           this function will load them into your OCEAN script, replacing the
           $RHYTHM_VARIABLES hook."""

        self.log.info(f"Loading variables...")
            
        variables_txt = "\n; ---------- Design Variables ---------\n"

        for var_name in variable_dict.keys():
            var_val = variable_dict[var_name]
            variables_txt += f"desVar(  \"{var_name}\" {var_val}  )\n"
            
            
        self.ocn_script += variables_txt


    def load_stage_stimulus(self, stimulus_file):
        """Given a stimulus file **in the same dir as the testbench** 
           copies it into the results folder and sets up the script to use it.
        """
        stimulus_file_name = os.path.basename(stimulus_file)

        #Set up the command to include the stimulus file.
        rhythm_stimulus_script = f"\nstimulusFile( \"{stimulus_file_name}\" )\n"

        #Copy stimulus file into the results directory (if it's not already there).
        try:
            shutil.copyfile(stimulus_file, os.path.join(self.full_rundir,stimulus_file_name))
        except shutil.SameFileError:
            pass

        self.ocn_script += rhythm_stimulus_script


    def load_stage_spectreSnip(self, spectre_code):
        """Given a snippet of Spectre code, use a hack to inject it into the final spectre netlist."""
        
        filename = os.path.join(self.full_rundir,f"spectreSnip_{self.spectreSnip_count}.scs")
        self.spectreSnip_count += 1

        with open(filename,"w") as write_file:
            write_file.write(spectre_code)

        #Hack: Put the spectre code in as a "stimulus file"
        self.ocn_script += f"\nstimulusFile( \"{filename}\" )\n"
        
    

    def load_stage_saveResults(self, results_list):
        """results_list should have the form of tuples, where the entries are:
           1. Name
           2. type (IDC, IT, etc) and
           3. hierarchical path of the node under test.
           4. (OPTIONAL) The value of the independent variable at which to capture this result, if any.
           second entry is the hierarchical path of that result."""
        
        #Create save statements and variable grabbing statements.
        save_script = ""
        for r in results_list:
            name = r[0]
            var_type = r[1]
            path = r[2]
            if var_type.startswith("I"):
                save_type = "'i"
            else:
                save_type = "'v"
            
            
            save_script += f"save( {save_type} \"{path}\" )\n"

        self.ocn_script += "\n"+save_script

    def load_stage_printScalars(self, results_list, filename="scalar_results.txt"):
        """Prints scalar results to a txt file. Syntax is the same as load_saveResults()"""
                
        #Create statements to write to file.
        self.ocn_script += f"\nwrite_file = outfile( \"{filename}\" \"w\" )\n"

        for r in results_list:
            name = r[0]
            self.ocn_script += self._fmt_result_statement(r)
            self.ocn_script += f"errset( fprintf( write_file \"{name} = %g\\n\" {name} ) t )\n"
            
        self.ocn_script += "close( write_file )\n"


    def load_stage_plot(self, results_list):
        """Sets up results to be plotted."""
        for r in results_list:
            name = r[0]
            self.ocn_script += self._fmt_result_statement(r)
            self.ocn_script += f"plot( {name} ?expr '( \"{name}\" ) )\n"
    
    def load_stage_printWaves(self,results_list):
        """Instruct rhythm to print output waves to a text file."""
        
        #Group a list of all the names of results separated by spaces
        #so they can all be printed to the same TXT.
        name_list = []

        for r in results_list:
            name = r[0]
            self.ocn_script += self._fmt_result_statement(r)
            name_list.append(name)
            
        name_list_str = " ".join(name_list)
        self.ocn_script += f"ocnPrint( ?output \"waves.txt\" "
        self.ocn_script += f"?numberNotation `engineering {name_list_str} )\n"
        
        self.waves = WaveformSet(os.path.join(self.full_rundir,"waves.txt"),name_list)
        self.post_run_tasks.append(("create_wave_set",None))


    def _fmt_result_statement(self, r):
        """Given a tuple describing the result, this function will return a string
           which will save the result to a variable."""
        name = r[0]
        var_type = r[1]
        path = r[2]

        if len(r) < 4:
            return f"{name} = {var_type}(\"{path}\")\n"

        #Argument 4 can be an expression, or if it's a single number it will be treated as value_at.
        if type(r[3]) == str:
            expression = r[3]
            return f"{name} = {expression}\n"
        else:
            value_at = r[3]
            return f"{name} = value( {var_type}(\"{path}\") {value_at})\n"
        
            

    ###########################
    # Compile and Run Methods #
    ###########################

    def compile_recipe(self, interactive=False):
        """Compile the Recipe into an OCEAN script and write it to the 
           current rundir."""
        if self.rundir is None:
            self.log.error("Need to specify a rundir before Recipe.compile_ocean()")
            return

        time_string = str_datetimestamp()
        # Replace hooks in OCEAN script
        # It doesn't matter if not all of these hooks / scripts that have been defined.
        #self.ocn_script = self.ocn_script.replace(RHYTHM_VARIABLES_HOOK, self.rhythm_variables_script)
        #self.ocn_script = self.ocn_script.replace(RHYTHM_SAVE_HOOK, self.rhythm_save_script)
        #self.ocn_script = self.ocn_script.replace(RHYTHM_POST_HOOK, self.rhythm_post_script)
        #self.ocn_script = self.ocn_script.replace(RHYTHM_STIMULUS_HOOK, self.rhythm_stimulus_script)


        with open(os.path.join(self.full_rundir, "compiled_recipe.ocn"),'w') as write_file:
            
            write_file.write(f"; OCEAN Script generated by RHYTHM at {time_string}\n")
            
            # Set the root directory for simulations and netlisting
            user = os.getlogin()
            sim_root_dir = f"{rg.DEFAULT_SIM_DIRECTORY}/{user}/{self.rundir}"
            write_file.write(f"envSetVal(\"asimenv.startup\" \"projectDir\" 'string \"{sim_root_dir}\")")

            write_file.write(self.ocn_script)
            #Append an exit statement to the output of OCEAN scripts to avoid going into 
            #interactive mode.
            if not interactive:
                write_file.write("\nexit()")


    def run(self, interactive=False, quiet=False):
        """Run the Recipe"""

        ## 0) Skip simulation if instructed.
        if rg.GLOBAL_SKIP_SIMULATION:
            self.log.info("Skipping simulations due to GLOBAL_SKIP_SIMULATION flag")
            self.do_post_run_tasks()
            return
        
        
        ## 1) Check that all appropriate variables are defined. ##
        if self.rundir is None:
            self.log.error("Need to specify a rundir before Recipe.run()")
            return

        if self.cdslib is None:
            self.log.error("Need to specify cds.lib file before Recipe.run()")
            return
            
        if os.system("which ocean") != 0:
            self.log.error("Cannot find 'ocean' executable on your path.")
            return
        

        


        ## 2) Final compilation of recipe. ##
        self.compile_recipe(interactive)
        self.log.info("Running simulation...")
        
        ## 3) Run! ##
        sim_log = os.path.join(self.full_rundir, "simulation.log")
        sim_log_short = os.path.join(self.rundir,"simulation.log")
        cds_log = "cds.log" #Rundir is already included by -log flag.

        OCEAN_COMMAND = ["ocean","-restore","compiled_recipe.ocn","-cdslib",self.cdslib, "-log", cds_log]
        
        if interactive:
            subprocess.run(OCEAN_COMMAND, 
                           cwd=self.full_rundir)
                
        else:
            with open(sim_log,"w") as write_file:
                if not quiet:
                    #Monitor the log file in a terminal separate from RHYTHM's outputs.
                    tail_proc = subprocess.Popen(["xterm","-T",f"RHYTHM ({sim_log_short})","-e","tail","-f",sim_log])
                
                subprocess.run(OCEAN_COMMAND, 
                           cwd=self.full_rundir,
                           stdout=write_file,
                           stderr=write_file)
        
        ## 4) Check for errors: ##
        with open(sim_log,"r") as read_file:
            sim_log_txt = read_file.read()
        
        if (not rg.CHECK_SIM_ERRORS) or (not self.find_log_errors(sim_log_txt)):
            self.log.info("Simulation complete!")
            if not interactive and not quiet:
                tail_proc.terminate()
            self.do_post_run_tasks()

    def find_log_errors(self, sim_log_txt):
        if "ERROR (SPECTRE-16080)" in sim_log_txt:
            self.log.error("DC Convergence Failure!")
            return True

        if "Simulation completed successfully." not in sim_log_txt:
            self.log.error("Simulation did NOT complete successfully! Check simulation.log for details.")
            return True
        
        return False
    
    def do_post_run_tasks(self):
        for a in self.post_run_tasks:
            if a[0] == "create_wave_set":
                self.waves.load_file()
            else:
                self.log.error(f"Unrecognized post-run task {a[0]}.")

    ####################
    # Analysis Methods #
    ####################

    def get_scalar_results(self, filename="scalar_results.txt"):
        return SimpleNamespace(**self.scalar_results_to_dict(filename))


    def scalar_results_to_dict(self,filename="scalar_results.txt"):
        """Loads scalar results into a dictionary."""
        path = os.path.join(self.full_rundir,filename)
        result = {}
        with open(path, "r") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    name, value = line.split("=", 1)
                    result[name.strip()] = float(value.strip())
                except ValueError:
                    raise ValueError(f"Invalid format on line {lineno}: {line}")

        return result
    

    def launch_viva(self):
        results_dir = self.get_results_dir()
        if results_dir is  None:
            self.log.info("Viva can only automatically open the results directory if it is defined in ocean/rhythm")
            viva_cmd = ["viva"]
        else:
            self.log.info(f"Opening results at {results_dir} with ViVA")
            viva_cmd = ["viva", "-datadir", results_dir]
        subprocess.run(viva_cmd)

    ####################
    # Helper Functions #
    ####################

    def _txt_to_csv(self,outputname):
        """Convert raw TXT files generated by OCEAN into CSVs"""
        txt_filename = os.path.join(self.full_rundir,f"{outputname}.txt")
        csv_filename = os.path.join(self.full_rundir,f"{outputname}.csv")
        
        rows = []
        header = None

        with open(txt_filename, "r") as f:
            for line in f:
                stripped = line.strip()

                # Ignore blank lines entirely
                if not stripped:
                    continue

                # Split on exactly FOUR spaces
                parts = re.split(r'\s{4,}', line.rstrip("\n"))


                # Remaining = data rows
                rows.append(parts)

        # Write out to CSV
        print("DBG:  ",rows)
        with open(csv_filename, "w", newline="") as out:
            writer = csv.writer(out)
            writer.writerows(rows)

    def get_results_dir(self):
        text = self.ocn_script
        m = re.search(r'resultsDir\s*\(\s*"(.*?)"\s*\)', text)
        if m:
            resultsDir = m.group(1)
            if resultsDir.startswith("/"):
                #Absolute path to resultsDir
                return resultsDir 
            else:
                #Relative path to resultsDir
                return os.path.join(self.full_rundir, resultsDir)
        return None

    def save_results_local(self):
        self.set_results_dir(self.full_rundir)

    def set_results_dir(self, new_path):
        text = self.ocn_script
        lines = text.splitlines(keepends=True)

        # Regex to match existing resultsDir("...")
        pattern = re.compile(r'(resultsDir\s*\(\s*")(.*?)(".*\))')

        replaced = False
        updated_lines = []
        
        for line in lines:
            # If resultsDir(...) exists, replace its path
            m = pattern.search(line)
            if m and not replaced:
                line = pattern.sub(rf'\1{new_path}\3', line)
                replaced = True
                
            updated_lines.append(line)

        # If replaced, we're done
        if replaced:
            self.ocn_script = "".join(updated_lines)
            return

        # Otherwise, insert resultsDir after the first "simulator" line
        insert_line = f'resultsDir( "{new_path}" )\n'
        final = []
        inserted = False

        for line in updated_lines:
            final.append(line)
            if not inserted and line.lstrip().startswith("simulator"):
                final.append(insert_line)
                inserted = True

        self.ocn_script = "".join(final)
        return


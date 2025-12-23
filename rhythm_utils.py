import datetime
import shutil
import os

from rhythm_logger import RhythmLogger



si_prefix_letter = ['z', '  a',   'f',   'p',   'n',  'u',  'm', '', 'k', 'M', 'G', 'T']
si_prefix_value  = [1e-21, 1e-18, 1e-15, 1e-12, 1e-9, 1e-6, 1e-3,1 , 1e3, 1e6, 1e9, 1e12]

#Returns a string representing a floating point number in SI format.
def si_fmt(number):
    si_offset = 7
    sign = ""
    if number < 0:
        sign = "-"
        number = abs(number)
        
    if number != 0:
        
        while number > 1000:
            number = number/1000
            si_offset = si_offset + 1
            if si_offset == len(si_prefix_letter)-1:
                break
        
        while number < 1:
            number = number*1000
            si_offset = si_offset - 1
            if si_offset == 0:
                break

    return sign + str(round(number, 3))+ si_prefix_letter[si_offset]



def str_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def str_datetimestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_hms(seconds: int) -> str:
    """Convert seconds into a string like '2h 5m 10s', 
    omitting hours/minutes when they are zero."""
    if seconds < 0:
        raise ValueError("seconds must be non-negative")

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    parts = []
    if h > 0:
        parts.append(f"{h}h")
    if m > 0 or h > 0:   # include minutes if nonzero OR if hours were shown
        parts.append(f"{m}m")
    parts.append(f"{s}s")

    return " ".join(parts)



class Record():

    def __init__(self, filename):
        self.filename = filename
        self.log = RhythmLogger(name="record")
        
    
        if os.path.isfile(filename) and os.path.getsize(filename) > 0:
            self.log.warning(f"Overwriting previous record at {filename}")
            #Preserve a copy of the previous record, just in case we didn't
            #actually want to overwrite it. :)
            shutil.copy(filename, filename+"~")

        #If the directory this record lives in doesn't exist, then make it.
        directory = os.path.dirname(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)

        #Start off the record, overwriting whatever was there.
        #print(f"<DBG> starting new record at {self.filename}")
        with open(self.filename,'w') as write_file:
            write_file.write(f"//RHYTHM Record generated at {str_datetimestamp()}\n")


    def write(self, write_string):
        #print(f"<DBG> writing to record at {self.filename}")
        with open(self.filename,'a') as write_file:
            write_file.write(write_string)
        self.log.info(write_string)

    def writeln(self,write_string):
        self.write(write_string+"\n")





class PnoiseAnalysis():

    DOCS = {"start" : "start frequency [Hz]",
            "stop"  : "stop frequency [Hz]",
            "pnoisemethod": "string: fullspectrum or default",
            "noisetype" : "string: timeaverage, sampled",
            "noise_p" : "positive terminal for voltage noise measurement",
            "noise_n" : "negative terminal for voltage noise measurement",
            "trig_p"  : "positive terminal of the sample trigger",
            "trig_n"  : "negative terminal of the sample trigger",
            "trig_dir": "trigger direction (rise or fall)",
            "trig_thresh": "trigger threshold [V]"}

    ALLOWED_VALS = {"pnoisemethod": ["fullspectrum","default"],
                    "noisetype"   : ["timeaverage","sampled"],
                    "trig_dir": ["rise", "fall"]}


    def __init__(self):
        self.start = None
        self.stop = None
        self.pnoisemethod = None
        self.noisetype = None 
        self.noise_p = None
        self.noise_n = None
        self.trig_p = None
        self.trig_n = None
        self.trig_dir = None
        self.trig_thresh = None

        self.args = []

    def check_fields(self, fields, reason):
        """Checks if the listed fields have (1) been assigned to something other than None, and
           (2) if they have ALLOWED_VALS then the assigned value is one of ALLOWED_VALS."""
        fields_correct = True
        for f in fields:
            val = getattr(self,f)
            if val is None:
                print(f"ERROR: you must set field {f} ({self.DOCS[f]}). Reason: {reason}")
                fields_correct = False
            elif f in self.ALLOWED_VALS.keys():
                if val not in self.ALLOWED_VALS[f]:
                    legal_vals = ", ".join(self.ALLOWED_VALS[f])
                    print(f"ERROR: field {f} has an illegal value {val}. Legal values: {legal_vals}")
                    fields_correct = False

        return fields_correct
        
    def validate(self):
        """Validates that the fields supplied by the user are sufficient to build a valid
           Pnoise analysis. Returns True or False."""
        valid1 = self.check_fields(["start","stop","pnoisemethod","noisetype","noise_p","noise_n"],
                             "Field required by default.")

        if self.noisetype == "sampled":
            valid2 = self.check_fields(["trig_p","trig_n","trig_dir","trig_thresh"],
                                       "Required for sampled pnoise analysis.")
        else:
            valid2 = True
            
        return (valid1 and valid2)
        


    def compile(self):
        if not self.validate():
            return None
        

        self.args += ["?start",f"\"{self.start}\"","?stop",f"\"{self.stop}\""]
        self.args += ["?pnoisemethod",f"\"{self.pnoisemethod}\""]

        if self.noisetype == "timeaverage":
            self.args += ["?p",f"\"{self.noise_p}\"","?n",f"\"{self.noise_n}\""]
            self.args += ["?noiseout","list(\"usb\")"]

        elif self.noisetype == "sampled":
            self.args += ["?noisetype", "\"sampled\""]
            self.args += ["?noisetypeUI1", "\"sampled(jitter)\""]
            self.args += ["?measTableData", self.build_measTableData()]
            

        command = "analysis( 'pnoise " + " ".join(self.args) + " )\n"

        return command
        

    def to_stage(self):
        """Output an OCEAN snippet stage for this analysis."""
        snip = self.compile()
        if snip is None:
            return None
        else:
            return ("ocnSnip",snip)


    
    def build_measTableData(self):
        """Hacky way to build measTableData argument for the most common
           sampled noise measurement I want to do."""
        tab = ["" for _ in range(26)]

        tab[0] = "1"
        tab[1] = "Edge Crossing" #type of trigger
        tab[2] = "voltage"  #trig modality
        tab[3] = str(self.trig_p)
        tab[4] = str(self.trig_n)
        tab[5] = "-"
        tab[6] = str(self.trig_thresh)
        tab[7] = "1"    #Edge number (presumably)
        tab[8] = str(self.trig_dir)
        tab[9] = "-"
        tab[10] = "voltage" #noise modality
        tab[11] = str(self.noise_p)
        tab[12] = str(self.noise_n)
        tab[13] = "-"
        tab[14] = "-"
        tab[15] = "-"
        tab[16] = "rise"
        tab[17] = "voltage"
        tab[18] = "-"
        tab[19] = "-"
        tab[20] = "-"
        tab[21] = "-"
        tab[22] = "-"
        tab[23] = "nil"
        tab[24] = "-"
        tab[25] = "t"

        return "list(\"" + ";".join(tab) + "\")"

        

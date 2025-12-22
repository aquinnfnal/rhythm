import datetime
import shutil
import os

from rhythm_logger import RhythmLogger



si_prefix_letter = ['z', '  a',   'f',   'p',   'n',  'u',  'm', '', 'k']
si_prefix_value  = [1e-21, 1e-18, 1e-15, 1e-12, 1e-9, 1e-6, 1e-3,1 , 1e3]

#Returns a string representing a floating point number in SI format.
def si_fmt(number):
    si_offset = 7
    sign = ""
    if number < 0:
        sign = "-"
        number = abs(number)

    while number > 1000:
        number = number/1000
        si_offset = si_offset + 1

    while number < 1:
        number = number*1000
        si_offset = si_offset - 1

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
        print(f"<DBG> starting new record at {self.filename}")
        with open(self.filename,'w') as write_file:
            write_file.write(f"//RHYTHM Record generated at {str_datetimestamp()}\n")


    def write(self, write_string):
        print(f"<DBG> writing to record at {self.filename}")
        with open(self.filename,'a') as write_file:
            write_file.write(write_string)
        self.log.info(write_string)

    def writeln(self,write_string):
        self.write(write_string+"\n")

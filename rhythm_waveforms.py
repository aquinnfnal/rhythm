
import re
import numpy as np
from rhythm_logger import RhythmLogger


def custom_interp(x_val, x, y):
    """np.interp() can only handle x-values that monotonically increase. That's fine
       for interpolating to get a y-value, but for  x_when_y_at, we need to be able
       to handle arbitrary y data.
       This function finds the first interval [x0,x1] that encompasses the desired x 
       value and does 2-pt linear interpolation on that interval."""
    for i in range(len(x)-1):
        if x[i] < x_val and x[i+1] >= x_val or x[i] > x_val and x[i+1] <= x_val:
            return y[i] + (y[i+1]-y[i]) * (x_val - x[i]) / (x[i+1] - x[i])
        
    return None
            

def lerp(x, x0, y0, x1, y1):
    """Linearly interpolate y at x between (x0, y0) and (x1, y1)."""
    if x1 == x0:
        raise ValueError("x0 and x1 must be different")

    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)



class Waveform:
    def __init__(self, x, y, name="waveform"):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.name = name
        self.log = RhythmLogger(name="waveform")

    def min(self):
        return np.min(self.y)

    def max(self):
        return np.max(self.y)

    def value_at(self, x_value):
        if x_value < self.x.min() or x_value > self.x.max():
            self.log.warning(
                f"{self.name}: interpolation point {x_value} is outside data range"
            )
            return None

        return np.interp(x_value, self.x, self.y)
    
    def x_when_y_at(self, y_value):
        if y_value < self.y.min() or y_value > self.y.max():
            self.log.warning(
                f"{self.name}: interpolation point {y_value} is outside data range"
            )
            return None

        print(y_value)
        print(self.y)
        print(self.x)
        result =  custom_interp(y_value, self.y, self.x)
        print(result)
        if result is None:
            self.log.error(f"Failed to interpolate {self.name}.x_when_y_at({y_value})")
        return result

    def __add__(self, other):
        self._check_compatibility(other)
        return Waveform(self.x, self.y + other.y, name=f"({self.name}+{other.name})")

    def __sub__(self, other):
        self._check_compatibility(other)
        return Waveform(self.x, self.y - other.y, name=f"({self.name}-{other.name})")

    def _check_compatibility(self, other):
        if not np.array_equal(self.x, other.x):
            raise ValueError("Independent variables do not match")


# WaveformSet is lazy, you give it a filename (which need not exist) when
# you initialize it. Then you can call load_file() later to get the data 
# when it exists.

class WaveformSet:
    def __init__(self, filename, y_names, x_name=None):
        self.x_name = x_name
        self.y_names = y_names
        self.filename = filename

    def load_file(self):
        with open(self.filename, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        data = []
        first_line = True
        for line in lines:
            if first_line: #Skip the first line (headers)
                first_line = False
                #If we didn't provide an x_name, it's the first bit of the header.
                if self.x_name is None:
                    self.x_name = line.split()[0]
                continue
            columns = re.split(r"\s{4,}", line)
            data.append([float(c) for c in columns])

        data = np.array(data)
        x = data[:, 0]
        waveforms = {}

        #For columsns 1 to N...
        for i in range(1, data.shape[1]):
            waveforms[self.y_names[i-1]] = Waveform(x, data[:, i], name=self.y_names[i-1])

        self.x = x
        self.waveforms = waveforms

    def get(self, name):
        return self.waveforms[name]

    def load_additional_file(self, filename, prefix="extra"):
        x_new, new_waveforms = self._load_file(filename)

        for name, wf in new_waveforms.items():
            if not np.array_equal(self.x, x_new):
                interpolated_y = np.interp(self.x, wf.x, wf.y)
                wf = Waveform(self.x, interpolated_y, name=f"{prefix}_{name}")

            self.waveforms[wf.name] = wf

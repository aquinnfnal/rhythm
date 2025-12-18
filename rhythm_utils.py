import datetime



si_prefix_letter = ['z', '  a',   'f',   'p',   'n',  'u',  'm']
si_prefix_value  = [1e-21, 1e-18, 1e-15, 1e-12, 1e-9, 1e-6, 1e-3]

#Returns a string representing a floating point number in SI format.
def si_fmt(number):
    si_offset = 0
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

    return sign + str(round(number, 3))+ si_prefix_letter[si_offset+6]



def str_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def str_datetimestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

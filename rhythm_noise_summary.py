import sys
import os
from datetime import datetime
from collections import defaultdict, namedtuple

#First word of each line in the Cadence Noise Results files which does NOT represent a contributor.
META_LINES = ["Device ", "Integrated ", "Total ","No ","The "]


# Each line in a Cadence Noise Summary is a "Noise Contributor" with the following four columns:
# - device:  Name of the device
# - param:   Which noise parameter this is, i.e. flicker vs shot
# - noise:   The raw amount of noise contributed, typically in V^2
# - percent: % of the total noise that this contributor is responsible for.
Contributor = namedtuple("Contributor", ["device", "param", "noise", "percent"])

def parse_rules(rules_filename):
    """Given the name of a rules file, this function will parse the lines in that file
       into a list of dicts, with each line/rule represented by one dictionary."""
    groups = []
    
    with open(rules_filename, "r") as f:
        for line in f:
            tokens = line.strip().split()
            # Each rule should define a group, so it should start with GROUP_NAME.
            if not tokens or tokens[0] != "GROUP_NAME":
                continue

            group = {
                "name": tokens[1],
                "device_includes": [],
                "param_includes": [],
                "scale": 1.0,
            }

            i = 2
            while i < len(tokens):
                if tokens[i] == "DEVICE_INCLUDES":
                    i += 1
                    while i < len(tokens) and tokens[i] not in {"PARAM_INCLUDES", "SCALE_BY"}:
                        group["device_includes"].append(tokens[i])
                        i += 1
                elif tokens[i] == "PARAM_INCLUDES":
                    i += 1
                    while i < len(tokens) and tokens[i] not in {"DEVICE_INCLUDES", "SCALE_BY"}:
                        group["param_includes"].append(tokens[i])
                        i += 1
                elif tokens[i] == "SCALE_BY":
                    i += 1
                    group["scale"] = float(tokens[i])
                    i += 1
                else:
                    i += 1
            groups.append(group)
            
    #Finally, make sure the special group "_ungrouped" is a group:
    groups.append({
                "name": "_ungrouped",
                "device_includes": [],
                "param_includes": [],
                "scale": 1.0,
            })
    return groups


def parse_noise_file(noise_filename):
    """Given a noise file, this function will parse every line into a Contributor() object"""
    data = []
    with open(noise_filename, "r") as f:
        for line in f:
            #Ignore blank lines and lines that contain metadata instead of a contributor.
            if line.strip() == "" or any([line.strip().startswith(a) for a in META_LINES]):
                continue
            try:
                device, param, noise_str, percent_str = line.strip().split(None, 3)
                noise = float(noise_str)
                percent = float(percent_str.strip('%'))
                data.append(Contributor(device=device, param=param, noise=noise, percent=percent))
            except ValueError:
                continue  # Skip malformed lines
    return data


def get_single_noise_contributor(noise_data,device,param):
    
    #noise_data can be a file path.
    if type(noise_data) == str:
        noise_data = parse_noise_file(noise_data)
        

    for c in noise_data:
        if c.device == device and c.param == param:
            return c.noise


    print("RHYTHM NOISE PARSING ERROR: Could not identify a noise result for {device} {param}")
    return None
    


def match_rule(contributor, group):
    """Returns True if the given Contributor object falls under the rule specified by group."""
    device_match = (
        not group["device_includes"] or
        any(substr in contributor.device for substr in group["device_includes"])
    )
    param_match = (
        not group["param_includes"] or
        any(substr in contributor.param for substr in group["param_includes"])
    )
    return device_match and param_match




def summarize(noise_data, groups):
    """Given a list of Contributor objects and a list of rules/groups (parsed from the Cadence noise summary file and 
       the rules file respectively), this function builds a summary dictionary of how much noise is in each group."""
    
    ## STEP 1: Split the list of contributors into lists that correspond to each group.
    grouped_contributors = defaultdict(list)

    #print(noise_data)
    #print(groups)

    for c in noise_data:
        matched = False
        for group in groups:
            if match_rule(c, group):
                #!! Apply the scale factor here !!
                scaled_c = Contributor(
                    device=c.device,
                    param=c.param,
                    noise=c.noise * group["scale"],
                    percent=c.percent
                )
                grouped_contributors[group["name"]].append(scaled_c)
                matched = True
                break  # Only match to the first group
        if not matched:
            # Assign to _ungrouped group without scaling
            grouped_contributors["_ungrouped"].append(c)

    summary = []
    
    ## STEP 2: Create summary dict
    for group_name, contributors in grouped_contributors.items():
        total_noise = sum(c.noise for c in contributors)
        top_contributors = sorted(contributors, key=lambda x: x.noise, reverse=True)[:3]
        top_noise = sum(c.noise for c in top_contributors)
        top_percentage = (top_noise / total_noise) * 100 if total_noise > 0 else 0
        group_scale = next(item for item in groups if item["name"] == group_name)["scale"]


        summary.append({
            "group_name": group_name,
            "scale_factor": group_scale,
            "total_noise": total_noise,
            "num_contributors": len(contributors),
            "top_contributors": top_contributors,
            "top_percentage": top_percentage,
        })

    return summary


def write_summary(output_filename, noise_filename, rules_filename, summary):
    """Writes noise summary to file."""
    with open(output_filename, "w") as f:
        f.write(f"Noise Summary Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Noise file: {os.path.basename(noise_filename)}\n")
        f.write(f"Rules file: {os.path.basename(rules_filename)}\n\n")

        tot_noise = 0

        for group in summary:
            f.write(f"Group: {group['group_name']}")
            if group['scale_factor'] != 1:
                f.write(f" (Scaled by {group['scale_factor']}x)\n")
            else:
                f.write("\n")
            f.write(f"  Total Noise: {group['total_noise']:.4e}\n")
            f.write(f"  Contributors: {group['num_contributors']}\n")
            f.write(f"  Top 3 Contributors:\n")
            for i, c in enumerate(group["top_contributors"], start=1):
                f.write(f"    {i}. Device: {c.device}, Param: {c.param}, Noise: {c.noise:.4e}\n")
            f.write(f"  Top 3 Contribution %: {group['top_percentage']:.2f}%\n\n")

            if not group['group_name'].startswith('ignore'):
                tot_noise += group['total_noise']

        f.write(f"** Total Noise from Non-Ignored Groups: {tot_noise:.4e} **\n")
        return tot_noise

def rhythm_noise_summary(noise_file, rules_file, output_file):

    rules = parse_rules(rules_file)
    noise_data = parse_noise_file(noise_file)
    summary = summarize(noise_data, rules)
    tot_noise = write_summary(output_file, noise_file, rules_file, summary)
    print(f"Noise Summary written to {output_file}")
    return tot_noise

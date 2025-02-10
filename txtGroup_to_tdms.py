"""Merge noise txt waveforms into LabVIEW TDMS file"""
import sys
import os
import re
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import OrderedDict
import matplotlib.pyplot as plt
import matplotlib
import math

import numpy as np
import pandas as pd
import nptdms
from nptdms import TdmsWriter, RootObject, GroupObject, ChannelObject

print(sys.executable)
print(sys.version)
print("numpy:", np.__version__)
print("pandas:", pd.__version__)
print("nptdms:", nptdms.__version__)

matplotlib.use('tkagg')
__version__ = "0.1.4" # 12.07.2024

col_time = 0

def delete_NaN(x):
       
    xi = np.arange(len(x))
    mask = np.isfinite(x)
    xfiltered = np.interp(xi, xi[mask], x[mask]) 
        
    return xfiltered

def check_nptdms_version():
    #required_version = "0.28.0"
    required_version = "1.7.0"
    if nptdms.__version__ == required_version:
        return True
    else:
        msg_str = (
            f"nptdms version: {nptdms.__version__} does not match required (tested): {required_version}\n"
            "conversion may not be correct"
        )
        print(msg_str)
        # Create Tk root
        root = tk.Tk()
        # Hide the main window
        root.withdraw()
        msg = messagebox.showerror(title="nptdms version ERROR", message=msg_str)
        return False

def convert_to_float(word, ignore_minus_sign=False):
    if ignore_minus_sign:
        non_decimal = re.compile(r'[^\d.]+')
    else:
        non_decimal = re.compile(r'[^-\d.]+')
    word = non_decimal.sub('', word)
    return float(word)

def find_unit(text):
    start = text.find("[")
    end = text.find("]")
    unit = text[start+1:end]
    return unit

def rms(a):
    return np.sqrt(np.mean(a**2))

def read_noise_txt(filepath):
    units = []
    channels_names = []
    df = pd.read_csv(filepath, sep="\t", skip_blank_lines=False, header=None, encoding='unicode_escape')
    
    for i in range(50):
        if df.iloc[i,0] == "Y axis unit":
            data_start = i + 1
            break
        elif df.iloc[i,0] == "DOF id":
            data_name = i
    
    data = df.iloc[data_start:, :].astype(float)
    data = data.to_numpy()
    
    new_data = []
    for i in range(len(data[0, :])):
        data_i = data[:, i]
    
        if not math.isnan(data_i[0]):
            nametype_CH = df.iloc[data_start-2, i]
            unit_CH = df.iloc[data_start-1, i]
            name_CH = df.iloc[data_name, i]
            if i == 0 :
                time = delete_NaN(data_i)
            elif name_CH !="DOF id":
                new_data.append(delete_NaN(data_i))
                channels_names.append(name_CH)
                units.append(unit_CH)
                
    return new_data, time, units, channels_names

def get_filenames_and_dirname():
    # Create Tk root
    root = tk.Tk()
    # Hide the main window
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)

    filepaths = filedialog.askopenfilename(multiple=True)
    if not filepaths:
        return None, None

    filenames = []
    for filepath in filepaths:
        if filepath.endswith(".txt"):
            basename = os.path.basename(filepath)
            filename, extension = os.path.splitext(basename)
            filenames.append(filename)
    dirname = os.path.dirname(filepath)
    return filenames, dirname

def write_single_tdms_file(basename, dirname):
    
    #for key, value in channels_map.items():
    for f in basename:
        f_txt = os.path.join(dirname, f + ".txt")
        channels_data, time, units, channels_names = read_noise_txt(f_txt)
    
        dt = time[1]-time[0]
        fs = round(1/dt)
        root_object = RootObject()
        group_object = GroupObject("Measurement")

        out_filepath = os.path.join(dirname, f"{f}.tdms")
        now = datetime.datetime.now()
        channel_objects = []
        
        for i in range(len(channels_names)):
        
            channel_object = ChannelObject("Measurement", channels_names[i], channels_data[i], properties={
                    "NI_Unit": units[i],
                    "Unit": units[i],
                    "NI_ChannelName": channels_names[i],
                    "wf_increment": float(1/fs),
                    "wf_samples": fs, 
                    "wf_start_offset": 0,
                    "wf_time_pref": "relative",
                    # "wf_start_time": now,
                    "wf_xname": "Time",
                    "wf_xunit_string": "s",
                    "unit_string": units[i],})
            channel_objects.append(channel_object)
        

        with TdmsWriter(out_filepath) as tdms_writer:
            
            for i in range(len(channel_objects)):
                if i==0:
                    tdms_writer.write_segment([root_object,group_object,channel_objects[i]])
                else:
                    tdms_writer.write_segment([channel_objects[i]])
        
        print("Saved:", out_filepath)

def main():
    print("Select files")
    filenames, dirname = get_filenames_and_dirname()
    if filenames is None:
        print("Canceled")
        return
    

    write_single_tdms_file(filenames, dirname)
    print("Done")
    input("Press enter to continue")

if __name__ == "__main__":
    status = check_nptdms_version()
    if status:
        main()

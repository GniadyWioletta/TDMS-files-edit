"""Merge noise txt waveforms into LabVIEW TDMS file"""
import sys
import os
import re
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import OrderedDict
import scipy
import mne

import numpy as np
import pandas as pd
import nptdms
from nptdms import TdmsWriter, RootObject, GroupObject, ChannelObject

print(sys.executable)
print(sys.version)
print("numpy:", np.__version__)
print("pandas:", pd.__version__)
print("nptdms:", nptdms.__version__)

__version__ = "0.1.3" # 23.06.2021

# change this
CHANNELS_MAP = OrderedDict({
    "wave1": "Acc",
    "wave2": "Pressure",
    "wave3": "Displacement",
    #"wave4": "Force",
    #"wave5": "Waveform",
})

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

def read_noise_txt(df, mdata, int):
    
    item = mdata[int]
    #raw = mne.io.RawArray(eeg_data, info)
    a = item[0][0][0]
    title = a[0][0]
    T = len(a)
    
    part_no = df.iloc[0, 1]
    amplitude = convert_to_float(df.iloc[2, 1], ignore_minus_sign=True)
    freq = convert_to_float(df.iloc[3, 1])
    temperature = convert_to_float(df.iloc[4, 1])
    side_load = df.iloc[5, 1]
    unit = find_unit(df.iloc[11, 0])
    
    params = {}
    params["part_no"] = part_no
    params["amplitude"] = amplitude
    params["freq"] = freq
    params["temperature"] = temperature
    params["side_load"] = side_load
    params["unit"] = unit
    
    data = df.iloc[12:, :].astype(float)
    data = data.to_numpy()
    return data, params

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
        if filepath.endswith(".mat"):
            basename = os.path.basename(filepath)
            filename, extension = os.path.splitext(basename)
            #if "wave" in filename:
            filenames.append(filename)
    dirname = os.path.dirname(filepath)
    return filenames, dirname

def get_basename_from_filename(filename: str):
    #basename = filename.split("wave")[0]
    #return basename.strip()
    return filename

def write_single_tdms_file(basename, dirname):
    channels_map = CHANNELS_MAP

    filepath = os.path.join(dirname, basename + ".mat")
    channels_names = []
    wave_names = []
    channels_data = []
    units = []
    basename_txt = os.path.basename(filepath)
    df = scipy.io.loadmat(filepath)
    mdata = df['Ch']
    
    n_time_samples = mdata.shape[1]
    info = mne.create_info(ch_names=[f"ch_{i + 1}" for i in range(mdata.shape[0])],sfreq=1000,ch_types='Ch')
    for i in range(mdata.shape[0]-1):
        channel_data, params = read_noise_txt(df, mdata, i)
        y = channel_data[:, 0]
        time = channel_data[:, 1]
        dt = time[1]-time[0]
        fs = round(1/dt)
        print(basename_txt, "fs =", fs, "hz", "unit =", params["unit"])
        channels_data.append(y)
        units.append(params["unit"])

    # write TDMS
    root_object = RootObject(properties={
        "nptdms__version__": nptdms.__version__,
    })

    group_params = params.copy()
    del group_params["unit"]
    group_object = GroupObject("Measurement", properties=group_params)

    # dirname = os.path.dirname(filepath)
    out_filepath = os.path.join(dirname, f"{basename}.tdms")
    now = datetime.datetime.now()
    with TdmsWriter(out_filepath) as tdms_writer:
        for i, y in enumerate(channels_data):
            channel_object = ChannelObject("Measurement", channels_names[i], y, properties={
                "NI_Unit": units[i],
                "NI_ChannelName": channels_names[i],
                "wf_increment": float(1/fs),
                "wf_samples": fs, # 12800
                "wf_start_offset": 0,
                "wf_time_pref": "relative",
                # "wf_start_time": now,
                "wf_xname": "Time",
                "wf_xunit_string": "s",
                "unit_string": units[i],
            })
            print(f"Writing wave {wave_names[i]} as:", channels_names[i], units[i])
            tdms_writer.write_segment([
                root_object,
                group_object,
                channel_object])
    print("Saved:", out_filepath)

def main():
    print("Select files")
    filenames, dirname = get_filenames_and_dirname()
    if filenames is None:
        print("Canceled")
        return
    
    basenames = list(map(get_basename_from_filename, filenames))
    unique_basenames = np.unique(basenames)

    # convert single measurement
    for unique_basename in unique_basenames:
        print("Processing:", unique_basename)
        write_single_tdms_file(unique_basename, dirname)
    print("Done")
    input("Press enter to continue")

if __name__ == "__main__":
    status = check_nptdms_version()
    if status:
        main()

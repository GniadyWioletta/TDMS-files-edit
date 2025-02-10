from nptdms import TdmsFile, TdmsWriter, RootObject, GroupObject, ChannelObject 
import scipy as sc
from scipy import signal as sp
import numpy as np
import os

def FFT(input, fs):

    N = len(input)
    win = sp.windows.hamming(N)
    fft_x = sc.fft.fft(input * win)
    freq = sc.fft.fftfreq(N, 1/fs)

    fft_x = sc.fft.fftshift(fft_x)
    freq = sc.fft.fftshift(freq)
            
    half_idx = len(fft_x)//2
    fft_x = fft_x[half_idx:]
    freq = freq[half_idx:]

    fft_x = 2.0/N * fft_x  # Or 1.0/len(fft_x) * fft_x

    win_mean = win.mean()
    correction_factor = 1/win_mean

    fft_x = fft_x * correction_factor / np.sqrt(2)
    spectrum = abs(fft_x)

    #look for max below 40Hz
    try:
        idx_40Hz = np.where(freq > 40)
        idx_max = np.where(np.max(spectrum[:idx_40Hz[0][0]]) == spectrum[:idx_40Hz[0][0]])
        max_freq = freq[idx_max]
    except:
        max_freq = 0

    return spectrum, freq, max_freq

def FindFreq(input, fs):
    peaks_pos_idx,_ = sp.find_peaks(input,prominence=1,width=2)
    
    indx = 0
    mfreq = 0
    
    dat = input[peaks_pos_idx]
    
    for idx in range(len(peaks_pos_idx)):
        if input[peaks_pos_idx[idx]]>1.5 and input[peaks_pos_idx[idx]]<10:
            peaks_pos_idx = peaks_pos_idx[idx:]
            break
    
    for idx in range(len(peaks_pos_idx)-2):
        
        input_segment_fft = input[peaks_pos_idx[idx]:peaks_pos_idx[idx+2]]
        [Spec, Freq, max_freq] = FFT(input_segment_fft, fs)
        
        #if max_freq[0]> 1.3 and max_freq[0]<1.8:
        #if max_freq[0]> 0.6 and max_freq[0]<1.3:
        if max_freq[0]> 0.4 and max_freq[0]<1.3:
            
            indx_init = peaks_pos_idx[idx]
            
            indx = indx_init
            mfreq = max_freq[0]

            break
      
    return indx, mfreq

if __name__ == "__main__":
    
    path_dir =""
    
    new_path = os.path.join(path_dir, "out")
    try:
        os.mkdir(new_path) 
    except:
        new_path = new_path
    
    samp = 0
    for file in os.listdir(path_dir):
        if ".tdms" in file and not "index" in file:
            path = path_dir + "\\" + file
            Name = file[:len(file)-5] #delete .tdms
            
            tdms_file = TdmsFile.read(path)   
            all_groups = tdms_file.groups()
            try:
                group = tdms_file["Measurement"]
            except:
                for i in range(len(all_groups)):
                    group = tdms_file[all_groups[i].name]
                    if len(group._channels) >=1:
                        break
                        
            all_group_channels = group.channels()
            
            root_object = RootObject()
            group_object = GroupObject("Measurement")
            datas = np.array([])
            units = np.array([])
            txts = np.array([])
            
            indx_mm = -1
            i = -1
            
            for CH in all_group_channels:
                
                i = i + 1
                wf_increment = CH.properties["wf_increment"]
                wf_samples = 1/wf_increment
                data = CH[:]
                txt = CH.properties["NI_ChannelName"]
                
                try:
                    unit = CH.properties["NI_UnitDescription"]  
                except:
                    try:
                        unit = CH.properties["NI_Unit"]     
                    except:
                        try:
                            unit = CH.properties["Unit"]     
                        except:
                            unit = ""
                   
                if unit == "mm" :
                    indx_mm = i   
                   
                if not samp==0:  
                    if not samp==len(data):
                        data = data[:samp]
                samp = len(data)
                
                datas = np.append(datas, data)
                units = np.append(units, unit)
                txts = np.append(txts, txt)
                
            if indx_mm == -1:
                for t in range(len(txts)):
                    if "disp" in txts[t].lower():
                        indx_mm = t
                        break           
             
            with TdmsWriter(new_path + "\\" + Name + "_out" + ".tdms") as tdms_writer:
                  
                    leng = len(data)
                    datas = np.reshape(datas, [len(txts), leng])  
                    [indx, max_freq] = FindFreq(datas[indx_mm], wf_samples)
                    print(Name + " " + str(max_freq))
                    
                    #indx = indx - int(wf_samples/2)
                    
                    for i in range(len(datas)):
                        trim_data = datas[i][indx:]
                        channel_object = ChannelObject("Measurement", 
                                                   txts[i], 
                                                   trim_data, 
                                                   properties={"NI_Unit": units[i],
                                                               "NI_ChannelName": txts[i],
                                                               "wf_increment": wf_increment, 
                                                               "wf_samples": wf_samples,
                                                               "wf_start_offset": 0, 
                                                               "wf_time_pref": "relative",
                                                               "wf_xname": "Time",
                                                               "wf_xunit_string": "s",
                                                               "unit_string": units[i],})
                    
                        if i ==0:
                            tdms_writer.write_segment([root_object,group_object,channel_object])
                        else:
                            tdms_writer.write_segment([channel_object])
                        
    print("FINISH")
            


            

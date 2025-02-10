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
        
        if max_freq[0]> 0.5 and max_freq[0]<1.3:
            
            indx_init = peaks_pos_idx[idx]
            
            indx = indx_init
            mfreq = max_freq[0]

            break
      
    return indx, mfreq

if __name__ == "__main__":
    
    path_dir = "C:\\Simcenter\\Testlab Data\\Projects\\Noise - Piston\\BMW\\G2x LCI\\CUU\\Dane od Elaine\\13517-8\\Dane mat\\Suspect_Part"
    
    files_paths = np.array([]) 
    names = np.array([]) 
    short_names = np.array([]) 
    processed_names = np.array([]) 
    g_const = 0.10197
    short_name = "_x"
    
    new_path = os.path.join(path_dir, "out")
    try:
        os.mkdir(new_path) 
    except:
        new_path = new_path
        
    for file in os.listdir(path_dir):
        if ".mat" in file:
            path = path_dir + "\\" + file
            Name = file[:len(file)-4] #delete .mat
            
            files_paths = np.append(files_paths, path)
            names = np.append(names, Name)
            pos = Name.find("rofile")
            short_name = Name[:pos+7]
            short_names = np.append(short_names, short_name)
        
        elif os.path.isdir(path_dir + "\\" + file) == True:
            for file_1 in os.listdir(path_dir + "\\" + file):
                if ".mat" in file_1:
                    path = path_dir + "\\" + file + "\\" + file_1
                    Name = file_1[:len(file_1)-4] #delete .mat
                
                    files_paths = np.append(files_paths, path)
                    names = np.append(names, Name)
                    pos = Name.find("rofile")
                    short_name = Name[:pos+7]
                    short_names = np.append(short_names, short_name)

                
    short_names = np.unique(short_names)
    
    for n in range(len(short_names)):
        
        #Mozna zmienic jak sie nie bedzie zgadzalo
        pos1 = short_names[n].find(short_name)-1
        pos2 = short_names[n].find(short_name)
        name1 = short_names[n][:pos1]
        name2 = short_names[n][pos2:]
        new_name = name1 + name2
        
        for m in range(len(names)):
            
            if name1 in names[m] and name2 in names[m]:
                flag = False
                if not len(processed_names)<1:
                    for el in range(len(processed_names)):
                        if processed_names[el] == names[m]:
                            flag = True
                            break
                if flag:
                    continue
                processed_names = np.append(processed_names, names[m])
                Name = names[m]
                path = files_paths[m]
                
                txts = np.array([])
                datas = np.array([])
                units = np.array([])
                indx_mm = -1
    
                mat = sc.io.loadmat(path)
                
                #print(mat.keys())
                #print(f" channels {[mat['Ch'][i][0][0][0][1][0] for i in range(len(mat['Ch']))   ]} ")
            
                wf_samples = mat['fs'][0][0]
                wf_increment = 1/wf_samples
            
                root_object = RootObject()
                group_object = GroupObject("Measurement")
                
                #Część jest w 10 elemencie, część w 3
                NIname_channel = -1
                for ss in range(len(mat)):
                    info = mat['Ch'][0][0][0][0][ss]
                    if len(info)>5:
                        data_channel = ss
                    elif len(info)==1:
                        if "cDAQ" in info[0]:
                            NIname_channel = ss
                            
                if NIname_channel == 0:
                    name_channel = 1
                else:
                    name_channel = 0
                        
                    
                time = wf_increment * np.arange(mat['Ch'][0][0][0][0][data_channel].shape[0])
                
                exr_path = os.path.join(new_path, new_name)
                try:
                    os.mkdir(exr_path) 
                except:
                    exr_path = exr_path
                
                with TdmsWriter(exr_path + "\\" + Name + "_out" + ".tdms") as tdms_writer:
                    for i in range(len(mat['Ch'])):
                        
                        txt = mat['Ch'][i][0][0][0][name_channel][0]
                        data = mat['Ch'][i][0][0][0][data_channel]
                        data = np.reshape(data, data.shape[0])
                        txt = txt.lower()
                        if txt == "force":
                            unit = "N"
                        elif txt == "stroke":
                            unit = "mm"
                            indx_mm = i
                            txt = "disp"
                        elif txt == "rod (vertical)":
                            unit = "g"
                            data = data*g_const
                            txt = "acc"
                        elif txt =="mm":
                            unit = txt
                            txt = "disp"
                            indx_mm = i
                        elif txt == "m/s^2":
                            unit = txt
                            txt = "acc"
                            data = data*g_const
                        elif txt == "ºc":
                            unit = txt
                            txt = "temp"
                        elif txt == "v":
                            unit = txt
                            txt = "force"
                        else:
                            txt = txt
                            unit = ""
                        
                        leng = len(data)
                        txts = np.append(txts, txt)
                        datas = np.append(datas, data)
                        units = np.append(units, unit)
                  
                    datas = np.reshape(datas, [len(txts), leng])  
                    [indx, max_freq] = FindFreq(datas[indx_mm], wf_samples)
                    print(Name + " " + str(max_freq))
                    
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
            


            

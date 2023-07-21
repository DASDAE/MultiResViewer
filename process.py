import pandas as pd
import numpy as np
import dascore as dc
import os
from SpoolProcessing import proc,utils

def estimate_spool_size(sp):
    data_size = 0
    for _,row in sp.get_contents().iterrows():
        timeN = (row['time_max']-row['time_min'])/row['d_time']
        chanN = (row['distance_max']-row['distance_min'])/row['d_distance']
        data_size += timeN*chanN*4/1e6
    return data_size

class MultiResProcess:

    def __init__(self):
        self.src_path = None
        self.tar_path = None
        self.raw_spool = None
        self.pre_process = None
        self.minimum_size = 200
        self.downsample_factor = 10
    
    def set_rawdata_path(self,srcpath):
        self.src_path = srcpath
        self.raw_spool = dc.spool(srcpath)
    
    def set_target_path(self,tarpath):
        self.tar_path = tarpath
    
    def set_raw_spool(self,sp):
        self.raw_spool = sp
    
    def set_pre_process(self,pre_process):
        self.pre_process = pre_process

    def set_downsample_factor(self,downsample_factor):
        self.downsample_factor = downsample_factor
    
    def set_minimum_size(self,minimum_size):
        self.minimum_size = minimum_size
    
    def downsample_process(self):

        if not os.path.isdir(self.tar_path):
            os.mkdir(self.tar_path)
            print(f'{self.tar_path} does not exist, created one')


        current_level = 0
        current_sp = self.raw_spool
        current_size = estimate_spool_size(current_sp)

        print(current_size)
        while current_size > self.minimum_size:
            
            current_level += 1
            current_folder = os.path.join(self.tar_path,str(current_level))
            print(current_folder)
            
            if os.path.isdir(current_folder):
                current_sp = dc.spool(current_folder)
                current_size = estimate_spool_size(current_sp)
            else:
                freq = 1/(current_sp.get_contents()['d_time'].iloc[0] / np.timedelta64(1,'s'))

                new_freq = freq/self.downsample_factor

                if current_level == 1:
                    proc.down_sample(current_sp,current_folder,new_freq,pre_process=self.pre_process)
                else:
                    proc.down_sample(current_sp,current_folder,new_freq,pre_process=None)
                current_sp = dc.spool(current_folder)
                current_size = estimate_spool_size(current_sp)
            
            print(current_size)
            

import opencv_wrapper
import numpy as np
import os
import struct
def calculate_packet(port_id, input_voltage,VFS):
#    VFS = 10.0
    voltage = max(-VFS, min(VFS, input_voltage))
    dac12 = int(round((voltage + VFS) / (2.0 * VFS) * 4095.0))
    dac12 = max(0, min(4095, dac12))
    packet = (port_id << 12) | dac12 
    data_bytes = struct.pack('>H', packet)       
    return data_bytes




PlayBackMode=False
user_quit=True
voltage_mock=False
playback_dir="testdata"
PortNum=16

#PortVoltages = np.arange(PortNum, dtype=np.float32)
PortVoltages=[0.0 for row in range(0,PortNum)]
#PortVoltages[0]=0.05
#PortVoltages[14]=0.1
#PortVoltages[15]=0.02
TimeNum=2
VFS = 10.0
ActuationTime=5.0
ActuationWaitTime=5
TimePoint=[0.0 for row in range(0,TimeNum)]
TimePoint[0]=0.0
TimePoint[1]=ActuationTime
TotalTime=int(ActuationTime)
path='CurrentPortVoltages.txt'
#f=file('CurrentPortVoltages.txt','w') 
with open(path, 'w', encoding='utf-8') as f:
    for ii in range(0,TimeNum):
        bin_list = []    
        for port_id in range(PortNum):
            v = PortVoltages[port_id]
            data_bytes = calculate_packet(port_id, v,VFS)
            packet_value = int.from_bytes(data_bytes, byteorder='big', signed=False)
            bin_list.append(format(packet_value, '016b'))
                    
        time_ms = TimePoint[ii] * 1000.0
        bin_str = ' '.join(bin_list)
        f.write(f"{time_ms:.3f} {bin_str}\n")
#f.close()
#opencv_wrapper.DynamicActuation(PortVoltages,PortNum,ActuationWaitTime,TotalTime,user_quit,voltage_mock)
opencv_wrapper.FeatureSelection(PlayBackMode,playback_dir)
#opencv_wrapper.ReadImage(3)         # 5
#print(str(result))

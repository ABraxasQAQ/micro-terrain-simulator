import opencv_wrapper
import numpy as np
import os
import struct
import threading
import time
def calculate_packet(port_id, input_voltage,VFS):
#    VFS = 10.0
    voltage = max(-VFS, min(VFS, input_voltage))
    dac12 = int(round((voltage + VFS) / (2.0 * VFS) * 4095.0))
    dac12 = max(0, min(4095, dac12))
    packet = (port_id << 12) | dac12 
    data_bytes = struct.pack('>H', packet)       
    return data_bytes


N=4
ActuationInSitu=False
PlayBackMode=False
user_quit=False
voltage_mock=False
LogSwitchOff=False
OutputInitialPos=False
ImportNormal=True
SaveImage=False
playback_dir="testdata"
PortNum=16
PointNum=N*N
SkipFrameNum=200
TestVoltage=0.1
TestPortId=2
for oi in range(0,6):
    PortVoltages = np.arange(PortNum, dtype=np.float32)
    for ii in range(0,PortNum):
        PortVoltages[ii]=0.0
#PortVoltages=[0.0 for row in range(0,PortNum)]
    PortVoltages[TestPortId-1]=0.1*oi
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

    opencv_wrapper.DynamicActuation(PortVoltages,PortNum,ActuationWaitTime,TotalTime,user_quit,voltage_mock,
                                    LogSwitchOff,ActuationInSitu,OutputInitialPos,ImportNormal,SaveImage)

    f=open("ResultPath.dat","r", encoding="utf-8")        
    line = f.readline()
    LineNow=line.split()
    RPath=line
    f.close()

    f=open(RPath+"/results.txt","r", encoding="utf-8")
    PosXAve=[0.0 for row in range(0,PointNum)]
    PosYAve=[0.0 for row in range(0,PointNum)]
    PosZAve=[0.0 for row in range(0,PointNum)]
    PointCount=0
    count=0

    fout=open("TestAveragePos.txt","w", encoding="utf-8")
    while True:
        line=f.readline()
        line=line.strip()
        count=count+1
        if len(line)==0:
           break
        else:
            LineNow=line.split()
            if count>1+SkipFrameNum:
                PointCount=PointCount+1
                for ii in range(0,PointNum):
                    try:       
                        PosXNow=float(LineNow[45+3*ii])
                    except:
                        PosXNow=0.0
                    try:
                        PosYNow=float(LineNow[45+3*ii+1]) 
                    except:
                        PosYNow=0.0
                    try:
                         PosZNow=float(LineNow[45+3*ii+2]) 
                    except:
                        PosZNow=0
                    PosXAve[ii]=PosXAve[ii]+PosXNow
                    PosYAve[ii]=PosYAve[ii]+PosYNow
                    PosZAve[ii]=PosZAve[ii]+PosZNow
                    fout.write('%25.15f %25.15f %25.15f' %(PosXNow,PosYNow,PosZNow))
                fout.write('\n')
    f.close() 
    fout.close()  
    fout=open("AveragePos"+str(oi+1)+".txt","w", encoding="utf-8")
    for ii in range(0,PointNum):
    
        PosXAve[ii]=PosXAve[ii]/PointCount
        PosYAve[ii]=PosYAve[ii]/PointCount
        PosZAve[ii]=PosZAve[ii]/PointCount
        fout.write('%25.15f %25.15f %25.15f' %(PosXAve[ii],PosYAve[ii],PosZAve[ii]))
        fout.write('\n')     
    fout.close() 
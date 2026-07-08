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
SkipFrameNum=0
TestVoltage=0.1
TestPortId=2
MaxVoltage=0.61
FeatureId=6
TimePerFrame=1.0/200.0
VFS = 10.0
ActuationTime=5.0
ActuationWaitTime=5
PortVoltages = np.arange(PortNum, dtype=np.float32)
for oi in range(0,1):
    f=open('CurrentVoltage.dat','r')
    line = f.readline()
    LineNow=line.split()
    PortNum=int(LineNow[0])
    TimeNum=int(LineNow[1])           

    Voltage=[[0 for col in range(0, PortNum)] for row in range(0,TimeNum+1)] 
    TimePoint=[0.0 for row in range(0,TimeNum+1)]
    for jj in range(0,TimeNum):
        line = f.readline()
        LineNow=line.split()
        TimePoint[jj]=float(LineNow[0])            
        line = f.readline()
        LineNow=line.split()    
        for ii in range(0,PortNum):
            Voltage[jj][ii]=float(LineNow[ii])
            
    f.close()
    jj=TimeNum   
    for ii in range(0,PortNum):
        Voltage[jj][ii]=Voltage[jj-1][ii] 
  
    TimePoint[TimeNum]=ActuationTime  
  
    for jj in range(0,TimeNum+1):  
        TotalVoltage=0.0
        for ii in range(0,PortNum):    
            TotalVoltage=TotalVoltage+abs(Voltage[jj][ii])
        if TotalVoltage>MaxVoltage:
            exit    
  
#    TimeNum=2


#    TimePoint[0]=0.0

    TotalTime=int(ActuationTime)
    path='CurrentPortVoltages.txt'
#f=file('CurrentPortVoltages.txt','w') 
    with open(path, 'w', encoding='utf-8') as f:
        for ii in range(0,TimeNum+1):
            bin_list = []    
            for port_id in range(PortNum):
                v = Voltage[ii][port_id]
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

    PointCount=0
    count=0

    fout=open("CurrentPosZ"+".txt","w", encoding="utf-8")
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

                    if ii==FeatureId-1:                
                        TimeNow=(PointCount-1)*TimePerFrame
                        fout.write('%25.15f %25.15f\n' %(TimeNow,PosZNow))

    f.close() 
    fout.close()  
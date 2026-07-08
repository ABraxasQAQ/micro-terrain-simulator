function Pos = GetShape_SinglePort_Dynamics(x,PortId,PortNum,TimeNum,TimePoint,MaxVoltage)



PauseTime=5.0;
filename='CurrentVoltage.dat';
fid=fopen(filename,'w');
fprintf(fid,'%8d %8d\r\n',PortNum,TimeNum);

for jj=1:TimeNum
    PortVoltages=zeros(PortNum,1);
    PortVoltages(PortId)=x(jj);
    fprintf(fid,'%25.15f\r\n',TimePoint(jj));
    for ii=1:PortNum
        fprintf(fid,'%25.15f',PortVoltages(ii));
    end
    fprintf(fid,'\r\n');
end
fclose(fid);

% Pos=[];


if max(abs(x))<MaxVoltage
    command=strcat("python SinglePort_Dynamics.py");
    status = system(command);
    Pos=load("CurrentPosZ.txt");
    pause(PauseTime);
else
    Pos=[];
end



end


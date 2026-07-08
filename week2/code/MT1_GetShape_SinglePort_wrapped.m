function Pos = MT1_GetShape_SinglePort_wrapped(x,PortId,PortNum,MaxVoltage)

PortVoltages=zeros(PortNum,1);
PortVoltages(PortId)=x(1);

filename='CurrentVoltage.dat';
fid=fopen(filename,'w');
for ii=1:PortNum
    fprintf(fid,'%25.15f\r\n',PortVoltages(ii));
end
fclose(fid);

if abs(x(1))<MaxVoltage
    command=strcat("python MT1_SinglePort_wrapped.py");
    status = system(command);
    if status ~= 0
        error("MT1_SinglePort_wrapped.py failed with status %d", status);
    end
    Pos=load("AveragePos.txt");
else
    Pos=[];
end

end

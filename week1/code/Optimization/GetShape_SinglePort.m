function Pos = GetShape_SinglePort(x,PortId,PortNum,MaxVoltage)


PortVoltages=zeros(PortNum,1);
PortVoltages(PortId)=x(1);

filename='CurrentVoltage.dat';
fid=fopen(filename,'w');
for ii=1:PortNum
    fprintf(fid,'%25.15f\r\n',PortVoltages(ii));
end
fclose(fid);

if abs(x(1))<MaxVoltage
    command=strcat("python SinglePort.py");
    status = system(command);
    Pos=load("AveragePos.txt");
else
    Pos=[];
end



end


function Pos = MT1_GetShape_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax)

PortVoltages=zeros(PortNum,1);
for ii=1:length(ActivePortIds)
    PortVoltages(ActivePortIds(ii))=x(ii);
end

filename='CurrentVoltage.dat';
fid=fopen(filename,'w');
for ii=1:PortNum
    fprintf(fid,'%25.15f\r\n',PortVoltages(ii));
end
fclose(fid);

if sum(abs(PortVoltages))<VoltageMax
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

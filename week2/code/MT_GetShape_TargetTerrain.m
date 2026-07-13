function Pos = MT_GetShape_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax)

ThisDir=fileparts(mfilename('fullpath'));
ProjectRoot=ThisDir;

PortVoltages=zeros(PortNum,1);
for ii=1:length(ActivePortIds)
    PortVoltages(ActivePortIds(ii))=x(ii);
end

filename=fullfile(ProjectRoot,'CurrentVoltage.dat');
fid=fopen(filename,'w');
for ii=1:PortNum
    fprintf(fid,'%25.15f\r\n',PortVoltages(ii));
end
fclose(fid);

if sum(abs(PortVoltages))<VoltageMax
    PythonEntry=fullfile(ThisDir,"MT_single_port.py");
    command=sprintf('python "%s" --max-total-abs-voltage %.15f',PythonEntry,VoltageMax);
    status = system(command);
    if status ~= 0
        error("MT_single_port.py failed with status %d", status);
    end
    Pos=load(fullfile(ProjectRoot,"AveragePos.txt"));
else
    Pos=[];
end

end

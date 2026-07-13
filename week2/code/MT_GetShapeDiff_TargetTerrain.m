function y = MT_GetShapeDiff_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax,TargetZ,Weights)

Pos = MT_GetShape_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax);

MeasuredZ=Pos(:,3);
TargetZ=TargetZ(:);
Weights=Weights(:);

if length(MeasuredZ) ~= length(TargetZ)
    error("MeasuredZ and TargetZ length mismatch");
end

if length(Weights) ~= length(TargetZ)
    error("Weights and TargetZ length mismatch");
end

Diff=(MeasuredZ-TargetZ).*Weights;
y=norm(Diff);

OutFileName=strcat("ErrorNow.dat");
fidout=fopen(OutFileName,'a+');
fprintf(fidout,'%25.15f\r\n',y);
fclose(fidout);

OutFileName=strcat("VoltageNow.dat");
fidout=fopen(OutFileName,'a+');
for kk=1:length(x)
    fprintf(fidout,'%25.15f',x(kk));
end
fprintf(fidout,'\r\n');
fclose(fidout);

OutFileName=strcat("TargetTerrainResult.dat");
fidout=fopen(OutFileName,'a+');
fprintf(fidout,'%25.15f',y);
for kk=1:length(x)
    fprintf(fidout,'%25.15f',x(kk));
end
for kk=1:length(MeasuredZ)
    fprintf(fidout,'%25.15f',MeasuredZ(kk));
end
fprintf(fidout,'\r\n');
fclose(fidout);

end

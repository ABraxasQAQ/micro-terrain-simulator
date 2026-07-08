function y = GetShapeDiff_SinglePort_wrapped(x,PortId,PortNum,MaxVoltage,TargetPos,FeatureId)

Pos = GetShape_SinglePort_wrapped(x,PortId,PortNum,MaxVoltage);

PosFeature=Pos(FeatureId,3);

y=abs(PosFeature-TargetPos);

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

end

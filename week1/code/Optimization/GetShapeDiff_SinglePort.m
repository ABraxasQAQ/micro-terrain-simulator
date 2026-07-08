function y = GetShapeDiff_SinglePort(x,PortId,PortNum,MaxVoltage,TargetPos,FeatureId)

Pos = GetShape_SinglePort(x,PortId,PortNum,MaxVoltage);

PosFeature=Pos(FeatureId,3);

y=abs(PosFeature-TargetPos);

OutFileName=strcat("ErrorNow.dat");  %%% Record the x-displacement in each trial
fidout=fopen(OutFileName,'a+');
fprintf(fidout,'%25.15f\r\n',y);
fclose(fidout);

OutFileName=strcat("VoltageNow.dat");  %%% Record the force applied in each trial
fidout=fopen(OutFileName,'a+');
for kk=1:1    
    fprintf(fidout,'%25.15f',x(kk));
end
fprintf(fidout,'\r\n');
fclose(fidout);
end


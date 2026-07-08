function y = GetShapeDiff_SinglePort_Dynamics(x,PortId,PortNum,TimeNum,TimePoint,...
                                              MaxVoltage,TargetPos,...
                                              InitialTime,FinalTime,RepeatNum)

y=0.0;
for oi=1:RepeatNum
    Pos = GetShape_SinglePort_Dynamics(x,PortId,PortNum,TimeNum,TimePoint,MaxVoltage);
    yStep=0.0;
    FrameNum=length(Pos(:,1));
    count=0;
    for ii=1:FrameNum
        TimeNow=Pos(ii,1);
        zNow=Pos(ii,2);
        if TimeNow>=InitialTime && TimeNow<=FinalTime
            count=count+1;
            yStep=yStep+abs(zNow-TargetPos);
        end
    end
    yStep=yStep/(count);
    y=y+yStep;
end
y=y/(RepeatNum);

OutFileName=strcat("ErrorNow.dat");  %%% Record the x-displacement in each trial
fidout=fopen(OutFileName,'a+');
fprintf(fidout,'%25.15f\r\n',y);
fclose(fidout);

OutFileName=strcat("VoltageNow.dat");  %%% Record the force applied in each trial
fidout=fopen(OutFileName,'a+');
for kk=1:TimeNum   
    fprintf(fidout,'%25.15f',x(kk));
end
fprintf(fidout,'\r\n');
fclose(fidout);
end


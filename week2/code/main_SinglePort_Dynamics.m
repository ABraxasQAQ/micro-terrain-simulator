clear all
clc
N=4;
PortNum=N*N;
TimeNum=3;
InitialFrame=20;
RepeatNum=3;
FinalFrame=100;
FrameRate=200.0;
TimePerFrame=1.0/FrameRate;

InitialTime=InitialFrame*TimePerFrame;
FinalTime=FinalFrame*TimePerFrame;
TimePoint=zeros(TimeNum,1);
for ii=1:TimeNum
    TimePoint(ii)=InitialTime/(TimeNum-1)*(ii-1);
end

ActivePortNum=1;
PortId=2;
FeaturePointId=6;
VoltageMax=0.61;
VoltageMaxR=0.6;
PosIni=-1.8166;
TargetPos=-1.5;
FontSize=16;
VariableNum=ActivePortNum*TimeNum;
MaxVoltage=VoltageMax;
x0=zeros(VariableNum,1);

x0(1)=0.44;
x0(2)=0.44;
x0(3)=0.44;

% x0(1)=0.167187500000000;
% x0(2)=0.292187500000000;
% x0(3)=0.440625000000000;
% Pos = GetShape_SinglePort_Dynamics(x0,PortId,PortNum,TimeNum,TimePoint,VoltageMax);
               

y = GetShapeDiff_SinglePort_Dynamics(x0,PortId,PortNum,TimeNum,TimePoint,...
                                              VoltageMax,TargetPos, ...
                                              InitialTime,FinalTime,RepeatNum);

% lb=zeros(VariableNum,1);
% ub=zeros(VariableNum,1);
% for ii=1:VariableNum
%     lb(ii)=-VoltageMaxR;
%     ub(ii)=VoltageMaxR;
% end
% ACon=[];
% bCon=[];
% myoptions = optimoptions(@patternsearch,'Display','iter','MaxFunEvals',200,'MaxIter',200);
% 
% %%% Gradient decent algorithm
% % x = fmincon(@GetShapeDiff,x0,[],[],[],[],lb,ub,[],myoptions);
% 
% %%% Pattern search algorithm
x = patternsearch(@(x) GetShapeDiff_SinglePort_Dynamics(x,PortId,PortNum,...
                 TimeNum,TimePoint,MaxVoltage,TargetPos,...
                 InitialTime,FinalTime,RepeatNum),...
                 x0,ACon,bCon,[],[],lb,ub,[],myoptions);





clear all
clc
N=4;
PortNum=N*N;
ActivePortNum=1;
PortId=2;
FeaturePointId=6;
VoltageMax=0.51;
TargetPos=-1.5;
x0=zeros(ActivePortNum,1);

lb=zeros(ActivePortNum,1);
ub=zeros(ActivePortNum,1);
for ii=1:ActivePortNum
    lb(ii)=-VoltageMax;
    ub(ii)=VoltageMax;
end
ACon=[];
bCon=[];

delete_if_exists("ErrorNow.dat");
delete_if_exists("VoltageNow.dat");

myoptions = optimoptions(@patternsearch,'Display','iter','MaxFunEvals',20,'MaxIter',20);

x = patternsearch(@(x) MT1_GetShapeDiff_SinglePort_wrapped(x,PortId,PortNum,VoltageMax,...
                 TargetPos,FeaturePointId),x0,ACon,bCon,[],[],lb,ub,[],myoptions);

fidout=fopen("SinglePortWrappedResult.dat",'w');
fprintf(fidout,'%25.15f',x);
fprintf(fidout,'\r\n');
fclose(fidout);

function delete_if_exists(filename)
    if exist(filename,'file')
        delete(filename);
    end
end

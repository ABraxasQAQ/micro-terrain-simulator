clear all
clc

N=4;
PortNum=N*N;

% Short first-pass test: optimize the four center-related ports only.
% Adjust ActivePortIds after confirming the physical port map.
ActivePortIds=[6 7 10 11];
ActivePortNum=length(ActivePortIds);

VoltageMax=0.51;
x0=zeros(ActivePortNum,1);

% Default target: center region higher than a flat baseline.
% Replace these values with a measured/desired 16x1 TargetZ before serious runs.
BaselineZ=0.0;
TargetZ=BaselineZ*ones(PortNum,1);
TargetZ([6 7 10 11])=0.5;
Weights=ones(PortNum,1);

lb=-VoltageMax*ones(ActivePortNum,1);
ub= VoltageMax*ones(ActivePortNum,1);
ACon=[];
bCon=[];

delete_if_exists("ErrorNow.dat");
delete_if_exists("VoltageNow.dat");
delete_if_exists("TargetTerrainResult.dat");

myoptions = optimoptions(@patternsearch,'Display','iter','MaxFunEvals',30,'MaxIter',30);

x = patternsearch(@(x) GetShapeDiff_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax,...
                 TargetZ,Weights),x0,ACon,bCon,[],[],lb,ub,[],myoptions);

fidout=fopen("TargetTerrainBestVoltage.dat",'w');
fprintf(fidout,'%25.15f',x);
fprintf(fidout,'\r\n');
fclose(fidout);

save("TargetZ.mat","TargetZ","Weights","ActivePortIds","x");

function delete_if_exists(filename)
    if exist(filename,'file')
        delete(filename);
    end
end

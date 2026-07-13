clear all
clc

ThisDir=fileparts(mfilename('fullpath'));
addpath(ThisDir);
cd(ThisDir);

% MT: MATLAB optimization stage.
% Edit this config block after reading the MT port spatial map.

TerrainName="center_bump_rim_down_strong";
TargetMode="center_bump_rim_down";

N=4;
PortNum=N*N;

% ActivePortIds should come from MT_outputs/port_spatial_map.
% Current center-bump candidate:
% center-up ports = 14/12/11/13
% rim-shaping ports = 9/16/10/7
ActivePortIds=[14 12 11 13 9 16 10 7];
x0=[0.25; 0.25; 0.15; 0.15; 0.08; 0.08; 0.06; 0.06];

CenterIds=[6 7 10 11];
XSmallIds=[1 2 3 4];
XLargeIds=[13 14 15 16];
YSmallIds=[1 5 9 13];
YLargeIds=[4 8 12 16];

TargetDelta=1.0;
RimDownDelta=0.5;
VoltageMax=2.05;
MaxTotalAbsVoltage=2.00;
UpperVoltage=0.80;

ActivePortNum=length(ActivePortIds);
if length(x0) ~= ActivePortNum
    error("x0 length must match ActivePortIds length");
end

lb=zeros(ActivePortNum,1);
ub=UpperVoltage*ones(ActivePortNum,1);
ACon=ones(1,ActivePortNum);
bCon=MaxTotalAbsVoltage;

% Measure this run's flat baseline.
BaselinePos = MT_GetShape_TargetTerrain(zeros(ActivePortNum,1),ActivePortIds,PortNum,VoltageMax);
BaselineZ = BaselinePos(:,3);

[TargetZ,Weights] = build_target(TargetMode,BaselineZ,TargetDelta,RimDownDelta, ...
    CenterIds,XSmallIds,XLargeIds,YSmallIds,YLargeIds);

delete_if_exists("ErrorNow.dat");
delete_if_exists("VoltageNow.dat");
delete_if_exists("TargetTerrainResult.dat");
delete_if_exists("TargetTerrainBestVoltage.dat");

myoptions = optimoptions(@patternsearch, ...
    'Display','iter', ...
    'MaxFunEvals',45, ...
    'MaxIter',45, ...
    'MeshTolerance',0.02);

x = patternsearch(@(x) MT_GetShapeDiff_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax, ...
                 TargetZ,Weights),x0,ACon,bCon,[],[],lb,ub,[],myoptions);

fidout=fopen("TargetTerrainBestVoltage.dat",'w');
fprintf(fidout,'%25.15f',x);
fprintf(fidout,'\r\n');
fclose(fidout);

RunDir = make_run_dir("MT_outputs",strcat(TerrainName,"_optimize"));
save(fullfile(RunDir,"MT_optimization.mat"), ...
    "TerrainName","TargetMode","TargetZ","Weights","ActivePortIds", ...
    "x","x0","BaselineZ","TargetDelta","RimDownDelta", ...
    "VoltageMax","MaxTotalAbsVoltage","UpperVoltage");

copy_if_exists("TargetTerrainBestVoltage.dat",RunDir);
copy_if_exists("ErrorNow.dat",RunDir);
copy_if_exists("VoltageNow.dat",RunDir);
copy_if_exists("TargetTerrainResult.dat",RunDir);
copy_if_exists("AveragePos.txt",RunDir);
copy_if_exists("measure_log.json",RunDir);
copy_if_exists("CurrentVoltage.dat",RunDir);

write_summary(RunDir,TerrainName,TargetMode,ActivePortIds,x,x0,TargetDelta,RimDownDelta, ...
    BaselineZ,TargetZ,Weights,VoltageMax,MaxTotalAbsVoltage,UpperVoltage);

fprintf('MT optimization outputs archived to: %s\n',RunDir);
fprintf('Save preset with:\n');
SaveScript=fullfile(ThisDir,"MT_save_preset.py");
fprintf('python "%s" %s --active-ports ',SaveScript,TerrainName);
fprintf('%d ',ActivePortIds);
fprintf('--voltage-file "%s"\n',fullfile(RunDir,"TargetTerrainBestVoltage.dat"));

function [TargetZ,Weights] = build_target(TargetMode,BaselineZ,TargetDelta,RimDownDelta, ...
    CenterIds,XSmallIds,XLargeIds,YSmallIds,YLargeIds)
    TargetZ=BaselineZ;
    Weights=0.5*ones(length(BaselineZ),1);

    if TargetMode=="center_bump"
        TargetZ(CenterIds)=BaselineZ(CenterIds)+TargetDelta;
        Weights(CenterIds)=3.0;
    elseif TargetMode=="center_bump_rim_down"
        RimIds=setdiff(1:length(BaselineZ),CenterIds);
        TargetZ(CenterIds)=BaselineZ(CenterIds)+TargetDelta;
        TargetZ(RimIds)=BaselineZ(RimIds)-RimDownDelta;
        Weights(CenterIds)=3.0;
        Weights(RimIds)=1.2;
    elseif TargetMode=="x_large_up"
        TargetZ(XLargeIds)=BaselineZ(XLargeIds)+TargetDelta;
        TargetZ(XSmallIds)=BaselineZ(XSmallIds)-TargetDelta;
        Weights(XLargeIds)=2.0;
        Weights(XSmallIds)=2.0;
    elseif TargetMode=="x_small_up"
        TargetZ(XSmallIds)=BaselineZ(XSmallIds)+TargetDelta;
        TargetZ(XLargeIds)=BaselineZ(XLargeIds)-TargetDelta;
        Weights(XSmallIds)=2.0;
        Weights(XLargeIds)=2.0;
    elseif TargetMode=="y_large_up"
        TargetZ(YLargeIds)=BaselineZ(YLargeIds)+TargetDelta;
        TargetZ(YSmallIds)=BaselineZ(YSmallIds)-TargetDelta;
        Weights(YLargeIds)=2.0;
        Weights(YSmallIds)=2.0;
    elseif TargetMode=="y_small_up"
        TargetZ(YSmallIds)=BaselineZ(YSmallIds)+TargetDelta;
        TargetZ(YLargeIds)=BaselineZ(YLargeIds)-TargetDelta;
        Weights(YSmallIds)=2.0;
        Weights(YLargeIds)=2.0;
    else
        error("Unknown TargetMode: %s",TargetMode);
    end
end

function delete_if_exists(filename)
    if exist(filename,'file')
        delete(filename);
    end
end

function run_dir = make_run_dir(root,label)
    if ~exist(root,'dir')
        mkdir(root);
    end
    stamp = datestr(now,'yyyymmdd_HHMMSS');
    run_dir = fullfile(root,strcat(stamp,"_",label));
    if ~exist(run_dir,'dir')
        mkdir(run_dir);
    end
end

function copy_if_exists(filename,run_dir)
    if exist(filename,'file')
        copyfile(filename,fullfile(run_dir,filename));
    end
end

function write_summary(RunDir,TerrainName,TargetMode,ActivePortIds,x,x0,TargetDelta,RimDownDelta, ...
    BaselineZ,TargetZ,Weights,VoltageMax,MaxTotalAbsVoltage,UpperVoltage)
    fidout=fopen(fullfile(RunDir,"MT_optimization_summary.txt"),'w');
fprintf(fidout,'terrain_name=%s\r\n',char(TerrainName));
fprintf(fidout,'target_mode=%s\r\n',char(TargetMode));
    fprintf(fidout,'active_ports=');
    fprintf(fidout,'%d ',ActivePortIds);
    fprintf(fidout,'\r\n');
    fprintf(fidout,'initial_active_voltage=');
    fprintf(fidout,'%25.15f ',x0);
    fprintf(fidout,'\r\n');
    fprintf(fidout,'best_active_voltage=');
    fprintf(fidout,'%25.15f ',x);
    fprintf(fidout,'\r\n');
    fprintf(fidout,'target_delta=%25.15f\r\n',TargetDelta);
    fprintf(fidout,'rim_down_delta=%25.15f\r\n',RimDownDelta);
    fprintf(fidout,'voltage_max=%25.15f\r\n',VoltageMax);
    fprintf(fidout,'max_total_abs_voltage=%25.15f\r\n',MaxTotalAbsVoltage);
    fprintf(fidout,'upper_voltage=%25.15f\r\n',UpperVoltage);
    fprintf(fidout,'baseline_z=');
    fprintf(fidout,'%25.15f ',BaselineZ);
    fprintf(fidout,'\r\n');
    fprintf(fidout,'target_z=');
    fprintf(fidout,'%25.15f ',TargetZ);
    fprintf(fidout,'\r\n');
    fprintf(fidout,'weights=');
    fprintf(fidout,'%25.15f ',Weights);
    fprintf(fidout,'\r\n');
    fclose(fidout);
end

clear all
clc

% MT5: MATLAB optimization stage.
% Edit this config block after reading the MT4 port mapping table.

TerrainName="center_bump_strong";
TargetMode="center_bump";

N=4;
PortNum=N*N;

% ActivePortIds should come from MT4_outputs/port_mapping.
% Current center_bump candidate from the latest table:
% ports 12/14 are stable center-up candidates; ports 11/13 add extra shape
% authority for a stronger cross-like bump.
ActivePortIds=[12 14 11 13];
x0=[0.15; 0.10; 0.15; 0.10];

CenterIds=[6 7 10 11];
XSmallIds=[1 2 3 4];
XLargeIds=[13 14 15 16];
YSmallIds=[1 5 9 13];
YLargeIds=[4 8 12 16];

TargetDelta=1.0;
VoltageMax=0.51;
MaxTotalAbsVoltage=0.50;
UpperVoltage=0.35;

ActivePortNum=length(ActivePortIds);
if length(x0) ~= ActivePortNum
    error("x0 length must match ActivePortIds length");
end

lb=zeros(ActivePortNum,1);
ub=UpperVoltage*ones(ActivePortNum,1);
ACon=ones(1,ActivePortNum);
bCon=MaxTotalAbsVoltage;

% Measure this run's flat baseline.
BaselinePos = MT1_GetShape_TargetTerrain(zeros(ActivePortNum,1),ActivePortIds,PortNum,VoltageMax);
BaselineZ = BaselinePos(:,3);

[TargetZ,Weights] = build_target(TargetMode,BaselineZ,TargetDelta, ...
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

x = patternsearch(@(x) MT1_GetShapeDiff_TargetTerrain(x,ActivePortIds,PortNum,VoltageMax, ...
                 TargetZ,Weights),x0,ACon,bCon,[],[],lb,ub,[],myoptions);

fidout=fopen("TargetTerrainBestVoltage.dat",'w');
fprintf(fidout,'%25.15f',x);
fprintf(fidout,'\r\n');
fclose(fidout);

RunDir = make_run_dir("MT5_outputs",strcat(TerrainName,"_optimize"));
save(fullfile(RunDir,"MT5_optimization.mat"), ...
    "TerrainName","TargetMode","TargetZ","Weights","ActivePortIds", ...
    "x","x0","BaselineZ","TargetDelta","VoltageMax","MaxTotalAbsVoltage","UpperVoltage");

copy_if_exists("TargetTerrainBestVoltage.dat",RunDir);
copy_if_exists("ErrorNow.dat",RunDir);
copy_if_exists("VoltageNow.dat",RunDir);
copy_if_exists("TargetTerrainResult.dat",RunDir);
copy_if_exists("AveragePos.txt",RunDir);
copy_if_exists("measure_log.json",RunDir);
copy_if_exists("CurrentVoltage.dat",RunDir);

write_summary(RunDir,TerrainName,TargetMode,ActivePortIds,x,x0,TargetDelta, ...
    BaselineZ,TargetZ,Weights,VoltageMax,MaxTotalAbsVoltage,UpperVoltage);

fprintf('MT5 optimization outputs archived to: %s\n',RunDir);
fprintf('Save preset with:\n');
fprintf('python MT5_save_optimized_preset.py %s --active-ports ',TerrainName);
fprintf('%d ',ActivePortIds);
fprintf('--voltage-file "%s"\n',fullfile(RunDir,"TargetTerrainBestVoltage.dat"));

function [TargetZ,Weights] = build_target(TargetMode,BaselineZ,TargetDelta, ...
    CenterIds,XSmallIds,XLargeIds,YSmallIds,YLargeIds)
    TargetZ=BaselineZ;
    Weights=0.5*ones(length(BaselineZ),1);

    if TargetMode=="center_bump"
        TargetZ(CenterIds)=BaselineZ(CenterIds)+TargetDelta;
        Weights(CenterIds)=3.0;
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

function write_summary(RunDir,TerrainName,TargetMode,ActivePortIds,x,x0,TargetDelta, ...
    BaselineZ,TargetZ,Weights,VoltageMax,MaxTotalAbsVoltage,UpperVoltage)
    fidout=fopen(fullfile(RunDir,"MT5_optimization_summary.txt"),'w');
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

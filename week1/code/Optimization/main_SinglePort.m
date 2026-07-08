clear all
clc
N=4;
PortNum=N*N;
ActivePortNum=1;
PortId=2;
FeaturePointId=6;
VoltageMax=0.51;
VoltageMaxR=0.5;
PosIni=-1.8166;
TargetPos=-1.5;
FontSize=16;

Diff = GetShapeDiff_SinglePort(x,PortId,PortNum,VoltageMax,TargetPos,FeatureId);

x0=zeros(ActivePortNum,1);
lb=zeros(ActivePortNum,1);
ub=zeros(ActivePortNum,1);
for ii=1:ActivePortNum
    lb(ii)=-VoltageMaxR;
    ub(ii)=VoltageMaxR;
end
ACon=[];
bCon=[];
myoptions = optimoptions(@patternsearch,'Display','iter','MaxFunEvals',200,'MaxIter',200);

%%% Gradient decent algorithm
% x = fmincon(@GetShapeDiff,x0,[],[],[],[],lb,ub,[],myoptions);

%%% Pattern search algorithm
x = patternsearch(@(x) GetShapeDiff_SinglePort(x,PortId,PortNum,VoltageMax,...
                 TargetPos,FeaturePointId),x0,ACon,bCon,[],[],lb,ub,[],myoptions);



% 
% 
% CaseNum=11;
% RepeatNum=5;
% PosZAll=zeros(CaseNum,RepeatNum);
% VoltageAll=zeros(CaseNum,1);
% for jj=1:RepeatNum
%     for ii=1:CaseNum
%         VoltageNow=(ii-1)*0.05;
%         x=zeros(ActivePortNum,1);
%         x(1)=VoltageNow;
%         Pos = GetShape_SinglePort(x,PortId,PortNum,VoltageMax);
% 
%         PosFeature=Pos(FeaturePointId,3);
%         VoltageAll(ii,1)=VoltageNow;
%         PosZAll(ii,jj)=PosFeature;
%     end
% 
% end
% PosZAve=zeros(CaseNum,1);
% PosZVar=zeros(CaseNum,1);
% 
% for ii=1:CaseNum
%     PosZAve(ii)=mean(PosZAll(ii,:));
%     PosZVar(ii)=sqrt(var(PosZAll(ii,:)));
% end
% 
% OutFileName=strcat('PosZ.dat');
% fidout=fopen(OutFileName,'w');
% for ii=1:CaseNum
%     fprintf(fidout,'%25.15f',VoltageAll(ii,1));
%     fprintf(fidout,'%25.15f %25.15f',PosZAve(ii),PosZVar(ii));
%     for jj=1:RepeatNum
%         fprintf(fidout,'%25.15f',PosZAll(ii,jj));
%     end
%     fprintf(fidout,'\r\n');    
% end
% fclose(fidout);
% 
% VoltageError=zeros(CaseNum,1);
% plot(VoltageAll,PosZAve,VoltageError,PosZVar)

%     set(gca,'FontSize',FontSize,'fontweight','bold','FontName','Arial',...
%         'InnerPosition',[0.18,0.25,0.75,0.50]);  
%     xlabel('Port voltges (V)','FontSize',FontSize,'fontweight','bold','FontName','Arial');
%     ylabel('Position (mm)','FontSize',FontSize,'fontweight','bold','FontName','Arial');
% %     title(strcat('Frequency=',num2str(Frequency(oj)),'Hz ,Mode',num2str(ii)),...
% %        'FontSize',FontSize,'fontweight','bold','FontName','Arial',...
% %         'units','normalized','Position',[0.5,1.25,0])
%     set(gca, 'LineWidth',1.5)
%     print(gcf,'-dpng',strcat('PosZ','.png'));    



function BreatheIn2
% tested in matlab 2012b

[filename, path]=uigetfile('*.csv'); 
BreatheInFN=[path, filename]
assignin('base','BreatheInFN',BreatheInFN)

%%
y=dlmread(BreatheInFN,',');
RR=y(:,1);
SpO2=y(:,2);
PR2=y(:,3);
Psignal=[y(:,5) diff(y(:,[4 6]),[],2)];
Ssignal=[y(:,8) diff(y(:,[7 9]),[],2)];
% ROS=
clear y

time=cumsum(RR);
RRsmooth=smooth(RR,100,'moving'); 
I=find(abs(RR-RRsmooth)>0.3);
RRcore=RR; RRcore(I)=RRsmooth(I); % cut outliers
RRsmooth=smooth(RRcore,60,'moving');

SpO2(SpO2<80)=80; % sometimes there are wrong measurements

%% report

% close all
[~,filename]=fileparts(BreatheInFN);
figure('name',char(filename));

Nplots = 5;

k=1;
subplot(1,Nplots,k); k=k+1;
plot(SpO2,time/60,'-','markersize',1);
grid on; axis tight; xlim([85 100]);
xlabel('SpO2 (%)'); ylabel ('Time (minutes)')

subplot(1,Nplots,k); k=k+1;
plot(PR2,time/60);
grid on; axis tight;  xlim([50 80]);
xlabel('PR/min');

subplot(1,Nplots,k); k=k+1;
plot(RR,time/60); grid on; axis tight
xlabel('RR (s)')
xlim([0.5 1.4])

subplot(1,Nplots,k); k=k+1;
plot(RRcore,time/60); grid on; 
hold on
plot(RRsmooth,time/60,'r');
xlabel('RRcore (s)'); axis tight;
xlim([0.5 1.2])

% subplot(1,Nplots,k); k=k+1;
% plot(Psignal,time/60); grid on; axis tight
% 
% subplot(1,Nplots,k); k=k+1;
% % plot(Ssignal,time/60); grid on;  axis tight

% x=(Ssignal(:,2)./Ssignal(:,1))./(Psignal(:,2)./Psignal(:,1));
% x=smooth(x,100,'moving');
% plot(x,time/60)
% grid on;  axis tight; %xlim([0 10])

LinkAllAxes(gcf,'y')

subplot(1,Nplots,k); k=k+1;
spectrogram(RRcore-mean(RRcore),100);
title('RRCore')
xlabel('Normalized freq.')

set(gcf,'color','w');

%% numeric

if exist('SpO2','var')
  disp('----- SpO2')
  Stats(SpO2);
end

if exist('PR2','var')
  disp('----- PR2')
  Stats(PR2(PR2<100));
end

%%
% keyboard
end

% ============================ helpers
function Stats(x)
Mean=mean(x);
Std=std(x);
Skew=skewness(x);
Kurt=kurtosis(x);
Mean_Std_Skew_Kurt=[Mean,Std,Skew,Kurt]
end

function LinkAllAxes(rootobj,what)
warning('off','MATLAB:linkaxes:RequireDataAxes')
linkaxes(findobj(rootobj,'-property','Box'),what)
warning('on','MATLAB:linkaxes:RequireDataAxes')
end

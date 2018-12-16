function BreatheIn

[filename, path]=uigetfile('*.csv'); BreatheInFN=[path, filename];

%%
y=dlmread(BreatheInFN,',');
RR=y(:,1);
SPO2=y(:,2);
PR2=y(:,3);
Psignal=[y(:,5) diff(y(:,[4 6]),[],2)];
Ssignal=[y(:,8) diff(y(:,[7 9]),[],2)];
clear y

time=cumsum(RR);
RRsmooth=smooth(RR,100,'moving'); 
I=find(abs(RR-RRsmooth)>0.3);
RRcore=RR; RRcore(I)=RRsmooth(I); % cut outliers
RRsmooth=smooth(RRcore,60,'moving');

%% report

% close all
figure('name',char(filename));
k=1;

subplot(1,7,k); k=k+1;
plot(SPO2,time/60,'-','markersize',1);
grid on; axis tight; xlim([90 100]);
xlabel('SpO2 (%)'); ylabel ('Time (minutes)')

subplot(1,7,k); k=k+1;
plot(PR2,time/60);
grid on; axis tight;  xlim([50 100]);
xlabel('PR/min');

subplot(1,7,k); k=k+1;
plot(RR,time/60); grid on; axis tight
xlabel('RR (s)')
xlim([0.5 1.4])

subplot(1,7,k); k=k+1;
plot(RRcore,time/60); grid on; 
hold on
plot(RRsmooth,time/60,'r');
xlabel('RRcore (s)'); axis tight;
xlim([0.5 1.2])

subplot(1,7,k); k=k+1;
plot(Psignal,time/60); grid on; axis tight

subplot(1,7,k); k=k+1;
plot(Ssignal,time/60); grid on;  axis tight

LinkAllAxes(gcf,'y')

subplot(1,7,k); k=k+1;
%   S=specgram(RRup-mean(RRup),100); % the interbeat times have a strong ciclic component!
%   imagesc(flipud(abs(S)));
%   caxis([0 2])
spectrogram(RRcore-mean(RRcore),100);
% [S,F,T,P]=spectrogram(RRcore-RRsmooth,100);
% imagesc(flipud(abs(S)'))
% caxis([0 max(abs(S(:)))/2])
title('RRCore')

%% numeric

if exist('SPO2','var')
  disp('----- SpO2')
  Stats(SPO2);
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

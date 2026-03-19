% plot_obd_data.m
% Script to import OBD-II CSV log files and generate plots.

% Find the Logs directory relative to this script
scriptDir = fileparts(mfilename('fullpath'));
logFolder = fullfile(scriptDir, '..', 'Logs');
files = dir(fullfile(logFolder, 'obd_log_*.csv'));

if isempty(files)
    error('No log files found in the %s directory.', logFolder);
end

% Sort files by date to get the newest one
[~, idx] = sort([files.datenum], 'descend');
latestFile = fullfile(files(idx(1)).folder, files(idx(1)).name);

fprintf('Loading data from: %s\n', latestFile);

% Read the CSV file as a table
data = readtable(latestFile);

% The logger exports "N/A" for unsupported/missing PIDs
% Convert 'N/A' strings to NaN manually for MATLAB version compatibility
for v = 1:length(data.Properties.VariableNames)
    varName = data.Properties.VariableNames{v};
    if strcmp(varName, 'Timestamp')
        continue;
    end
    
    colData = data.(varName);
    if iscell(colData)
        idx = strcmp(colData, 'N/A') | strcmp(colData, 'NA');
        colData(idx) = {'NaN'};
        data.(varName) = str2double(colData);
    elseif isstring(colData)
        idx = (colData == "N/A") | (colData == "NA");
        colData(idx) = "NaN";
        data.(varName) = double(colData);
    end
end

% Convert Timestamp string to datetime
if ismember('Timestamp', data.Properties.VariableNames)
    try
        data.Timestamp = datetime(data.Timestamp, 'InputFormat', 'yyyy-MM-dd HH:mm:ss.SSS');
    catch
        warning('Could not parse timestamps directly. Attempting fallback.');
    end
else
    % Create a dummy time vector if Timestamp is missing
    data.Timestamp = seconds(1:height(data))';
end

% Ensure columns exist, padding with NaN if they weren't logged
requiredVars = {'SPEED', 'RPM', 'ENGINE_LOAD'};
for i = 1:length(requiredVars)
    var = requiredVars{i};
    if ~ismember(var, data.Properties.VariableNames)
        warning('Variable %s not found in log file. Plots will show empty data.', var);
        data.(var) = NaN(height(data), 1);
    end
    
    % Ensure numeric formatting (in case strings snuck past 'N/A' filtering)
    if iscell(data.(var)) || isstring(data.(var))
        data.(var) = str2double(data.(var));
    end
end


%% Figure 1: Timeseries of Speed, RPM, Engine Load
figure('Name', 'Timeseries Overview', 'Position', [100, 100, 800, 900]);

% Axes for Speed
ax1 = subplot(3,1,1);
plot(data.Timestamp, data.SPEED, 'b-', 'LineWidth', 1.5);
title('Vehicle Speed');
ylabel('Speed (km/h)');
grid on;

% Axes for RPM
ax2 = subplot(3,1,2);
plot(data.Timestamp, data.RPM, 'r-', 'LineWidth', 1.5);
title('Engine RPM');
ylabel('RPM');
grid on;

% Axes for Engine Load
ax3 = subplot(3,1,3);
plot(data.Timestamp, data.ENGINE_LOAD, 'm-', 'LineWidth', 1.5);
title('Engine Load');
ylabel('Load (%)');
xlabel('Time');
grid on;

% Link x-axes for easy zooming synchronization
linkaxes([ax1, ax2, ax3], 'x');


%% Figure 2: Speed vs RPM
figure('Name', 'Speed vs RPM', 'Position', [950, 100, 600, 500]);
scatter(data.RPM, data.SPEED, 15, 'filled', 'MarkerFaceAlpha', 0.5);
title('Speed vs Engine RPM');
xlabel('Engine RPM');
ylabel('Speed (km/h)');
grid on;

% --- Identify and Plot Gear Ratios ---
% Filter valid data (speed > 10 km/h, RPM > 1000) to avoid idle and clutch slip noise
validGearIdx = data.SPEED > 10 & data.RPM > 1000 & ~isnan(data.SPEED) & ~isnan(data.RPM);
if any(validGearIdx)
    speedRpmRatio = data.SPEED(validGearIdx) ./ data.RPM(validGearIdx);
    
    % Use histogram to find peaks in the ratio
    edges = linspace(min(speedRpmRatio), max(speedRpmRatio), 100);
    [N_counts, edges] = histcounts(speedRpmRatio, edges);
    centers = (edges(1:end-1) + edges(2:end)) / 2;
    
    % Simple peak finding
    isPeak = [false, (N_counts(2:end-1) > N_counts(1:end-2)) & (N_counts(2:end-1) > N_counts(3:end)), false];
    
    % Keep only peaks with sufficient data points (e.g., > 2% of total valid points)
    minPointsPerGear = sum(validGearIdx) * 0.02;
    isPeak = isPeak & (N_counts > minPointsPerGear);
    
    peakIndices = find(isPeak);
    estimatedRatios = sort(centers(peakIndices));
    
    % Remove peaks that are too close to each other (e.g., within 10% ratio difference)
    if length(estimatedRatios) > 1
        keep = true(size(estimatedRatios));
        for g = 2:length(estimatedRatios)
            if (estimatedRatios(g) - estimatedRatios(g-1)) / estimatedRatios(g-1) < 0.1
                % Keep the one with higher count
                idx1 = find(centers == estimatedRatios(g-1));
                idx2 = find(centers == estimatedRatios(g));
                if N_counts(idx1) > N_counts(idx2)
                    keep(g) = false;
                else
                    keep(g-1) = false;
                end
            end
        end
        estimatedRatios = estimatedRatios(keep);
    end
    
    % Plot the identified lines
    hold on;
    allRPMs = [0, max(data.RPM, [], 'omitnan')];
    for g = 1:length(estimatedRatios)
        plot(allRPMs, allRPMs * estimatedRatios(g), 'r--', 'LineWidth', 1, 'DisplayName', sprintf('Gear %d', g));
        
        % Add text label at the end of the line
        y_end = allRPMs(2) * estimatedRatios(g);
        if y_end <= max(data.SPEED, [], 'omitnan') * 1.15
            text(allRPMs(2)*0.95, y_end, sprintf('Gear %d', g), ...
                'Color', 'red', 'VerticalAlignment', 'bottom', ...
                'HorizontalAlignment', 'right', 'FontWeight', 'bold');
        end
    end
    hold off;
end


%% Figure 3: 2D Histogram of Engine Load vs RPM
figure('Name', 'Engine Load vs RPM (2D Hist)', 'Position', [950, 650, 600, 500]);

% Remove NaN rows for histogram
validIdx = ~isnan(data.RPM) & ~isnan(data.ENGINE_LOAD);

if any(validIdx)
    if exist('histogram2', 'file')
        % Plot 2D histogram (MATLAB R2015b or later)
        histogram2(data.RPM(validIdx), data.ENGINE_LOAD(validIdx), ...
            [0:100:500*max(data.RPM/500)], [0:10:100],...
            'DisplayStyle', 'tile', 'ShowEmptyBins', 'on');
        colorbar;
        title('2D Histogram: Engine Load vs RPM');
        xlabel('Engine RPM');
        ylabel('Engine Load (%)');
    else
        % Fallback for older MATLAB versions
        warning('histogram2 function is not available. Falling back to scatter.');
        scatter(data.RPM(validIdx), data.ENGINE_LOAD(validIdx), 15, ...
            data.SPEED(validIdx), 'filled', 'MarkerFaceAlpha', 0.5);
        colorbar;
        title('Engine Load vs RPM (Colored by Speed)');
        xlabel('Engine RPM');
        ylabel('Engine Load (%)');
    end
else
    text(0.5, 0.5, 'Insufficient data to plot 2D Histogram (Missing RPM or ENGINE_LOAD)', ...
        'HorizontalAlignment', 'center', 'FontSize', 12, 'Units', 'normalized');
end

fprintf('Done plotting.\n');

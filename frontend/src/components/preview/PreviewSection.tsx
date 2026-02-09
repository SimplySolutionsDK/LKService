import React from 'react';
import { PreviewStats } from './PreviewStats';
import { PreviewTabs } from './PreviewTabs';
import { DailyTable } from './DailyTable';
import { WeeklyTable } from './WeeklyTable';
import { ExportBar } from './ExportBar';
import type { PreviewData, TabType, OutputFormat, CallOutSelections, AbsenceSelections, AbsenceType } from '../../types';
import './PreviewSection.css';

interface PreviewSectionProps {
  data: PreviewData;
  activeTab: TabType;
  outputFormat: OutputFormat;
  callOutSelections: CallOutSelections;
  absenceSelections: AbsenceSelections;
  onTabChange: (tab: TabType) => void;
  onFormatChange: (format: OutputFormat) => void;
  onCallOutChange: (date: string, checked: boolean) => void;
  onAbsenceChange: (date: string, absenceType: AbsenceType) => void;
  onShowDetails: (index: number) => void;
  onExport: () => void;
  onSubmitToDanlon?: () => void;
  danlonConnected?: boolean;
  isSubmittingToDanlon?: boolean;
}

export const PreviewSection: React.FC<PreviewSectionProps> = ({
  data,
  activeTab,
  outputFormat,
  callOutSelections,
  absenceSelections,
  onTabChange,
  onFormatChange,
  onCallOutChange,
  onAbsenceChange,
  onShowDetails,
  onExport,
  onSubmitToDanlon,
  danlonConnected = false,
  isSubmittingToDanlon = false,
}) => {
  return (
    <div className="preview-section active">
      <div className="preview-card">
        <div className="preview-header">
          <h3 className="preview-title">
            <span>📊</span>
            Data Forhåndsvisning
          </h3>
          <PreviewTabs activeTab={activeTab} onTabChange={onTabChange} />
        </div>

        <PreviewStats data={data} callOutSelections={callOutSelections} />

        {activeTab === 'daily' ? (
          <DailyTable
            data={data.daily}
            callOutSelections={callOutSelections}
            absenceSelections={absenceSelections}
            onCallOutChange={onCallOutChange}
            onAbsenceChange={onAbsenceChange}
            onShowDetails={onShowDetails}
          />
        ) : (
          <WeeklyTable data={data.weekly} />
        )}

        <ExportBar
          outputFormat={outputFormat}
          onFormatChange={onFormatChange}
          onExport={onExport}
        />

        {onSubmitToDanlon && (
          <div className="danlon-submit-section">
            <button
              className="danlon-submit-button"
              onClick={onSubmitToDanlon}
              disabled={!danlonConnected || isSubmittingToDanlon}
              title={!danlonConnected ? 'Tilslut til Danløn først' : 'Send til Danløn'}
            >
              {isSubmittingToDanlon ? (
                <>
                  <span className="spinner"></span>
                  Sender til Danløn...
                </>
              ) : (
                <>
                  📤 Send til Danløn
                </>
              )}
            </button>
            {!danlonConnected && (
              <p className="danlon-info-text">
                Du skal først tilslutte til Danløn for at kunne sende timeregistreringer.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

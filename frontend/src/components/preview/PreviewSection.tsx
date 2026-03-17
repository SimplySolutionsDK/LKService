import React from 'react';
import { PreviewStats } from './PreviewStats';
import { PreviewTabs } from './PreviewTabs';
import { DailyTable } from './DailyTable';
import { PeriodTable } from './PeriodTable';
import { ExportBar } from './ExportBar';
import type {
  PreviewData,
  TabType,
  OutputFormat,
  CallOutSelections,
  AbsenceSelections,
  AbsenceType,
  StatsOverrides,
} from '../../types';

interface PreviewSectionProps {
  data: PreviewData;
  activeTab: TabType;
  outputFormat: OutputFormat;
  callOutSelections: CallOutSelections;
  absenceSelections: AbsenceSelections;
  statsOverrides: StatsOverrides;
  onTabChange: (tab: TabType) => void;
  onFormatChange: (format: OutputFormat) => void;
  onCallOutChange: (date: string, checked: boolean) => void;
  onAbsenceChange: (date: string, absenceType: AbsenceType) => void;
  onStatsOverride: (field: keyof StatsOverrides, value: number) => void;
  onStatsReset: (field: keyof StatsOverrides) => void;
  onShowDetails: (index: number) => void;
  onHalfSickDayOpen: () => void;
  onExport: () => void;
  danlonCompanyId?: string;
}

export const PreviewSection: React.FC<PreviewSectionProps> = ({
  data,
  activeTab,
  outputFormat,
  callOutSelections,
  absenceSelections,
  statsOverrides,
  onTabChange,
  onFormatChange,
  onCallOutChange,
  onAbsenceChange,
  onStatsOverride,
  onStatsReset,
  onShowDetails,
  onHalfSickDayOpen,
  onExport,
  danlonCompanyId,
}) => {
  return (
    <div className="w-full mt-2 animate-fade-in">
      <div className="bg-bg-card border border-border rounded-2xl overflow-hidden">
        <div className="p-4 px-5 border-b border-border flex justify-between items-center flex-wrap gap-4 max-md:flex-col max-md:items-start">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span>📊</span>
              Data Forhåndsvisning
            </h3>
            <button
              className="flex items-center gap-1.5 py-1.5 px-3 rounded-lg text-[0.8rem] font-medium bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 hover:text-blue-300 transition-colors cursor-pointer"
              onClick={onHalfSickDayOpen}
              title="Tilføj halv sygedag til en dato"
            >
              🤒 Halv Sygedag
            </button>
          </div>
          <PreviewTabs activeTab={activeTab} onTabChange={onTabChange} />
        </div>

        <PreviewStats
          data={data}
          callOutSelections={callOutSelections}
          statsOverrides={statsOverrides}
          onStatsOverride={onStatsOverride}
          onStatsReset={onStatsReset}
        />

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
          <PeriodTable data={data.periods} />
        )}

        <ExportBar
          outputFormat={outputFormat}
          onFormatChange={onFormatChange}
          onExport={onExport}
          danlonCompanyId={danlonCompanyId}
          previewSessionId={data.session_id}
        />
      </div>
    </div>
  );
};

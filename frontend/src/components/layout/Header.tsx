import React, { useState } from 'react';
import { Select } from '../ui/Select';
import { DanlonConnection } from '../danlon/DanlonConnection';
import { DanlonSync } from '../danlon/DanlonSync';
import type { EmployeeType } from '../../types';

interface HeaderProps {
  employeeType: EmployeeType;
  onEmployeeTypeChange: (type: EmployeeType) => void;
  danlonCompanyId?: string;
  hasPreviewData?: boolean;
  onDanlonConnectionChange?: () => void;
}

const employeeTypeOptions = [
  { value: 'Svend', label: 'Svend (Faglært)' },
  { value: 'Lærling', label: 'Lærling' },
  { value: 'Funktionær', label: 'Funktionær' },
  { value: 'Elev', label: 'Elev (Handels/Kontor)' },
];

export const Header: React.FC<HeaderProps> = ({ 
  employeeType, 
  onEmployeeTypeChange,
  danlonCompanyId,
  hasPreviewData,
  onDanlonConnectionChange
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [settingsTab, setSettingsTab] = useState<'general' | 'danlon'>('general');

  const handleDanlonSync = () => {
    if (onDanlonConnectionChange) {
      onDanlonConnectionChange();
    }
  };

  return (
    <header className="text-center mb-10 relative max-md:mb-6">
      <div className="relative flex items-start justify-center mb-4 max-md:justify-between max-md:w-full">
        <div className="flex items-center justify-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-accent to-violet-500 rounded-xl flex items-center justify-center text-2xl shadow-[0_4px_20px_var(--color-accent-glow)] max-md:w-10 max-md:h-10 max-md:text-xl">
            ⏱
          </div>
          <h1 className="text-[1.75rem] font-bold tracking-tight max-md:text-2xl">
            Tidsregistrering Parser
          </h1>
        </div>

        <div className="absolute right-0 top-0 max-md:static max-md:ml-auto">
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className="w-11 h-11 bg-bg-card border border-border rounded-xl flex items-center justify-center text-xl transition-all hover:border-accent hover:bg-bg-secondary hover:rotate-45"
          >
            ⚙️
          </button>
          
          {showSettings && (
            <>
              <div 
                className="fixed inset-0 z-[90]" 
                onClick={() => setShowSettings(false)}
              />
              <div className="absolute right-0 top-[calc(100%+0.5rem)] bg-bg-card border border-border rounded-xl p-5 min-w-[600px] max-w-[800px] shadow-[0_8px_32px_rgba(0,0,0,0.3)] z-[100] max-md:fixed max-md:inset-4 max-md:top-auto max-md:bottom-4 max-md:min-w-0 max-md:max-w-none max-md:max-h-[80vh] max-md:overflow-y-auto">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-100">Indstillinger</h3>
                  <button
                    type="button"
                    onClick={() => setShowSettings(false)}
                    className="text-slate-400 hover:text-slate-100 text-xl"
                  >
                    ✕
                  </button>
                </div>

                <div className="flex gap-2 mb-4 border-b border-border pb-2">
                  <button
                    type="button"
                    onClick={() => setSettingsTab('general')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      settingsTab === 'general'
                        ? 'bg-accent text-white'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-bg-secondary'
                    }`}
                  >
                    ⚙️ Generelt
                  </button>
                  <button
                    type="button"
                    onClick={() => setSettingsTab('danlon')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      settingsTab === 'danlon'
                        ? 'bg-accent text-white'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-bg-secondary'
                    }`}
                  >
                    🔗 Danløn Integration
                  </button>
                </div>

                {settingsTab === 'general' ? (
                  <div>
                    <Select
                      label="Medarbejdertype"
                      value={employeeType}
                      onChange={(e) => onEmployeeTypeChange(e.target.value as EmployeeType)}
                      options={employeeTypeOptions}
                    />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <DanlonConnection />
                    {hasPreviewData && (
                      <DanlonSync
                        companyId={danlonCompanyId}
                        hasData={hasPreviewData}
                        onSyncComplete={handleDanlonSync}
                      />
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <p className="text-slate-400 text-[0.95rem] mt-2 max-md:text-[0.85rem]">
        Upload CSV-filer og få dem formateret med overtidsberegning
      </p>
    </header>
  );
};

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import type { OutputFormat } from '../../types';

interface SyncResult {
  success: boolean;
  message: string;
  summary?: { created: number; skipped: number; errors: number };
  skipped_items?: Array<{ worker?: string; date?: string; reason: string }>;
  errors?: Array<{ reason: string }>;
  unmatched_workers?: string[];
}

interface ExportBarProps {
  outputFormat: OutputFormat;
  onFormatChange: (format: OutputFormat) => void;
  onExport: () => void;
  danlonCompanyId?: string;
  previewSessionId?: string;
}

const formatOptions = [
  { value: 'daily', label: 'Daglig oversigt (standard)' },
  { value: 'detailed', label: 'Daglig oversigt (detaljeret DBR 2026)' },
  { value: 'weekly', label: 'Ugentlig opsummering' },
  { value: 'weekly_detailed', label: 'Ugentlig opsummering (detaljeret)' },
  { value: 'combined', label: 'Kombineret (begge)' },
];

export const ExportBar: React.FC<ExportBarProps> = ({
  outputFormat,
  onFormatChange,
  onExport,
  danlonCompanyId,
  previewSessionId,
}) => {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleDanlonSync = async () => {
    if (!danlonCompanyId || !previewSessionId) return;

    if (!confirm('Send bearbejdet data til Danløn? Dette opretter løndele for alle behandlede tidsregistreringer.')) {
      return;
    }

    try {
      setSyncing(true);
      setSyncResult(null);
      setShowDetails(false);

      const response = await fetch(
        `/danlon/sync/${previewSessionId}?company_id=${danlonCompanyId}`,
        { method: 'POST' },
      );

      const data = await response.json();

      if (!response.ok) {
        setSyncResult({ success: false, message: data.detail || `Server error (${response.status})` });
        return;
      }

      setSyncResult(data);
    } catch (err) {
      setSyncResult({ success: false, message: 'Fejl: ' + (err as Error).message });
    } finally {
      setSyncing(false);
    }
  };

  const showDanlon = !!danlonCompanyId && !!previewSessionId;

  return (
    <div className="border-t border-border">
      {/* Main action row */}
      <div className="p-4 px-5 flex justify-between items-center flex-wrap gap-4 max-md:flex-col max-md:items-stretch">
        <div className="flex items-center gap-3 flex-1 min-w-[250px] max-md:flex-col max-md:items-stretch">
          <label htmlFor="outputFormat" className="text-[0.85rem] text-slate-400 whitespace-nowrap">
            Eksport format:
          </label>
          <select
            id="outputFormat"
            className="flex-1 min-w-[200px] w-full py-2.5 px-3.5 bg-bg-secondary border border-border rounded-lg text-slate-100 font-sans text-[0.9rem] cursor-pointer transition-colors select-arrow hover:border-accent focus:border-accent focus:outline-none"
            value={outputFormat}
            onChange={(e) => onFormatChange(e.target.value as OutputFormat)}
          >
            {formatOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3 max-md:flex-col max-md:items-stretch">
          <Button
            variant="success"
            onClick={onExport}
            className="!w-auto py-2.5 px-6 whitespace-nowrap max-md:!w-full"
          >
            <span>📥</span>
            Download CSV
          </Button>

          {showDanlon && (
            <Button
              variant="primary"
              onClick={handleDanlonSync}
              disabled={syncing}
              className="!w-auto py-2.5 px-6 whitespace-nowrap max-md:!w-full"
            >
              {syncing ? (
                <>
                  <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  <span>Sender...</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Send til Danløn</span>
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Sync result area */}
      {syncResult && (
        <div className="px-5 pb-4 space-y-2">
          {syncResult.success ? (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 flex items-start gap-3">
              <span className="text-lg leading-none mt-0.5">✓</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-green-400">{syncResult.message}</p>
                {syncResult.summary && (
                  <div className="flex gap-4 mt-1 text-xs text-slate-400">
                    <span className="text-green-400 font-medium">{syncResult.summary.created} oprettet</span>
                    {syncResult.summary.skipped > 0 && (
                      <span className="text-yellow-400">{syncResult.summary.skipped} sprunget over</span>
                    )}
                    {syncResult.summary.errors > 0 && (
                      <span className="text-red-400">{syncResult.summary.errors} fejl</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-3">
              <span className="text-lg leading-none mt-0.5">✗</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-red-400">Synkronisering mislykkedes</p>
                <p className="text-xs text-slate-300 mt-0.5">{syncResult.message}</p>
              </div>
            </div>
          )}

          {syncResult.unmatched_workers && syncResult.unmatched_workers.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-xs">
              <p className="font-medium text-yellow-400 mb-1">
                Medarbejdere uden match i Danløn:
              </p>
              <p className="text-slate-400">
                {syncResult.unmatched_workers.join(', ')}
              </p>
              <p className="text-slate-500 mt-1">
                Kontroller at navne i tidsregistreringen stemmer overens med navne i Danløn.
              </p>
            </div>
          )}

          {((syncResult.skipped_items && syncResult.skipped_items.length > 0) ||
            (syncResult.errors && syncResult.errors.length > 0)) && (
            <div>
              <button
                type="button"
                className="text-xs text-accent hover:text-accent-light underline"
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? '▼ Skjul detaljer' : '▶ Vis detaljer'}
              </button>
              {showDetails && (
                <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                  {syncResult.skipped_items?.map((item, i) => (
                    <div key={i} className="bg-bg-secondary rounded p-2 text-xs">
                      <span className="text-yellow-400">{item.reason}</span>
                      {(item.worker || item.date) && (
                        <span className="text-slate-500 ml-2">
                          {[item.worker, item.date].filter(Boolean).join(' · ')}
                        </span>
                      )}
                    </div>
                  ))}
                  {syncResult.errors?.map((error, i) => (
                    <div key={i} className="bg-bg-secondary rounded p-2 text-xs text-red-400">
                      {error.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

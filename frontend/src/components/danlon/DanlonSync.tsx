import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';

interface SyncResult {
  success: boolean;
  message: string;
  summary?: {
    created: number;
    skipped: number;
    errors: number;
  };
  skipped_items?: Array<{ reason: string; data: any }>;
  errors?: Array<{ reason: string }>;
}

interface DanlonSyncProps {
  companyId?: string;
  hasData: boolean;
  onSyncComplete?: () => void;
}

export function DanlonSync({ companyId, hasData, onSyncComplete }: DanlonSyncProps) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleSync = async () => {
    if (!companyId) {
      setResult({
        success: false,
        message: 'Please connect to Danløn first',
      });
      return;
    }

    if (!confirm('Sync current data to Danløn? This will create payparts for all processed time registrations.')) {
      return;
    }

    try {
      setSyncing(true);
      setResult(null);

      const response = await fetch(`/danlon/example/sync-payparts?company_id=${companyId}`, {
        method: 'POST',
      });

      const data = await response.json();
      setResult(data);

      if (data.success && onSyncComplete) {
        onSyncComplete();
      }
    } catch (err) {
      setResult({
        success: false,
        message: 'Failed to sync to Danløn: ' + (err as Error).message,
      });
      console.error(err);
    } finally {
      setSyncing(false);
    }
  };

  if (!hasData) {
    return null;
  }

  return (
    <Card>
      <div className="space-y-4">
        <div>
          <h3 className="text-[1.1rem] font-semibold mb-2 flex items-center gap-2">
            <span>📤</span>
            Sync to Danløn
          </h3>
          <p className="text-[0.85rem] text-slate-400">
            Push processed time registrations to Danløn as payparts
          </p>
        </div>

        {!companyId ? (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <p className="font-medium text-yellow-400 mb-1">Not Connected</p>
                <p className="text-sm text-slate-400">
                  Connect to Danløn first to enable sync
                </p>
              </div>
            </div>
          </div>
        ) : (
          <>
            <Button
              variant="primary"
              onClick={handleSync}
              disabled={syncing || !hasData}
            >
              {syncing ? (
                <>
                  <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Sync to Danløn</span>
                </>
              )}
            </Button>

            {result && (
              <div className="space-y-3">
                {result.success ? (
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">✓</span>
                      <div className="flex-1">
                        <p className="font-medium text-green-400 mb-2">{result.message}</p>
                        {result.summary && (
                          <div className="grid grid-cols-3 gap-3 text-sm">
                            <div className="bg-bg-card rounded p-2">
                              <p className="text-slate-400 text-xs mb-1">Created</p>
                              <p className="text-lg font-semibold text-green-400">
                                {result.summary.created}
                              </p>
                            </div>
                            {result.summary.skipped > 0 && (
                              <div className="bg-bg-card rounded p-2">
                                <p className="text-slate-400 text-xs mb-1">Skipped</p>
                                <p className="text-lg font-semibold text-yellow-400">
                                  {result.summary.skipped}
                                </p>
                              </div>
                            )}
                            {result.summary.errors > 0 && (
                              <div className="bg-bg-card rounded p-2">
                                <p className="text-slate-400 text-xs mb-1">Errors</p>
                                <p className="text-lg font-semibold text-red-400">
                                  {result.summary.errors}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">✗</span>
                      <div className="flex-1">
                        <p className="font-medium text-red-400 mb-1">Sync Failed</p>
                        <p className="text-sm text-slate-300">{result.message}</p>
                      </div>
                    </div>
                  </div>
                )}

                {(result.skipped_items && result.skipped_items.length > 0) || 
                 (result.errors && result.errors.length > 0) ? (
                  <div>
                    <button
                      type="button"
                      className="text-sm text-accent hover:text-accent-light underline"
                      onClick={() => setShowDetails(!showDetails)}
                    >
                      {showDetails ? '▼ Hide Details' : '▶ Show Details'}
                    </button>

                    {showDetails && (
                      <div className="mt-3 space-y-2 max-h-60 overflow-y-auto">
                        {result.skipped_items?.map((item, i) => (
                          <div key={i} className="bg-bg-secondary rounded p-3 text-xs">
                            <p className="text-yellow-400 font-medium mb-1">
                              Skipped: {item.reason}
                            </p>
                            <pre className="text-slate-500 overflow-x-auto">
                              {JSON.stringify(item.data, null, 2)}
                            </pre>
                          </div>
                        ))}
                        {result.errors?.map((error, i) => (
                          <div key={i} className="bg-bg-secondary rounded p-3 text-xs">
                            <p className="text-red-400 font-medium">
                              Error: {error.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </>
        )}

        <div className="text-xs text-slate-500 bg-bg-secondary rounded-lg p-3">
          <p className="font-medium mb-1">ℹ️ About Syncing:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Syncs all processed time registrations to Danløn</li>
            <li>Creates payparts for matched employees</li>
            <li>Skips entries with missing employee or pay code info</li>
            <li>Shows detailed results after sync</li>
          </ul>
        </div>
      </div>
    </Card>
  );
}

import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

interface SyncResult {
  success: boolean;
  message: string;
  summary?: {
    created: number;
    skipped: number;
    errors: number;
  };
  skipped_items?: Array<{ worker?: string; date?: string; reason: string }>;
  errors?: Array<{ reason: string }>;
  unmatched_workers?: string[];
}

interface DanlonSyncProps {
  companyId?: string;
  sessionId?: string;
  hasData: boolean;
  onSyncComplete?: () => void;
}

export function DanlonSync({ companyId, sessionId, hasData, onSyncComplete }: DanlonSyncProps) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleSync = async () => {
    if (!companyId) {
      setResult({ success: false, message: 'Please connect to Danløn first' });
      return;
    }

    if (!sessionId) {
      setResult({ success: false, message: 'No processed data found. Please process your time registrations first.' });
      return;
    }

    if (!confirm('Send bearbejdet data til Danløn? Dette opretter løndele for alle behandlede tidsregistreringer.')) {
      return;
    }

    try {
      setSyncing(true);
      setResult(null);

      const response = await fetch(`/danlon/sync/${sessionId}?company_id=${companyId}`, {
        method: 'POST',
      });

      const data = await response.json();

      if (!response.ok) {
        setResult({
          success: false,
          message: data.detail || `Server error (${response.status})`,
        });
        return;
      }

      setResult(data);

      if (data.success && onSyncComplete) {
        onSyncComplete();
      }
    } catch (err) {
      setResult({
        success: false,
        message: 'Fejl ved synkronisering til Danløn: ' + (err as Error).message,
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
            Send til Danløn
          </h3>
          <p className="text-[0.85rem] text-slate-400">
            Opret løndele i Danløn fra de behandlede tidsregistreringer
          </p>
        </div>

        {!companyId ? (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <p className="font-medium text-yellow-400 mb-1">Ikke forbundet</p>
                <p className="text-sm text-slate-400">
                  Forbind til Danløn for at aktivere synkronisering
                </p>
              </div>
            </div>
          </div>
        ) : !sessionId ? (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <p className="font-medium text-yellow-400 mb-1">Ingen data</p>
                <p className="text-sm text-slate-400">
                  Behandl dine tidsregistreringer for at aktivere synkronisering
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
                  <span>Sender...</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Send til Danløn</span>
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
                              <p className="text-slate-400 text-xs mb-1">Oprettet</p>
                              <p className="text-lg font-semibold text-green-400">
                                {result.summary.created}
                              </p>
                            </div>
                            {result.summary.skipped > 0 && (
                              <div className="bg-bg-card rounded p-2">
                                <p className="text-slate-400 text-xs mb-1">Sprunget over</p>
                                <p className="text-lg font-semibold text-yellow-400">
                                  {result.summary.skipped}
                                </p>
                              </div>
                            )}
                            {result.summary.errors > 0 && (
                              <div className="bg-bg-card rounded p-2">
                                <p className="text-slate-400 text-xs mb-1">Fejl</p>
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
                        <p className="font-medium text-red-400 mb-1">Synkronisering mislykkedes</p>
                        <p className="text-sm text-slate-300">{result.message}</p>
                      </div>
                    </div>
                  </div>
                )}

                {result.unmatched_workers && result.unmatched_workers.length > 0 && (
                  <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                    <p className="text-xs font-medium text-yellow-400 mb-1">
                      Medarbejdere uden match i Danløn:
                    </p>
                    <ul className="text-xs text-slate-400 list-disc list-inside space-y-0.5">
                      {result.unmatched_workers.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                    <p className="text-xs text-slate-500 mt-1">
                      Kontroller at medarbejdernavne i Danløn stemmer overens med navne i tidsregistreringen.
                    </p>
                  </div>
                )}

                {((result.skipped_items && result.skipped_items.length > 0) ||
                  (result.errors && result.errors.length > 0)) && (
                  <div>
                    <button
                      type="button"
                      className="text-sm text-accent hover:text-accent-light underline"
                      onClick={() => setShowDetails(!showDetails)}
                    >
                      {showDetails ? '▼ Skjul detaljer' : '▶ Vis detaljer'}
                    </button>

                    {showDetails && (
                      <div className="mt-3 space-y-2 max-h-60 overflow-y-auto">
                        {result.skipped_items?.map((item, i) => (
                          <div key={i} className="bg-bg-secondary rounded p-3 text-xs">
                            <p className="text-yellow-400 font-medium mb-1">
                              Sprunget over: {item.reason}
                            </p>
                            {(item.worker || item.date) && (
                              <p className="text-slate-500">
                                {item.worker && <span>Medarbejder: {item.worker}</span>}
                                {item.worker && item.date && ' — '}
                                {item.date && <span>Dato: {item.date}</span>}
                              </p>
                            )}
                          </div>
                        ))}
                        {result.errors?.map((error, i) => (
                          <div key={i} className="bg-bg-secondary rounded p-3 text-xs">
                            <p className="text-red-400 font-medium">Fejl: {error.reason}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        <div className="text-xs text-slate-500 bg-bg-secondary rounded-lg p-3">
          <p className="font-medium mb-1">ℹ️ Om synkronisering:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Opretter løndele for normaltimer, overtid og udkald</li>
            <li>Matcher medarbejdere på fuldt navn mod Danløn</li>
            <li>Springer poster over uden match eller timer</li>
            <li>Viser detaljerede resultater efter afsendelse</li>
          </ul>
        </div>
      </div>
    </Card>
  );
}

import { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';

const CACHE_KEY = 'danlon_connection_status';

interface ConnectionStatus {
  connected: boolean;
  user_id?: string;
  company_id?: string;
  company_name?: string;
  expires_at?: string;
}

interface PendingSession {
  pending: boolean;
  session_id?: string;
  select_company_url?: string;
  expires_at?: string;
}

type ManualMode = 'code' | 'tokens';

function loadCachedStatus(): ConnectionStatus | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as ConnectionStatus) : null;
  } catch {
    return null;
  }
}

function saveStatusToCache(status: ConnectionStatus) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(status));
  } catch {
    // ignore storage errors
  }
}

export function DanlonConnection() {
  const [status, setStatus] = useState<ConnectionStatus>(
    () => loadCachedStatus() ?? { connected: false }
  );
  const [loading, setLoading] = useState(true);
  const [justConnected, setJustConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pending / manual-complete state
  const [pendingSession, setPendingSession] = useState<PendingSession | null>(null);
  const [showManual, setShowManual] = useState(false);
  const [manualMode, setManualMode] = useState<ManualMode>('code');
  const [manualCode, setManualCode] = useState('');
  const [manualAccessToken, setManualAccessToken] = useState('');
  const [manualRefreshToken, setManualRefreshToken] = useState('');
  const [manualCompanyId, setManualCompanyId] = useState('');
  const [manualCompanyName, setManualCompanyName] = useState('');
  const [completing, setCompleting] = useState(false);

  const checkConnection = async () => {
    try {
      setLoading(true);
      const response = await fetch('/danlon/status');
      const data: ConnectionStatus = await response.json();
      setStatus(data);
      saveStatusToCache(data);
      setError(null);
      if (data.connected) {
        setPendingSession(null);
        setShowManual(false);
      }
    } catch (err) {
      setError('Failed to check connection status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const checkPending = async () => {
    try {
      const response = await fetch('/danlon/pending');
      const data: PendingSession = await response.json();
      if (data.pending) {
        setPendingSession(data);
      }
    } catch {
      // non-critical
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('danlon_connected') === 'true') {
      setJustConnected(true);
      window.history.replaceState({}, '', window.location.pathname);
    }

    checkConnection().then(() => {
      // Only look for a pending session if not connected
      setStatus(prev => {
        if (!prev.connected) checkPending();
        return prev;
      });
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleConnect = () => {
    window.location.href = '/danlon/connect';
  };

  const handleOpenSelectCompany = () => {
    if (pendingSession?.select_company_url) {
      window.open(pendingSession.select_company_url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleManualComplete = async () => {
    setCompleting(true);
    setError(null);
    try {
      let body: Record<string, string>;
      if (manualMode === 'code') {
        if (!manualCode.trim()) {
          setError('Please enter the code from the redirect URL.');
          return;
        }
        body = { code: manualCode.trim() };
      } else {
        if (!manualAccessToken.trim() || !manualRefreshToken.trim()) {
          setError('Access token and refresh token are required.');
          return;
        }
        body = {
          access_token: manualAccessToken.trim(),
          refresh_token: manualRefreshToken.trim(),
          company_id: manualCompanyId.trim(),
          company_name: manualCompanyName.trim(),
        };
      }

      const response = await fetch('/danlon/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        setJustConnected(true);
        setShowManual(false);
        setPendingSession(null);
        await checkConnection();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to complete connection.');
      }
    } catch (err) {
      setError('An unexpected error occurred.');
      console.error(err);
    } finally {
      setCompleting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect from Danløn?')) return;

    try {
      setLoading(true);
      const response = await fetch('/danlon/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_id: status.company_id }),
      });

      if (response.ok) {
        await checkConnection();
        setError(null);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to disconnect');
      }
    } catch (err) {
      setError('Failed to disconnect from Danløn');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-[1.3rem] font-semibold mb-2 flex items-center gap-2">
            <span>🔐</span>
            Danløn Integration
          </h2>
          <p className="text-[0.85rem] text-slate-400">
            Connect to Danløn to sync time registrations automatically
          </p>
        </div>
      </div>

      {justConnected && (
        <div className="mb-4">
          <Status type="success" message="Successfully connected to Danløn!" />
        </div>
      )}

      {error && (
        <div className="mb-4">
          <Status type="error" message={error} />
        </div>
      )}

      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
            <p className="mt-2 text-slate-400 text-sm">Checking connection...</p>
          </div>
        ) : status.connected ? (
          <div className="space-y-4">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">✓</span>
                <div className="flex-1">
                  <p className="font-medium text-green-400 mb-1">Connected to Danløn</p>
                  {status.company_name && (
                    <p className="text-sm text-slate-300 mb-1">Company: {status.company_name}</p>
                  )}
                  <p className="text-xs text-slate-400">Company ID: {status.company_id}</p>
                  {status.expires_at && (
                    <p className="text-xs text-slate-500 mt-2">
                      Token expires: {new Date(status.expires_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="secondary" onClick={checkConnection} disabled={loading}>
                🔄 Refresh Status
              </Button>
              <Button variant="secondary" onClick={handleDisconnect} disabled={loading}>
                🔌 Disconnect
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">ℹ️</span>
                <div className="flex-1">
                  <p className="font-medium text-blue-400 mb-1">Not Connected</p>
                  <p className="text-sm text-slate-400">
                    Connect to Danløn to enable automatic time registration sync
                  </p>
                </div>
              </div>
            </div>

            <div className="flex gap-2 flex-wrap">
              <Button variant="primary" onClick={handleConnect} disabled={loading}>
                <span>🔗</span>
                Connect to Danløn
              </Button>

              {pendingSession?.pending && (
                <Button variant="secondary" onClick={handleOpenSelectCompany}>
                  🏢 Open company selection
                </Button>
              )}
            </div>

            {/* Manual completion panel — shown when the OAuth redirect didn't land */}
            {pendingSession?.pending && (
              <div className="border border-yellow-500/30 bg-yellow-500/5 rounded-lg p-4 space-y-3">
                <p className="text-sm font-medium text-yellow-400">
                  OAuth flow started — complete connection manually
                </p>
                <p className="text-xs text-slate-400">
                  If the automatic redirect from Danløn did not come back, click
                  "Open company selection" above, select your company, then use
                  one of the options below to finish.
                </p>

                <button
                  className="text-xs text-accent underline"
                  onClick={() => setShowManual(v => !v)}
                >
                  {showManual ? 'Hide manual entry' : 'Show manual entry options'}
                </button>

                {showManual && (
                  <div className="space-y-3 pt-2">
                    {/* Mode toggle */}
                    <div className="flex gap-2 text-xs">
                      <button
                        className={`px-3 py-1 rounded ${manualMode === 'code' ? 'bg-accent text-white' : 'bg-bg-secondary text-slate-400'}`}
                        onClick={() => setManualMode('code')}
                      >
                        Enter redirect code
                      </button>
                      <button
                        className={`px-3 py-1 rounded ${manualMode === 'tokens' ? 'bg-accent text-white' : 'bg-bg-secondary text-slate-400'}`}
                        onClick={() => setManualMode('tokens')}
                      >
                        Enter tokens directly
                      </button>
                    </div>

                    {manualMode === 'code' ? (
                      <div className="space-y-2">
                        <p className="text-xs text-slate-400">
                          If Danløn redirected to a URL like{' '}
                          <code className="text-slate-300">
                            http://localhost:8000/danlon/success?code=…
                          </code>{' '}
                          paste the <strong>code</strong> value here.
                        </p>
                        <input
                          type="text"
                          placeholder="code value from redirect URL"
                          value={manualCode}
                          onChange={e => setManualCode(e.target.value)}
                          className="w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                        />
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-xs text-slate-400">
                          Enter the access token, refresh token and company ID
                          from your Danløn demo credentials.
                        </p>
                        <input
                          type="text"
                          placeholder="Access token"
                          value={manualAccessToken}
                          onChange={e => setManualAccessToken(e.target.value)}
                          className="w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                        />
                        <input
                          type="text"
                          placeholder="Refresh token"
                          value={manualRefreshToken}
                          onChange={e => setManualRefreshToken(e.target.value)}
                          className="w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                        />
                        <input
                          type="text"
                          placeholder="Company ID"
                          value={manualCompanyId}
                          onChange={e => setManualCompanyId(e.target.value)}
                          className="w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                        />
                        <input
                          type="text"
                          placeholder="Company name (optional)"
                          value={manualCompanyName}
                          onChange={e => setManualCompanyName(e.target.value)}
                          className="w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                        />
                      </div>
                    )}

                    <Button
                      variant="primary"
                      onClick={handleManualComplete}
                      disabled={completing}
                    >
                      {completing ? 'Saving…' : '✓ Complete connection'}
                    </Button>
                  </div>
                )}
              </div>
            )}

            <div className="text-xs text-slate-500 bg-bg-secondary rounded-lg p-3">
              <p className="font-medium mb-1">What happens when you connect:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>You'll be redirected to Danløn's secure login</li>
                <li>After logging in, select your company</li>
                <li>Tokens will be stored securely</li>
                <li>You can then sync time registrations automatically</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

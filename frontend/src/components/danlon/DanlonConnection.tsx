import { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';

interface ConnectionStatus {
  connected: boolean;
  user_id?: string;
  company_id?: string;
  company_name?: string;
  expires_at?: string;
}

export function DanlonConnection() {
  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkConnection = async () => {
    try {
      setLoading(true);
      const response = await fetch('/danlon/status');
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to check connection status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  const handleConnect = () => {
    window.location.href = '/danlon/connect';
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect from Danløn?')) {
      return;
    }

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

      {error && (
        <div className="mb-4">
          <Status type="error" message={error} />
        </div>
      )}

      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
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
                    <p className="text-sm text-slate-300 mb-1">
                      Company: {status.company_name}
                    </p>
                  )}
                  <p className="text-xs text-slate-400">
                    Company ID: {status.company_id}
                  </p>
                  {status.expires_at && (
                    <p className="text-xs text-slate-500 mt-2">
                      Token expires: {new Date(status.expires_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={checkConnection}
                disabled={loading}
              >
                🔄 Refresh Status
              </Button>
              <Button
                variant="secondary"
                onClick={handleDisconnect}
                disabled={loading}
              >
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

            <Button
              variant="primary"
              onClick={handleConnect}
              disabled={loading}
            >
              <span>🔗</span>
              Connect to Danløn
            </Button>

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

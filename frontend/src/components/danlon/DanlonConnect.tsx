import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { DanlonConnectionStatus } from '../../types';
import './DanlonConnect.css';

export const DanlonConnect = () => {
  const [status, setStatus] = useState<DanlonConnectionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const statusData = await api.getDanlonStatus();
      setStatus(statusData);
      setError(null);
    } catch (err) {
      console.error('Failed to load Danlon status:', err);
      setError(err instanceof Error ? err.message : 'Failed to load status');
    }
  };

  const handleConnect = () => {
    // Redirect to Danlon connect endpoint
    window.location.href = '/danlon/connect';
  };

  const handleDisconnect = async () => {
    if (!confirm('Er du sikker på, at du vil afbryde forbindelsen til Danløn?')) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await api.disconnectDanlon();
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect');
    } finally {
      setIsLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="danlon-connect-card">
        <h3>Danløn Integration</h3>
        <p>Indlæser...</p>
      </div>
    );
  }

  return (
    <div className="danlon-connect-card">
      <h3>Danløn Integration</h3>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {status.connected ? (
        <div className="connected-status">
          <div className="status-indicator connected">
            <span className="status-dot"></span>
            Tilsluttet
          </div>
          
          {status.company_id && (
            <p className="company-info">
              Virksomhed: {status.company_id}
            </p>
          )}
          
          {status.connected_at && (
            <p className="connection-time">
              Tilsluttet: {new Date(status.connected_at).toLocaleString('da-DK')}
            </p>
          )}

          <button
            className="disconnect-button"
            onClick={handleDisconnect}
            disabled={isLoading}
          >
            {isLoading ? 'Afbryder...' : 'Afbryd forbindelse'}
          </button>
        </div>
      ) : (
        <div className="disconnected-status">
          <div className="status-indicator disconnected">
            <span className="status-dot"></span>
            Ikke tilsluttet
          </div>
          
          <p className="info-text">
            Tilslut til Danløn for at kunne sende timeregistreringer direkte.
          </p>

          <button
            className="connect-button"
            onClick={handleConnect}
            disabled={isLoading}
          >
            Tilslut til Danløn
          </button>
        </div>
      )}
    </div>
  );
};

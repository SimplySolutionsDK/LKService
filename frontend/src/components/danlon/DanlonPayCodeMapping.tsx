import { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';

interface PayPartMeta {
  code: string;
  description: string;
  unitsAllowed: boolean;
  rateAllowed: boolean;
  amountAllowed: boolean;
}

interface Mapping {
  normal_code: string;
  overtime_code: string;
  callout_code: string;
  is_default?: boolean;
}

interface DanlonPayCodeMappingProps {
  connected: boolean;
}

export function DanlonPayCodeMapping({ connected }: DanlonPayCodeMappingProps) {
  const [meta, setMeta] = useState<PayPartMeta[]>([]);
  const [mapping, setMapping] = useState<Mapping>({
    normal_code: 'T1',
    overtime_code: 'T2',
    callout_code: 'T3',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  const loadData = async () => {
    if (!connected) return;
    setLoading(true);
    setError(null);
    try {
      const [metaRes, mappingRes] = await Promise.all([
        fetch('/danlon/payparts-meta'),
        fetch('/danlon/paycode-mapping'),
      ]);
      const metaData = await metaRes.json();
      const mappingData = await mappingRes.json();

      setMeta(metaData.pay_parts_meta ?? []);
      setIsDemo(metaData.source === 'demo_fallback');
      setMapping({
        normal_code: mappingData.normal_code,
        overtime_code: mappingData.overtime_code,
        callout_code: mappingData.callout_code,
      });
    } catch (err) {
      setError('Failed to load pay code configuration.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [connected]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const response = await fetch('/danlon/paycode-mapping', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mapping),
      });
      if (response.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to save mapping.');
      }
    } catch (err) {
      setError('Failed to save mapping.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (!connected) return null;

  const codeLabel = (code: string) => {
    const found = meta.find(m => m.code === code);
    return found ? `${found.code} – ${found.description}` : code;
  };

  const selectClass =
    'w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200';

  const rows: { label: string; description: string; field: keyof Omit<Mapping, 'is_default'> }[] = [
    {
      label: 'Normal hours',
      description: 'Regular working hours within the norm',
      field: 'normal_code',
    },
    {
      label: 'Overtime',
      description: 'All overtime categories (weekday / Saturday / Sunday / day-off)',
      field: 'overtime_code',
    },
    {
      label: 'Callout (Udrykning)',
      description: 'Call-out payment for qualifying entries',
      field: 'callout_code',
    },
  ];

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-[1.1rem] font-semibold mb-1 flex items-center gap-2">
          <span>🗂️</span>
          Pay Code Mapping
        </h3>
        <p className="text-[0.85rem] text-slate-400">
          Map time registration categories to Danløn pay-part codes
        </p>
      </div>

      {isDemo && (
        <div className="mb-4 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-3 py-2">
          Showing demo pay-part codes (T1 / T2 / T3). Live codes will load once the Danløn API is reachable.
        </div>
      )}

      {error && (
        <div className="mb-4">
          <Status type="error" message={error} />
        </div>
      )}

      {saved && (
        <div className="mb-4">
          <Status type="success" message="Mapping saved successfully." />
        </div>
      )}

      {loading ? (
        <div className="text-center py-6">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-accent" />
          <p className="mt-2 text-slate-400 text-sm">Loading pay codes…</p>
        </div>
      ) : (
        <div className="space-y-4">
          {rows.map(({ label, description, field }) => (
            <div key={field} className="grid grid-cols-2 gap-4 items-start">
              <div>
                <p className="text-sm font-medium text-slate-200">{label}</p>
                <p className="text-xs text-slate-500">{description}</p>
              </div>
              <div>
                {meta.length > 0 ? (
                  <select
                    className={selectClass}
                    value={mapping[field]}
                    onChange={e => setMapping(prev => ({ ...prev, [field]: e.target.value }))}
                  >
                    {meta.map(m => (
                      <option key={m.code} value={m.code}>
                        {m.code} – {m.description}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    className={selectClass}
                    value={mapping[field]}
                    onChange={e => setMapping(prev => ({ ...prev, [field]: e.target.value }))}
                    placeholder="Pay code (e.g. T1)"
                  />
                )}
                {meta.length > 0 && (
                  <p className="mt-1 text-xs text-slate-600">
                    {(() => {
                      const m = meta.find(x => x.code === mapping[field]);
                      if (!m) return null;
                      const allowed = [
                        m.unitsAllowed && 'units',
                        m.rateAllowed && 'rate',
                        m.amountAllowed && 'amount',
                      ].filter(Boolean);
                      return `Allows: ${allowed.join(', ') || 'nothing'}`;
                    })()}
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* Summary */}
          <div className="bg-bg-secondary rounded-lg p-3 text-xs text-slate-400 space-y-1">
            <p className="font-medium text-slate-300">Current mapping</p>
            <p>Normal → <span className="text-slate-200">{codeLabel(mapping.normal_code)}</span></p>
            <p>Overtime → <span className="text-slate-200">{codeLabel(mapping.overtime_code)}</span></p>
            <p>Callout → <span className="text-slate-200">{codeLabel(mapping.callout_code)}</span></p>
          </div>

          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : '💾 Save mapping'}
          </Button>
        </div>
      )}
    </Card>
  );
}

import { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';

interface DanlonEmployee {
  id: string;
  name: string;
  domainId?: string;
  active?: boolean;
  email?: string;
}

interface EmployeeMapping {
  ftz_employee_name: string;
  danlon_employee_id: string;
  danlon_employee_name: string;
}

interface FallbackEmployee {
  danlon_employee_id: string;
  danlon_employee_name: string;
}

interface DanlonEmployeeMappingProps {
  connected: boolean;
}

function employeeLabel(emp: DanlonEmployee): string {
  return emp.domainId ? `${emp.domainId} – ${emp.name}` : emp.name;
}

export function DanlonEmployeeMapping({ connected }: DanlonEmployeeMappingProps) {
  const [danlonEmployees, setDanlonEmployees] = useState<DanlonEmployee[]>([]);
  const [mappings, setMappings] = useState<EmployeeMapping[]>([]);
  const [fallback, setFallback] = useState<FallbackEmployee | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!connected) return;
    setLoading(true);
    setError(null);
    try {
      const [empRes, mapRes] = await Promise.all([
        fetch('/danlon/employees'),
        fetch('/danlon/employee-mapping'),
      ]);

      if (!empRes.ok) throw new Error('Failed to fetch Danløn employees');
      if (!mapRes.ok) throw new Error('Failed to fetch employee mapping');

      const empData = await empRes.json();
      const mapData = await mapRes.json();

      setDanlonEmployees(empData.employees ?? []);
      setMappings(mapData.mappings ?? []);
      setFallback(mapData.fallback ?? null);
    } catch (err) {
      setError('Kunne ikke indlæse medarbejderkonfiguration.');
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
      const response = await fetch('/danlon/employee-mapping', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mappings, fallback }),
      });
      if (response.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Kunne ikke gemme mapping.');
      }
    } catch (err) {
      setError('Kunne ikke gemme mapping.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const addRow = () => {
    setMappings(prev => [
      ...prev,
      { ftz_employee_name: '', danlon_employee_id: '', danlon_employee_name: '' },
    ]);
  };

  const removeRow = (index: number) => {
    setMappings(prev => prev.filter((_, i) => i !== index));
  };

  const updateRow = (index: number, field: keyof EmployeeMapping, value: string) => {
    setMappings(prev =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    );
  };

  const handleRowDanlonChange = (index: number, danlonEmployeeId: string) => {
    const emp = danlonEmployees.find(e => e.id === danlonEmployeeId);
    setMappings(prev =>
      prev.map((row, i) =>
        i === index
          ? {
              ...row,
              danlon_employee_id: danlonEmployeeId,
              danlon_employee_name: emp ? employeeLabel(emp) : '',
            }
          : row
      )
    );
  };

  const handleFallbackChange = (danlonEmployeeId: string) => {
    if (!danlonEmployeeId) {
      setFallback(null);
      return;
    }
    const emp = danlonEmployees.find(e => e.id === danlonEmployeeId);
    setFallback({
      danlon_employee_id: danlonEmployeeId,
      danlon_employee_name: emp ? employeeLabel(emp) : '',
    });
  };

  if (!connected) return null;

  const inputClass =
    'w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500';
  const selectClass =
    'w-full bg-bg-secondary border border-slate-700 rounded px-3 py-2 text-sm text-slate-200';

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-[1.1rem] font-semibold mb-1 flex items-center gap-2">
          <span>👥</span>
          Medarbejder Mapping
        </h3>
        <p className="text-[0.85rem] text-slate-400">
          Knyt FTZ-medarbejdere til Danløn-medarbejdere. Fallback-medarbejderen bruges til alle
          ikke-matchede (egnet til demo/test).
        </p>
      </div>

      {error && (
        <div className="mb-4">
          <Status type="error" message={error} />
        </div>
      )}

      {saved && (
        <div className="mb-4">
          <Status type="success" message="Medarbejder-mapping gemt." />
        </div>
      )}

      {loading ? (
        <div className="text-center py-6">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-accent" />
          <p className="mt-2 text-slate-400 text-sm">Indlæser medarbejdere…</p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Fallback employee */}
          <div>
            <p className="text-sm font-medium text-slate-200 mb-1">Fallback-medarbejder</p>
            <p className="text-xs text-slate-500 mb-2">
              Alle FTZ-medarbejdere uden specifik mapping sendes til denne Danløn-medarbejder. Lad
              stå tom for kun at bruge eksplicitte mappings.
            </p>
            {danlonEmployees.length > 0 ? (
              <select
                className={selectClass}
                value={fallback?.danlon_employee_id ?? ''}
                onChange={e => handleFallbackChange(e.target.value)}
              >
                <option value="">— Ingen fallback —</option>
                {danlonEmployees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {employeeLabel(emp)}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-slate-500 italic">
                Ingen Danløn-medarbejdere fundet. Tjek forbindelsen.
              </p>
            )}
            {fallback && (
              <p className="mt-1 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 rounded px-2 py-1">
                Alle ikke-matchede FTZ-medarbejdere sendes til:{' '}
                <strong>{fallback.danlon_employee_name}</strong>
              </p>
            )}
          </div>

          {/* Explicit mappings */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-sm font-medium text-slate-200">Eksplicitte mappings</p>
                <p className="text-xs text-slate-500">FTZ-navn → Danløn-medarbejder</p>
              </div>
              <button
                type="button"
                onClick={addRow}
                className="text-xs text-accent hover:text-accent-light border border-accent/40 rounded px-2 py-1 transition-colors"
              >
                + Tilføj
              </button>
            </div>

            {mappings.length === 0 ? (
              <p className="text-xs text-slate-500 italic">
                Ingen eksplicitte mappings. Brug fallback-medarbejderen til test.
              </p>
            ) : (
              <div className="space-y-2">
                {mappings.map((row, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-center">
                    <input
                      type="text"
                      className={inputClass}
                      placeholder="FTZ-navn (præcis)"
                      value={row.ftz_employee_name}
                      onChange={e => updateRow(i, 'ftz_employee_name', e.target.value)}
                    />
                    {danlonEmployees.length > 0 ? (
                      <select
                        className={selectClass}
                        value={row.danlon_employee_id}
                        onChange={e => handleRowDanlonChange(i, e.target.value)}
                      >
                        <option value="">— Vælg medarbejder —</option>
                        {danlonEmployees.map(emp => (
                          <option key={emp.id} value={emp.id}>
                            {employeeLabel(emp)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        className={inputClass}
                        placeholder="Danløn employee ID"
                        value={row.danlon_employee_id}
                        onChange={e => updateRow(i, 'danlon_employee_id', e.target.value)}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => removeRow(i)}
                      className="text-slate-500 hover:text-red-400 transition-colors text-lg leading-none"
                      title="Fjern"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Gemmer…' : '💾 Gem medarbejder-mapping'}
          </Button>
        </div>
      )}
    </Card>
  );
}

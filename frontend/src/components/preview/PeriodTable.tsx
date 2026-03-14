import React, { useState } from 'react';
import clsx from 'clsx';
import type { PeriodRecord, OvertimeOverrides } from '../../types';

interface PeriodTableProps {
  data: PeriodRecord[];
  overtimeOverrides: OvertimeOverrides;
  onOvertimeOverride: (periodKey: string, field: string, value: number) => void;
}

const TH = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap bg-bg-secondary font-semibold text-slate-400 sticky top-0 z-10';
const TH_FIRST = `${TH} left-0 z-[15] shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap group-hover/row:bg-blue-500/5';
const TD_FIRST = `${TD} sticky left-0 z-[5] bg-bg-card shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD_NUM = `${TD} text-right [font-variant-numeric:tabular-nums]`;

/* Editable OT cell — shows a number input, highlights when overridden */
interface OtCellProps {
  value: number;
  overrideValue?: number;
  colorClass: string;
  onChange: (v: number) => void;
  title?: string;
}

const OtCell: React.FC<OtCellProps> = ({ value, overrideValue, colorClass, onChange, title }) => {
  const displayValue = overrideValue !== undefined ? overrideValue : value;
  const isOverridden = overrideValue !== undefined;

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const startEdit = () => {
    setDraft(displayValue.toFixed(2));
    setEditing(true);
  };

  const commitEdit = () => {
    const parsed = parseFloat(draft);
    if (!isNaN(parsed) && parsed >= 0) {
      onChange(parsed);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <td className={TD_NUM}>
        <input
          type="number"
          min="0"
          step="0.25"
          value={draft}
          className="w-[70px] bg-bg-secondary border border-accent rounded px-1.5 py-0.5 text-right text-[0.85rem] [font-variant-numeric:tabular-nums] outline-none"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitEdit();
            if (e.key === 'Escape') setEditing(false);
          }}
          autoFocus
        />
      </td>
    );
  }

  return (
    <td
      className={clsx(
        TD_NUM,
        displayValue > 0 && colorClass,
        displayValue > 0 && 'font-medium',
        isOverridden && 'ring-1 ring-inset ring-amber-500/50 bg-amber-500/[0.07]',
        'cursor-pointer select-none'
      )}
      title={title ? (isOverridden ? `${title} (overskrevet)` : title) : undefined}
      onClick={startEdit}
    >
      {displayValue.toFixed(2)}
      {isOverridden && <span className="ml-0.5 text-amber-400 text-[0.7rem]">✎</span>}
    </td>
  );
};

export const PeriodTable: React.FC<PeriodTableProps> = ({ data, overtimeOverrides, onOvertimeOverride }) => {
  return (
    <div className="overflow-x-auto max-h-[600px] overflow-y-auto [-webkit-overflow-scrolling:touch]">
      <div className="px-4 py-2 text-[0.75rem] text-slate-500 border-b border-border bg-bg-secondary/50">
        OT-timer er beregnet over 14-dages perioden (norm 74 timer). Klik på en OT-celle for at rette værdien.
        Gule felter er manuelt rettede.
      </div>
      <table className="w-full min-w-full border-collapse text-[0.85rem] max-md:text-[0.8rem]">
        <thead>
          <tr>
            <th className={TH_FIRST}>Medarbejder</th>
            <th className={TH}>Periode</th>
            <th className={TH}>Start</th>
            <th className={TH}>Slut</th>
            <th className={TH}>Hverdage</th>
            <th className={TH}>Normal</th>
            <th className={TH} title="OT1: 1. og 2. overtidstime (48,10 kr)">OT1</th>
            <th className={TH} title="OT2: 3. og 4. overtidstime (76,80 kr)">OT2</th>
            <th className={TH} title="OT3: 5.+ overtidstime (143,70 kr)">OT3</th>
            <th className={TH} title="Weekend timer — lørdag + søndag (flat OT3 sats, 143,70 kr)">OT Weekend</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const periodKey = `${row.worker_name}__${row.year}__${row.period_number}`;
            const ov = overtimeOverrides[periodKey];

            return (
              <tr key={index} className="group/row">
                <td className={TD_FIRST}>{row.worker_name}</td>
                <td className={TD}>
                  <span className="font-medium">P{row.period_number + 1}</span>
                  <span className="text-slate-500 ml-1 text-[0.75rem]">{row.year}</span>
                </td>
                <td className={TD}>{row.period_start}</td>
                <td className={TD}>{row.period_end}</td>
                <td className={TD_NUM}>{row.weekday_hours.toFixed(2)}</td>
                <td className={TD_NUM}>{row.normal_hours.toFixed(2)}</td>
                <OtCell
                  value={row.overtime_1}
                  overrideValue={ov?.overtime_1}
                  colorClass="text-ot1"
                  title="OT1 — klik for at rette"
                  onChange={(v) => onOvertimeOverride(periodKey, 'overtime_1', v)}
                />
                <OtCell
                  value={row.overtime_2}
                  overrideValue={ov?.overtime_2}
                  colorClass="text-ot2"
                  title="OT2 — klik for at rette"
                  onChange={(v) => onOvertimeOverride(periodKey, 'overtime_2', v)}
                />
                <OtCell
                  value={row.overtime_3}
                  overrideValue={ov?.overtime_3}
                  colorClass="text-ot3"
                  title="OT3 — klik for at rette"
                  onChange={(v) => onOvertimeOverride(periodKey, 'overtime_3', v)}
                />
                <OtCell
                  value={row.overtime_breakdown.ot_weekend}
                  overrideValue={ov?.ot_weekend}
                  colorClass="text-ot3"
                  title="OT Weekend — klik for at rette"
                  onChange={(v) => onOvertimeOverride(periodKey, 'ot_weekend', v)}
                />
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

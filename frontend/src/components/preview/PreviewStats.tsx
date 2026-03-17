import React, { useState } from 'react';
import clsx from 'clsx';
import type { PreviewData, CallOutSelections, StatsOverrides } from '../../types';

interface PreviewStatsProps {
  data: PreviewData;
  callOutSelections: CallOutSelections;
  statsOverrides: StatsOverrides;
  onStatsOverride: (field: keyof StatsOverrides, value: number) => void;
  onStatsReset: (field: keyof StatsOverrides) => void;
}

interface EditableStatCardProps {
  label: string;
  calculatedValue: number;
  overrideValue?: number;
  color?: string;
  field: keyof StatsOverrides;
  onOverride: (field: keyof StatsOverrides, value: number) => void;
  onReset: (field: keyof StatsOverrides) => void;
}

const EditableStatCard: React.FC<EditableStatCardProps> = ({
  label,
  calculatedValue,
  overrideValue,
  color,
  field,
  onOverride,
  onReset,
}) => {
  const displayValue = overrideValue !== undefined ? overrideValue : calculatedValue;
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
      onOverride(field, parsed);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex flex-col gap-0.5">
        <span className="text-xs text-slate-500 uppercase tracking-wider">{label}</span>
        <input
          type="number"
          min="0"
          step="0.25"
          value={draft}
          className="w-[90px] bg-bg-secondary border border-accent rounded px-1.5 py-0.5 text-right text-[1rem] font-semibold [font-variant-numeric:tabular-nums] outline-none"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitEdit();
            if (e.key === 'Escape') setEditing(false);
          }}
          autoFocus
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-slate-500 uppercase tracking-wider">{label}</span>
      <div className="flex items-center gap-1">
        <span
          className={clsx(
            'text-[1.1rem] font-semibold cursor-pointer select-none',
            color ?? 'text-slate-100',
            isOverridden && 'ring-1 ring-inset ring-amber-500/50 bg-amber-500/[0.07] rounded px-1'
          )}
          title={
            isOverridden
              ? `Beregnet: ${calculatedValue.toFixed(2)} — klik for at rette`
              : 'Klik for at rette'
          }
          onClick={startEdit}
        >
          {displayValue.toFixed(2)}
          {isOverridden && <span className="ml-0.5 text-amber-400 text-[0.7rem]">✎</span>}
        </span>
        {isOverridden && (
          <button
            className="text-slate-500 hover:text-red-400 text-[0.75rem] leading-none transition-colors"
            title={`Nulstil til beregnet (${calculatedValue.toFixed(2)})`}
            onClick={() => onReset(field)}
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};

export const PreviewStats: React.FC<PreviewStatsProps> = ({
  data,
  callOutSelections,
  statsOverrides,
  onStatsOverride,
  onStatsReset,
}) => {
  const { daily, periods } = data;

  let totalHours = 0, weekdayHours = 0, normalHours = 0, ot1 = 0, ot2 = 0, ot3 = 0, otWeekend = 0;
  periods.forEach(p => {
    totalHours += p.total_hours;
    weekdayHours += p.weekday_hours;
    normalHours += p.normal_hours;
    const otb = p.overtime_breakdown;
    ot1 += otb.ot_weekday_hour_1_2;
    ot2 += otb.ot_weekday_hour_3_4;
    ot3 += otb.ot_weekday_hour_5_plus + otb.ot_dayoff_day + otb.ot_dayoff_night;
    otWeekend += otb.ot_weekend;
  });

  let callOutQualifyingDays = 0;
  let callOutSelectedCount = 0;
  daily.forEach(d => {
    if (d.has_call_out_qualifying_time) {
      callOutQualifyingDays++;
      if (callOutSelections[d.date]) {
        callOutSelectedCount++;
      }
    }
  });

  const hasAnyOverride = Object.keys(statsOverrides).length > 0;

  return (
    <div className="flex flex-col">
      {hasAnyOverride && (
        <div className="px-5 py-1.5 text-[0.72rem] text-amber-400 bg-amber-500/[0.06] border-b border-amber-500/20 flex items-center gap-1.5">
          <span>✎</span>
          <span>Manuelle rettelser er aktive — gule værdier afviger fra beregningen. Klik × for at nulstille.</span>
        </div>
      )}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(110px,1fr))] gap-5 p-4 px-5 bg-bg-secondary border-b border-border max-md:grid-cols-2 max-md:gap-4">
        {/* Read-only cards */}
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Registreringer</span>
          <span className="text-[1.1rem] font-semibold text-slate-100">{daily.length}</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Total Timer</span>
          <span className="text-[1.1rem] font-semibold text-slate-100">{totalHours.toFixed(2)}</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Hverdag Timer</span>
          <span className="text-[1.1rem] font-semibold text-slate-100">{weekdayHours.toFixed(2)}</span>
        </div>

        {/* Editable cards */}
        <EditableStatCard
          label="Normal"
          calculatedValue={normalHours}
          overrideValue={statsOverrides.normal_hours}
          field="normal_hours"
          onOverride={onStatsOverride}
          onReset={onStatsReset}
        />
        <EditableStatCard
          label="Overtid 1"
          calculatedValue={ot1}
          overrideValue={statsOverrides.ot1}
          color="text-ot1"
          field="ot1"
          onOverride={onStatsOverride}
          onReset={onStatsReset}
        />
        <EditableStatCard
          label="Overtid 2"
          calculatedValue={ot2}
          overrideValue={statsOverrides.ot2}
          color="text-ot2"
          field="ot2"
          onOverride={onStatsOverride}
          onReset={onStatsReset}
        />
        <EditableStatCard
          label="Overtid 3"
          calculatedValue={ot3}
          overrideValue={statsOverrides.ot3}
          color="text-ot3"
          field="ot3"
          onOverride={onStatsOverride}
          onReset={onStatsReset}
        />
        <EditableStatCard
          label="OT Weekend"
          calculatedValue={otWeekend}
          overrideValue={statsOverrides.ot_weekend}
          color="text-ot3"
          field="ot_weekend"
          onOverride={onStatsOverride}
          onReset={onStatsReset}
        />

        {/* Read-only cards */}
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Call Out Dage</span>
          <span className="text-[1.1rem] font-semibold text-amber-500">{callOutSelectedCount}/{callOutQualifyingDays}</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Call Out Betaling</span>
          <span className="text-[1.1rem] font-semibold text-amber-500">{callOutSelectedCount * 750} kr</span>
        </div>
      </div>
    </div>
  );
};

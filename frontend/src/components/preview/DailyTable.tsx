import React from 'react';
import clsx from 'clsx';
import type { DailyRecord, CallOutSelections, AbsenceSelections, AbsenceType } from '../../types';

interface DailyTableProps {
  data: DailyRecord[];
  callOutSelections: CallOutSelections;
  absenceSelections: AbsenceSelections;
  onCallOutChange: (date: string, checked: boolean) => void;
  onAbsenceChange: (date: string, absenceType: AbsenceType) => void;
  onShowDetails: (index: number) => void;
}

/* Reusable cell styles */
const TH = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap bg-bg-secondary font-semibold text-slate-400 sticky top-0 z-10';
const TH_FIRST = `${TH} left-0 z-[15] shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap group-hover/row:bg-blue-500/5';
const TD_FIRST = `${TD} sticky left-0 z-[5] bg-bg-card shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD_NUM = `${TD} text-right [font-variant-numeric:tabular-nums]`;

export const DailyTable: React.FC<DailyTableProps> = ({
  data,
  callOutSelections,
  absenceSelections,
  onCallOutChange,
  onAbsenceChange,
  onShowDetails,
}) => {
  return (
    <div className="overflow-x-auto max-h-[600px] overflow-y-auto [-webkit-overflow-scrolling:touch]">
      <table className="w-full min-w-full border-collapse text-[0.85rem] max-md:text-[0.8rem]">
        <thead>
          <tr>
            <th className={TH_FIRST}>Medarbejder</th>
            <th className={TH}>Dato</th>
            <th className={TH}>Dag</th>
            <th className={TH}>Type</th>
            <th className={TH}>Total</th>
            <th className={TH}>Normal</th>
            <th className={TH} title="Weekend timer (lørdag + søndag) — OT3 sats (143,70 kr)">OT Weekend</th>
            <th className={TH} title="Call Out betaling (750 kr) for vagter der starter før 07:00 eller efter 15:30">Call Out / Fravær</th>
            <th className={TH}>Detaljer</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const otb = row.overtime_breakdown;
            const isEmpty = row.entries.length === 0;
            const isEligible = row.has_call_out_qualifying_time;
            const isChecked = callOutSelections[row.date] || false;
            const currentAbsence = absenceSelections[row.date] || 'None';
            const hasHalfSick = (row.half_sick_hours ?? 0) > 0;

            /* Determine row background — most specific wins */
            let rowBg = '';
            if (isEmpty) {
              if (currentAbsence === 'Vacation') rowBg = 'bg-amber-400/15';
              else if (currentAbsence === 'Sick') rowBg = 'bg-blue-500/15';
              else if (currentAbsence === 'Kursus') rowBg = 'bg-emerald-500/15';
              else rowBg = 'bg-slate-400/5';
            } else {
              if (hasHalfSick) rowBg = 'bg-blue-500/[0.07]';
              else if (row.day_type === 'Sunday') rowBg = 'bg-red-500/10';
              else if (row.day_type === 'Saturday') rowBg = 'bg-orange-500/[0.08]';
            }

            return (
              <tr key={index} className={clsx('group/row', rowBg)}>
                <td className={TD_FIRST}>{row.worker}</td>
                <td className={TD}>{row.date}</td>
                <td className={TD}>{row.day}</td>
                <td className={TD}>{row.day_type}</td>
                <td className={clsx(TD_NUM, isEmpty && 'text-slate-400 opacity-70')}>
                  {row.total_hours.toFixed(2)}
                  {hasHalfSick && (
                    <span
                      className="ml-1 text-blue-400 text-[0.75rem]"
                      title={`Halv sygedag: +${(row.half_sick_hours ?? 0).toFixed(2)}t`}
                    >
                      (+{(row.half_sick_hours ?? 0).toFixed(2)})
                    </span>
                  )}
                </td>
                <td className={clsx(TD_NUM, isEmpty && 'text-slate-400 opacity-70')}>
                  {row.normal_hours.toFixed(2)}
                </td>
                <td className={clsx(TD_NUM, otb.ot_weekend > 0 && 'text-ot3 font-medium')}>
                  {otb.ot_weekend.toFixed(2)}
                </td>
                <td className={`${TD} text-center`}>
                  {isEmpty ? (
                    <AbsenceSelector
                      currentAbsence={currentAbsence}
                      dayName={row.day}
                      date={row.date}
                      onAbsenceChange={onAbsenceChange}
                    />
                  ) : isEligible ? (
                    <>
                      <input
                        type="checkbox"
                        className="cursor-pointer w-[18px] h-[18px] mr-1"
                        checked={isChecked}
                        onChange={(e) => onCallOutChange(row.date, e.target.checked)}
                      />
                      <span className="text-base cursor-help" title="Kvalificerer til Call Out betaling">⏰</span>
                    </>
                  ) : (
                    <input
                      type="checkbox"
                      className="w-[18px] h-[18px] cursor-not-allowed opacity-30"
                      disabled
                      title="Ingen registreringer udenfor normal tid"
                    />
                  )}
                </td>
                <td className={`${TD} text-center`}>
                  <button
                    className="bg-transparent border-none text-xl cursor-pointer py-1 px-2 transition-transform opacity-70 hover:scale-110 hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-30"
                    onClick={() => onShowDetails(index)}
                    title="Vis tidsregistreringer"
                    disabled={isEmpty}
                  >
                    📋
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

/* Sub-component for the absence button group */
interface AbsenceSelectorProps {
  currentAbsence: string;
  dayName: string;
  date: string;
  onAbsenceChange: (date: string, absenceType: AbsenceType) => void;
}

const absenceOptions: { type: AbsenceType; label: string; activeColor: string }[] = [
  { type: 'None', label: '-', activeColor: 'bg-accent border-accent' },
  { type: 'Vacation', label: 'Ferie', activeColor: 'bg-amber-500 border-amber-500' },
  { type: 'Sick', label: 'Syg', activeColor: 'bg-blue-500 border-blue-500' },
  { type: 'Kursus', label: 'Kursus', activeColor: 'bg-emerald-500 border-emerald-500' },
];

const AbsenceSelector: React.FC<AbsenceSelectorProps> = ({ currentAbsence, dayName, date, onAbsenceChange }) => {
  const hours = dayName === 'Friday' ? '7.0' : '7.5';

  return (
    <div className="flex gap-1 justify-center flex-wrap">
      {absenceOptions.map(({ type, label, activeColor }) => {
        const isActive = currentAbsence === type;
        const title = type === 'None' ? 'Ingen fravær' : `${label} (${hours} timer)`;
        return (
          <button
            key={type}
            className={clsx(
              'py-1 px-2 text-xs border rounded cursor-pointer transition-all whitespace-nowrap',
              isActive
                ? `${activeColor} text-white font-medium`
                : 'border-border bg-bg-card text-slate-100 hover:bg-blue-500/10'
            )}
            onClick={() => onAbsenceChange(date, type)}
            title={title}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

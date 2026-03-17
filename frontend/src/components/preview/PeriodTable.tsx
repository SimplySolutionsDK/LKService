import React from 'react';
import type { PeriodRecord } from '../../types';

interface PeriodTableProps {
  data: PeriodRecord[];
}

const TH = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap bg-bg-secondary font-semibold text-slate-400 sticky top-0 z-10';
const TH_FIRST = `${TH} left-0 z-[15] shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap group-hover/row:bg-blue-500/5';
const TD_FIRST = `${TD} sticky left-0 z-[5] bg-bg-card shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD_NUM = `${TD} text-right [font-variant-numeric:tabular-nums]`;

export const PeriodTable: React.FC<PeriodTableProps> = ({ data }) => {
  return (
    <div className="overflow-x-auto max-h-[600px] overflow-y-auto [-webkit-overflow-scrolling:touch]">
      <table className="w-full min-w-full border-collapse text-[0.85rem] max-md:text-[0.8rem]">
        <thead>
          <tr>
            <th className={TH_FIRST}>Medarbejder</th>
            <th className={TH}>Periode</th>
            <th className={TH}>Start</th>
            <th className={TH}>Slut</th>
            <th className={TH}>Hverdage</th>
            <th className={TH}>Normal</th>
            <th className={TH} title="OT1: 1. og 2. overtidstime">OT1</th>
            <th className={TH} title="OT2: 3. og 4. overtidstime">OT2</th>
            <th className={TH} title="OT3: 5.+ overtidstime">OT3</th>
            <th className={TH} title="Weekend timer — lørdag + søndag (flat OT3 sats)">OT Weekend</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
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
              <td className={`${TD_NUM} ${row.overtime_1 > 0 ? 'text-ot1 font-medium' : ''}`}>
                {row.overtime_1.toFixed(2)}
              </td>
              <td className={`${TD_NUM} ${row.overtime_2 > 0 ? 'text-ot2 font-medium' : ''}`}>
                {row.overtime_2.toFixed(2)}
              </td>
              <td className={`${TD_NUM} ${row.overtime_3 > 0 ? 'text-ot3 font-medium' : ''}`}>
                {row.overtime_3.toFixed(2)}
              </td>
              <td className={`${TD_NUM} ${row.overtime_breakdown.ot_weekend > 0 ? 'text-ot3 font-medium' : ''}`}>
                {row.overtime_breakdown.ot_weekend.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

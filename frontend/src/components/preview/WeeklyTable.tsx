import React from 'react';
import clsx from 'clsx';
import type { WeeklyRecord } from '../../types';

interface WeeklyTableProps {
  data: WeeklyRecord[];
}

const TH = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap bg-bg-secondary font-semibold text-slate-400 sticky top-0 z-10';
const TH_FIRST = `${TH} left-0 z-[15] shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD = 'py-2.5 px-3.5 text-left border-b border-border whitespace-nowrap group-hover/row:bg-blue-500/5';
const TD_FIRST = `${TD} sticky left-0 z-[5] bg-bg-card shadow-[2px_0_4px_rgba(0,0,0,0.1)]`;
const TD_NUM = `${TD} text-right [font-variant-numeric:tabular-nums]`;

export const WeeklyTable: React.FC<WeeklyTableProps> = ({ data }) => {
  return (
    <div className="overflow-x-auto max-h-[600px] overflow-y-auto [-webkit-overflow-scrolling:touch]">
      <table className="w-full min-w-full border-collapse text-[0.85rem] max-md:text-[0.8rem]">
        <thead>
          <tr>
            <th className={TH_FIRST}>Medarbejder</th>
            <th className={TH}>År</th>
            <th className={TH}>Uge</th>
            <th className={TH}>Total Timer</th>
            <th className={TH}>Normal Timer</th>
            <th className={TH} title="Hverdage: 1. & 2. overtidstime">OT Hvd 1-2</th>
            <th className={TH} title="Hverdage: 3. & 4. overtidstime">OT Hvd 3-4</th>
            <th className={TH} title="Hverdage: 5.+ overtidstime">OT Hvd 5+</th>
            <th className={TH} title="Lørdag timer">OT Lør</th>
            <th className={TH} title="Søndag timer">OT Søn</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const otb = row.overtime_breakdown;
            const ot_lor_total = otb.ot_saturday_day + otb.ot_saturday_night;
            const ot_son_total = otb.ot_sunday_before_noon + otb.ot_sunday_after_noon;

            return (
              <tr key={index} className="group/row">
                <td className={TD_FIRST}>{row.worker_name}</td>
                <td className={TD_NUM}>{row.year}</td>
                <td className={TD_NUM}>{row.week_number}</td>
                <td className={TD_NUM}>{row.total_hours.toFixed(2)}</td>
                <td className={TD_NUM}>{row.normal_hours.toFixed(2)}</td>
                <td className={clsx(TD_NUM, otb.ot_weekday_hour_1_2 > 0 && 'text-ot1 font-medium')}>
                  {otb.ot_weekday_hour_1_2.toFixed(2)}
                </td>
                <td className={clsx(TD_NUM, otb.ot_weekday_hour_3_4 > 0 && 'text-ot2 font-medium')}>
                  {otb.ot_weekday_hour_3_4.toFixed(2)}
                </td>
                <td className={clsx(TD_NUM, otb.ot_weekday_hour_5_plus > 0 && 'text-ot3 font-medium')}>
                  {otb.ot_weekday_hour_5_plus.toFixed(2)}
                </td>
                <td className={clsx(TD_NUM, ot_lor_total > 0 && 'text-ot2 font-medium')}>
                  {ot_lor_total.toFixed(2)}
                </td>
                <td className={clsx(TD_NUM, ot_son_total > 0 && 'text-ot3 font-medium')}>
                  {ot_son_total.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

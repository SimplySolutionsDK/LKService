import React from 'react';
import type { PreviewData, CallOutSelections } from '../../types';

interface PreviewStatsProps {
  data: PreviewData;
  callOutSelections: CallOutSelections;
}

export const PreviewStats: React.FC<PreviewStatsProps> = ({ data, callOutSelections }) => {
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

  const stats = [
    { label: 'Registreringer', value: daily.length.toString() },
    { label: 'Total Timer', value: totalHours.toFixed(2) },
    { label: 'Hverdag Timer', value: weekdayHours.toFixed(2) },
    { label: 'Normal', value: normalHours.toFixed(2) },
    { label: 'Overtid 1', value: ot1.toFixed(2), color: 'text-ot1' },
    { label: 'Overtid 2', value: ot2.toFixed(2), color: 'text-ot2' },
    { label: 'Overtid 3', value: ot3.toFixed(2), color: 'text-ot3' },
    { label: 'OT Weekend', value: otWeekend.toFixed(2), color: 'text-ot3' },
    { label: 'Call Out Dage', value: `${callOutSelectedCount}/${callOutQualifyingDays}`, color: 'text-amber-500' },
    { label: 'Call Out Betaling', value: `${callOutSelectedCount * 750} kr`, color: 'text-amber-500' },
  ];

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(110px,1fr))] gap-5 p-4 px-5 bg-bg-secondary border-b border-border max-md:grid-cols-2 max-md:gap-4">
      {stats.map((stat) => (
        <div key={stat.label} className="flex flex-col gap-0.5">
          <span className="text-xs text-slate-500 uppercase tracking-wider">{stat.label}</span>
          <span className={`text-[1.1rem] font-semibold ${stat.color ?? 'text-slate-100'}`}>
            {stat.value}
          </span>
        </div>
      ))}
    </div>
  );
};

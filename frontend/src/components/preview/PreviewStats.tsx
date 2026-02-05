import React from 'react';
import type { PreviewData, CallOutSelections } from '../../types';
import './PreviewStats.css';

interface PreviewStatsProps {
  data: PreviewData;
  callOutSelections: CallOutSelections;
}

export const PreviewStats: React.FC<PreviewStatsProps> = ({ data, callOutSelections }) => {
  const { daily, weekly } = data;

  let totalHours = 0, normalHours = 0, ot1 = 0, ot2 = 0, ot3 = 0;
  weekly.forEach(w => {
    totalHours += w.total_hours;
    normalHours += w.normal_hours;
    const otb = w.overtime_breakdown;
    ot1 += otb.ot_weekday_hour_1_2;
    ot2 += otb.ot_weekday_hour_3_4;
    ot3 += otb.ot_weekday_hour_5_plus + otb.ot_saturday_day + otb.ot_saturday_night +
           otb.ot_sunday_before_noon + otb.ot_sunday_after_noon;
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

  return (
    <div className="preview-stats">
      <div className="stat">
        <span className="stat-label">Registreringer</span>
        <span className="stat-value">{daily.length}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Total Timer</span>
        <span className="stat-value">{totalHours.toFixed(2)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Normal</span>
        <span className="stat-value">{normalHours.toFixed(2)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Overtid 1</span>
        <span className="stat-value overtime1">{ot1.toFixed(2)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Overtid 2</span>
        <span className="stat-value overtime2">{ot2.toFixed(2)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Overtid 3</span>
        <span className="stat-value overtime3">{ot3.toFixed(2)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Call Out Dage</span>
        <span className="stat-value call-out">{callOutSelectedCount}/{callOutQualifyingDays}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Call Out Betaling</span>
        <span className="stat-value call-out">{callOutSelectedCount * 750} kr</span>
      </div>
    </div>
  );
};

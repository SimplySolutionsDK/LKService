import React from 'react';
import type { DailyRecord, CallOutSelections } from '../../types';
import './Table.css';

interface DailyTableProps {
  data: DailyRecord[];
  callOutSelections: CallOutSelections;
  onCallOutChange: (date: string, checked: boolean) => void;
  onShowDetails: (index: number) => void;
}

export const DailyTable: React.FC<DailyTableProps> = ({
  data,
  callOutSelections,
  onCallOutChange,
  onShowDetails,
}) => {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Medarbejder</th>
            <th>Dato</th>
            <th>Dag</th>
            <th>Type</th>
            <th>Total</th>
            <th>Normal</th>
            <th title="Hverdage: 1. & 2. overtidstime (48,10 kr)">OT Hvd 1-2</th>
            <th title="Hverdage: 3. & 4. overtidstime (76,80 kr)">OT Hvd 3-4</th>
            <th title="Hverdage: 5.+ overtidstime (143,70 kr)">OT Hvd 5+</th>
            <th title="Lørdag timer (dag: 76,80 kr, nat: 143,70 kr)">OT Lør</th>
            <th title="Søndag timer (før 12: 95,75 kr, efter 12: 143,70 kr)">OT Søn</th>
            <th title="Call Out betaling (750 kr) for vagter der starter før 07:00 eller efter 15:30">Call Out 🕐</th>
            <th>Detaljer</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const otb = row.overtime_breakdown;
            const ot_lor_total = otb.ot_saturday_day + otb.ot_saturday_night;
            const ot_son_total = otb.ot_sunday_before_noon + otb.ot_sunday_after_noon;
            
            let rowClass = '';
            if (row.day_type === 'Sunday') rowClass = 'day-sunday';
            else if (row.day_type === 'Saturday') rowClass = 'day-saturday';

            const isEligible = row.has_call_out_qualifying_time;
            const isChecked = callOutSelections[row.date] || false;

            return (
              <tr key={index} className={rowClass}>
                <td>{row.worker}</td>
                <td>{row.date}</td>
                <td>{row.day}</td>
                <td>{row.day_type}</td>
                <td className="number">{row.total_hours.toFixed(2)}</td>
                <td className="number">{row.normal_hours.toFixed(2)}</td>
                <td className={`number ${otb.ot_weekday_hour_1_2 > 0 ? 'overtime1' : ''}`}>
                  {otb.ot_weekday_hour_1_2.toFixed(2)}
                </td>
                <td className={`number ${otb.ot_weekday_hour_3_4 > 0 ? 'overtime2' : ''}`}>
                  {otb.ot_weekday_hour_3_4.toFixed(2)}
                </td>
                <td className={`number ${otb.ot_weekday_hour_5_plus > 0 ? 'overtime3' : ''}`}>
                  {otb.ot_weekday_hour_5_plus.toFixed(2)}
                </td>
                <td className={`number ${ot_lor_total > 0 ? 'overtime2' : ''}`}>
                  {ot_lor_total.toFixed(2)}
                </td>
                <td className={`number ${ot_son_total > 0 ? 'overtime3' : ''}`}>
                  {ot_son_total.toFixed(2)}
                </td>
                <td className="call-out-cell">
                  {isEligible ? (
                    <>
                      <input
                        type="checkbox"
                        className="call-out-checkbox"
                        checked={isChecked}
                        onChange={(e) => onCallOutChange(row.date, e.target.checked)}
                      />
                      <span className="call-out-indicator" title="Kvalificerer til Call Out betaling">⏰</span>
                    </>
                  ) : (
                    <input
                      type="checkbox"
                      className="call-out-checkbox"
                      disabled
                      title="Ingen registreringer udenfor normal tid"
                    />
                  )}
                </td>
                <td className="details-cell">
                  <button
                    className="details-btn"
                    onClick={() => onShowDetails(index)}
                    title="Vis tidsregistreringer"
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

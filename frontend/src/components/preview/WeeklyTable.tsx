import React from 'react';
import type { WeeklyRecord } from '../../types';
import './Table.css';

interface WeeklyTableProps {
  data: WeeklyRecord[];
}

export const WeeklyTable: React.FC<WeeklyTableProps> = ({ data }) => {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Medarbejder</th>
            <th>År</th>
            <th>Uge</th>
            <th>Total Timer</th>
            <th>Normal Timer</th>
            <th title="Hverdage: 1. & 2. overtidstime">OT Hvd 1-2</th>
            <th title="Hverdage: 3. & 4. overtidstime">OT Hvd 3-4</th>
            <th title="Hverdage: 5.+ overtidstime">OT Hvd 5+</th>
            <th title="Lørdag timer">OT Lør</th>
            <th title="Søndag timer">OT Søn</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => {
            const otb = row.overtime_breakdown;
            const ot_lor_total = otb.ot_saturday_day + otb.ot_saturday_night;
            const ot_son_total = otb.ot_sunday_before_noon + otb.ot_sunday_after_noon;

            return (
              <tr key={index}>
                <td>{row.worker_name}</td>
                <td className="number">{row.year}</td>
                <td className="number">{row.week_number}</td>
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
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

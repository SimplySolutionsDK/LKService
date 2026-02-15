import React, { useEffect } from 'react';
import type { DailyRecord } from '../../types';

interface EntriesModalProps {
  isOpen: boolean;
  record: DailyRecord | null;
  onClose: () => void;
}

const MTH = 'bg-bg-secondary py-3 px-4 text-left font-semibold text-slate-400 border-b border-border sticky top-0';
const MTD = 'py-3 px-4 border-b border-border text-slate-100';

export const EntriesModal: React.FC<EntriesModalProps> = ({ isOpen, record, onClose }) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handleEscape);
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !record) return null;

  const entries = [...record.entries].sort((a, b) => {
    if (a.start_time < b.start_time) return -1;
    if (a.start_time > b.start_time) return 1;
    return 0;
  });

  return (
    <div
      className="fixed inset-0 bg-black/75 backdrop-blur-[4px] flex items-center justify-center z-[1000] animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-bg-card border border-border rounded-2xl w-[90%] max-w-[700px] max-h-[80vh] flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="py-5 px-6 border-b border-border flex items-center justify-between">
          <h3 className="text-[1.1rem] font-semibold text-slate-100 m-0">
            Tidsregistreringer - {record.worker} - {record.date}
          </h3>
          <button
            className="bg-transparent border-none text-slate-500 text-2xl cursor-pointer py-1 px-2 leading-none transition-colors hover:text-red-500"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <div className="p-6 overflow-y-auto flex-1">
          <table className="w-full border-collapse text-[0.9rem]">
            <thead>
              <tr>
                <th className={MTH}>Sag Nr</th>
                <th className={MTH}>Start</th>
                <th className={MTH}>Slut</th>
                <th className={MTH}>Timer (HH:MM)</th>
                <th className={MTH}>Timer</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => {
                const displayText = entry.case_number || entry.activity;
                return (
                  <tr key={index} className="last:*:border-b-0 hover:*:bg-blue-500/5">
                    <td className={MTD}>{displayText}</td>
                    <td className={MTD}>{entry.start_time}</td>
                    <td className={MTD}>{entry.end_time}</td>
                    <td className={`${MTD} text-right [font-variant-numeric:tabular-nums]`}>
                      {entry.duration_display || '—'}
                    </td>
                    <td className={`${MTD} text-right [font-variant-numeric:tabular-nums]`}>
                      {entry.total_hours.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

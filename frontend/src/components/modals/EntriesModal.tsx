import React, { useEffect } from 'react';
import type { DailyRecord } from '../../types';
import './EntriesModal.css';

interface EntriesModalProps {
  isOpen: boolean;
  record: DailyRecord | null;
  onClose: () => void;
}

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
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">
            Tidsregistreringer - {record.worker} - {record.date}
          </h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <table className="modal-table">
            <thead>
              <tr>
                <th>Sag Nr</th>
                <th>Start</th>
                <th>Slut</th>
                <th>Timer</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => {
                const displayText = entry.case_number || entry.activity;
                return (
                  <tr key={index}>
                    <td>{displayText}</td>
                    <td>{entry.start_time}</td>
                    <td>{entry.end_time}</td>
                    <td className="number">{entry.total_hours.toFixed(2)}</td>
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

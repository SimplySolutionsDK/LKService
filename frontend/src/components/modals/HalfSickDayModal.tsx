import React, { useEffect, useState } from 'react';
import type { DailyRecord } from '../../types';

interface HalfSickDayModalProps {
  isOpen: boolean;
  dailyRecords: DailyRecord[];  // All daily records to populate date list
  onClose: () => void;
  onApply: (date: string) => void;
  isLoading?: boolean;
}

export const HalfSickDayModal: React.FC<HalfSickDayModalProps> = ({
  isOpen,
  dailyRecords,
  onClose,
  onApply,
  isLoading = false,
}) => {
  const [selectedDate, setSelectedDate] = useState<string>('');

  // Lock body scroll while open and handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
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

  // Reset selection each time the modal opens
  useEffect(() => {
    if (isOpen) setSelectedDate('');
  }, [isOpen]);

  if (!isOpen) return null;

  // Only allow weekdays that have actual entries and are not already fully sick
  const eligibleRecords = dailyRecords.filter(
    (r) =>
      r.day_type === 'Weekday' &&
      r.entries.length > 0
  );

  const selectedRecord = eligibleRecords.find((r) => r.date === selectedDate);

  // Norm for the selected day
  const dailyNorm = selectedRecord
    ? selectedRecord.day === 'Friday'
      ? 7.0
      : 7.5
    : null;

  const workedHours = selectedRecord ? selectedRecord.total_hours : null;
  const sickHours =
    dailyNorm !== null && workedHours !== null
      ? Math.max(0, dailyNorm - workedHours)
      : null;

  const alreadyFull =
    workedHours !== null && dailyNorm !== null && workedHours >= dailyNorm;

  const handleApply = () => {
    if (selectedDate && !alreadyFull) {
      onApply(selectedDate);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/75 backdrop-blur-[4px] flex items-center justify-center z-[1000] animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-bg-card border border-border rounded-2xl w-[90%] max-w-[480px] flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="py-5 px-6 border-b border-border flex items-center justify-between">
          <h3 className="text-[1.1rem] font-semibold text-slate-100 m-0">
            Halv Sygedag
          </h3>
          <button
            className="bg-transparent border-none text-slate-500 text-2xl cursor-pointer py-1 px-2 leading-none transition-colors hover:text-red-500"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 flex flex-col gap-4">
          <p className="text-[0.85rem] text-slate-400 leading-relaxed m-0">
            Vælg en dag med arbejdsregistreringer. Systemet tilføjer sygetimer så
            dagstotalen svarer til fuld normdag (7,5t man–tor / 7,0t fre).
          </p>

          {eligibleRecords.length === 0 ? (
            <p className="text-sm text-slate-500 italic">
              Ingen hverdage med arbejdstid fundet i denne periode.
            </p>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-[0.8rem] font-medium text-slate-400 uppercase tracking-wider">
                  Dato
                </label>
                <select
                  className="bg-bg-secondary border border-border rounded-lg px-3 py-2 text-slate-100 text-[0.9rem] outline-none focus:border-accent transition-colors"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                >
                  <option value="">— Vælg dato —</option>
                  {eligibleRecords.map((r) => (
                    <option key={r.date} value={r.date}>
                      {r.date} ({r.day}) — {r.total_hours.toFixed(2)}t arbejdet
                    </option>
                  ))}
                </select>
              </div>

              {selectedRecord && (
                <div className="bg-bg-secondary border border-border rounded-lg p-4 flex flex-col gap-2 text-[0.85rem]">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Arbejdet</span>
                    <span className="text-slate-100 [font-variant-numeric:tabular-nums]">
                      {workedHours!.toFixed(2)} timer
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Norm (fuld dag)</span>
                    <span className="text-slate-100 [font-variant-numeric:tabular-nums]">
                      {dailyNorm!.toFixed(2)} timer
                    </span>
                  </div>
                  <div className="border-t border-border pt-2 flex justify-between">
                    <span className="text-slate-400">Sygetimer der tilføjes</span>
                    <span
                      className={
                        alreadyFull
                          ? 'text-slate-500 [font-variant-numeric:tabular-nums]'
                          : 'text-blue-400 font-semibold [font-variant-numeric:tabular-nums]'
                      }
                    >
                      {alreadyFull ? '0.00 (allerede fuld dag)' : `+${sickHours!.toFixed(2)} timer`}
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="py-4 px-6 border-t border-border flex justify-end gap-3">
          <button
            className="py-2 px-4 rounded-lg border border-border bg-transparent text-slate-400 text-[0.9rem] cursor-pointer hover:bg-bg-secondary transition-colors"
            onClick={onClose}
          >
            Annuller
          </button>
          <button
            className="py-2 px-5 rounded-lg bg-accent text-white text-[0.9rem] font-medium cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!selectedDate || alreadyFull === true || isLoading}
            onClick={handleApply}
          >
            {isLoading ? 'Beregner…' : 'Tilføj sygetimer'}
          </button>
        </div>
      </div>
    </div>
  );
};

import React from 'react';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  disabled?: boolean;
}

const dateInputClass =
  'date-input w-full py-2.5 px-2.5 border border-border rounded bg-bg-primary text-slate-100 text-[0.9rem] transition-colors hover:enabled:border-accent focus:outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] disabled:bg-bg-secondary disabled:cursor-not-allowed disabled:opacity-60';

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  disabled = false,
}) => {
  return (
    <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
      <div className="flex flex-col gap-2">
        <label htmlFor="start-date" className="font-medium text-slate-100 text-[0.9rem]">
          Start Dato:
        </label>
        <input
          id="start-date"
          type="date"
          className={dateInputClass}
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          disabled={disabled}
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="end-date" className="font-medium text-slate-100 text-[0.9rem]">
          Slut Dato:
        </label>
        <input
          id="end-date"
          type="date"
          className={dateInputClass}
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          min={startDate}
          disabled={disabled}
        />
      </div>
    </div>
  );
};

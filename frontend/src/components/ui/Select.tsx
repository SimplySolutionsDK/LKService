import React from 'react';
import clsx from 'clsx';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Array<{ value: string; label: string }>;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  className,
  ...props
}) => {
  return (
    <div className="mb-4 last:mb-0">
      {label && (
        <label className="block text-[0.85rem] font-medium mb-1.5 text-slate-400">
          {label}
        </label>
      )}
      <select
        className={clsx(
          'w-full py-2.5 px-3.5 bg-bg-secondary border border-border rounded-lg text-slate-100 font-sans text-[0.9rem] cursor-pointer transition-colors select-arrow hover:border-accent focus:border-accent focus:outline-none',
          className
        )}
        {...props}
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

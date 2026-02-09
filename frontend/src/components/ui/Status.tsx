import React from 'react';
import clsx from 'clsx';

interface StatusProps {
  type: 'success' | 'error' | 'loading';
  message: string;
}

const typeStyles: Record<string, string> = {
  success: 'bg-green-500/15 border-green-500 text-green-500',
  error: 'bg-red-500/15 border-red-500 text-red-500',
  loading: 'bg-blue-500/15 border-accent text-accent-light flex items-center justify-center gap-3',
};

export const Status: React.FC<StatusProps> = ({ type, message }) => {
  return (
    <div className={clsx(
      'p-3.5 rounded-[10px] mt-4 text-[0.9rem] border animate-fade-in',
      typeStyles[type]
    )}>
      {type === 'loading' && (
        <div className="w-[18px] h-[18px] border-2 border-transparent border-t-current rounded-full animate-spin" />
      )}
      <span>{message}</span>
    </div>
  );
};

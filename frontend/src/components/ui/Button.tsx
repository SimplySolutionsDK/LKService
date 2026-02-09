import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success';
  children: React.ReactNode;
}

const variantStyles: Record<string, string> = {
  primary:
    'bg-gradient-to-br from-accent to-indigo-500 text-white border-none shadow-[0_4px_15px_var(--color-accent-glow)] hover:enabled:-translate-y-0.5 hover:enabled:shadow-[0_6px_25px_var(--color-accent-glow)] disabled:opacity-50 disabled:cursor-not-allowed',
  secondary:
    'bg-bg-secondary text-slate-100 border border-border hover:bg-border',
  success:
    'bg-gradient-to-br from-green-500 to-green-600 text-white border-none shadow-[0_4px_15px_rgba(34,197,94,0.3)] hover:enabled:-translate-y-0.5 hover:enabled:shadow-[0_6px_25px_rgba(34,197,94,0.4)]',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  children,
  className,
  ...props
}) => {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 py-3 px-5 font-sans text-[0.9rem] font-semibold rounded-[10px] cursor-pointer transition-all w-full',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};

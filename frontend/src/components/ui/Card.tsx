import React from 'react';
import clsx from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className }) => {
  return (
    <div className={clsx(
      'bg-bg-card border border-border rounded-2xl p-6 transition-colors hover:border-accent h-fit',
      className
    )}>
      {children}
    </div>
  );
};

interface CardTitleProps {
  icon?: string;
  children: React.ReactNode;
}

export const CardTitle: React.FC<CardTitleProps> = ({ icon, children }) => {
  return (
    <h2 className="text-[1.1rem] font-semibold mb-5 flex items-center gap-2">
      {icon && <span className="text-accent-light">{icon}</span>}
      {children}
    </h2>
  );
};

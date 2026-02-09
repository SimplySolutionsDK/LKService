import React from 'react';
import clsx from 'clsx';
import type { TabType } from '../../types';

interface PreviewTabsProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

const baseTab = 'py-2 px-4 rounded-lg text-[0.85rem] font-medium cursor-pointer transition-all max-md:flex-1 max-md:text-center';

export const PreviewTabs: React.FC<PreviewTabsProps> = ({ activeTab, onTabChange }) => {
  return (
    <div className="flex gap-2 flex-wrap max-md:w-full">
      <button
        className={clsx(baseTab, activeTab === 'daily'
          ? 'bg-accent border border-accent text-white'
          : 'bg-bg-secondary border border-border text-slate-400 hover:border-accent hover:text-slate-100'
        )}
        onClick={() => onTabChange('daily')}
      >
        Daglig
      </button>
      <button
        className={clsx(baseTab, activeTab === 'weekly'
          ? 'bg-accent border border-accent text-white'
          : 'bg-bg-secondary border border-border text-slate-400 hover:border-accent hover:text-slate-100'
        )}
        onClick={() => onTabChange('weekly')}
      >
        Ugentlig
      </button>
    </div>
  );
};

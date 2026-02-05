import React from 'react';
import type { TabType } from '../../types';
import './PreviewTabs.css';

interface PreviewTabsProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export const PreviewTabs: React.FC<PreviewTabsProps> = ({ activeTab, onTabChange }) => {
  return (
    <div className="preview-tabs">
      <button
        className={`preview-tab ${activeTab === 'daily' ? 'active' : ''}`}
        onClick={() => onTabChange('daily')}
      >
        Daglig
      </button>
      <button
        className={`preview-tab ${activeTab === 'weekly' ? 'active' : ''}`}
        onClick={() => onTabChange('weekly')}
      >
        Ugentlig
      </button>
    </div>
  );
};

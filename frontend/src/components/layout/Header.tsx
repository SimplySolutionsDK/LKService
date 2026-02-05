import React from 'react';
import './Header.css';

export const Header: React.FC = () => {
  return (
    <header>
      <div className="logo">
        <div className="logo-icon">⏱</div>
        <h1>Tidsregistrering Parser</h1>
      </div>
      <p className="subtitle">Upload CSV-filer og få dem formateret med overtidsberegning</p>
    </header>
  );
};

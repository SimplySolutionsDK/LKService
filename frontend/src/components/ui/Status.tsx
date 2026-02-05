import React from 'react';
import './Status.css';

interface StatusProps {
  type: 'success' | 'error' | 'loading';
  message: string;
}

export const Status: React.FC<StatusProps> = ({ type, message }) => {
  return (
    <div className={`status ${type}`}>
      {type === 'loading' && <div className="spinner"></div>}
      <span>{message}</span>
    </div>
  );
};

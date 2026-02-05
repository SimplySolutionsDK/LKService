import React from 'react';
import './Card.css';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div className={`card ${className}`}>
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
    <h2 className="card-title">
      {icon && <span className="card-title-icon">{icon}</span>}
      {children}
    </h2>
  );
};

import React from 'react';

const TabBar = ({ currentTab, setCurrentTab, userData }) => {
  const tabs = [
    { id: 'profile', icon: '👤', label: 'Профиль' },
    ...(userData?.is_admin ? [{ id: 'add', icon: '➕', label: 'Начислить' }] : []),
    { id: 'info', icon: 'ℹ️', label: 'Инфо' }
  ];

  return (
    <div className="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab ${currentTab === tab.id ? 'active' : ''}`}
          onClick={() => setCurrentTab(tab.id)}
        >
          <div className="tab-icon">{tab.icon}</div>
          <div className="tab-label">{tab.label}</div>
        </button>
      ))}
    </div>
  );
};

export default TabBar;
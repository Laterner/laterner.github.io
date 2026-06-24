import React from 'react';

const BalanceCard = ({ userData }) => {
  if (!userData) {
    return (
      <div className="balance-card">
        <div>💰 Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="balance-card">
      <div className="balance-label">💰 Ваш баланс</div>
      <div className="balance-amount">{userData.balance || 0}</div>
      <div className="member-number">
        🆔 Номер участника: {userData.member_number || '—'}
      </div>
    </div>
  );
};

export default BalanceCard;
import React from 'react';

const ProfileInfo = ({ userData }) => {
  if (!userData) return null;

  return (
    <div className="card">
      <h3>👤 Личная информация</h3>
      <p><strong>Имя:</strong> {userData.first_name} {userData.last_name || ''}</p>
      <p><strong>Username:</strong> @{userData.username || 'не указан'}</p>
      <p><strong>Telegram ID:</strong> {userData.telegram_id}</p>
      {userData.is_admin && (
        <p style={{ color: '#4caf50' }}>👑 Администратор</p>
      )}
    </div>
  );
};

export default ProfileInfo;
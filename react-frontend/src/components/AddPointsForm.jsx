import React, { useState } from 'react';

const AddPointsForm = ({ userData }) => {
  const [memberNumber, setMemberNumber] = useState('');
  const [points, setPoints] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!memberNumber || !points) {
      setMessage({ text: 'Заполните все поля', type: 'error' });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/add-points', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Telegram-Init-Data': window.Telegram.WebApp.initData
        },
        body: JSON.stringify({
          member_number: memberNumber,
          amount: parseInt(points)
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage({ 
          text: `✅ Начислено ${points} баллов пользователю ${memberNumber}`, 
          type: 'success' 
        });
        setMemberNumber('');
        setPoints('');
      } else {
        setMessage({ text: data.error || 'Ошибка при начислении', type: 'error' });
      }
    } catch (error) {
      setMessage({ text: 'Ошибка сервера', type: 'error' });
    }
    setLoading(false);
    
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  if (!userData?.is_admin) {
    return (
      <div className="card" style={{ textAlign: 'center' }}>
        ⛔ У вас нет прав администратора для начисления баллов
      </div>
    );
  }

  return (
    <div className="card">
      <h2>➕ Начисление баллов</h2>
      <p className="hint">Введите номер участника и количество баллов</p>
      
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Номер участника (5 цифр)"
          value={memberNumber}
          onChange={(e) => setMemberNumber(e.target.value.replace(/\D/g, '').slice(0, 5))}
          maxLength="5"
        />
        
        <input
          type="number"
          placeholder="Количество баллов"
          value={points}
          onChange={(e) => setPoints(e.target.value)}
          min="1"
        />
        
        <button type="submit" disabled={loading}>
          {loading ? '⏳ Обработка...' : '✨ Начислить баллы'}
        </button>
        
        {message.text && (
          <div className={message.type === 'success' ? 'success' : 'error'}>
            {message.text}
          </div>
        )}
      </form>
    </div>
  );
};

export default AddPointsForm;
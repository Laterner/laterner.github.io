import React, { useState, useEffect } from 'react';
import BalanceCard from './components/BalanceCard';
import AddPointsForm from './components/AddPointsForm';
import ProfileInfo from './components/ProfileInfo';
import TabBar from './components/TabBar';
import { useTelegram } from './hooks/useTelegram';

function App() {
  const [currentTab, setCurrentTab] = useState('profile');
  const [userData, setUserData] = useState(null);
  const { tg, user } = useTelegram();

  useEffect(() => {
    // Получаем данные пользователя из API
    const fetchUserData = async () => {
      try {
        const response = await fetch('/api/user', {
          headers: {
            'X-Telegram-Init-Data': tg.initData
          }
        });
        const data = await response.json();
        if (data.success) {
          setUserData(data.user);
        }
      } catch (error) {
        console.error('Error fetching user data:', error);
      }
    };

    if (tg) {
      fetchUserData();
    }
  }, [tg]);

  const renderContent = () => {
    switch (currentTab) {
      case 'profile':
        return (
          <>
            <BalanceCard userData={userData} />
            <ProfileInfo userData={userData} />
          </>
        );
      case 'add':
        return <AddPointsForm userData={userData} />;
      case 'info':
        return <InfoTab />;
      default:
        return null;
    }
  };

  return (
    <div className="app">
      <div className="container">
        {renderContent()}
      </div>
      <TabBar currentTab={currentTab} setCurrentTab={setCurrentTab} userData={userData} />
    </div>
  );
}

function InfoTab() {
  return (
    <div className="card">
      <h2>ℹ️ О системе</h2>
      <p>• Каждый пользователь получает уникальный 5-значный номер</p>
      <p>• Баллы начисляются через админ-панель</p>
      <p>• Все транзакции сохраняются в БД</p>
    </div>
  );
}

export default App;
import { useEffect, useState } from 'react';

export const useTelegram = () => {
  const [tg, setTg] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Проверяем, что мы в Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
      const telegram = window.Telegram.WebApp;
      telegram.expand();
      telegram.ready();
      
      setTg(telegram);
      
      if (telegram.initDataUnsafe && telegram.initDataUnsafe.user) {
        setUser(telegram.initDataUnsafe.user);
      }
    }
  }, []);

  return { tg, user };
};
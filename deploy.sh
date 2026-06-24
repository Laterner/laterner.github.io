# Создаём директорию для сайта
sudo mkdir -p /var/www/fstbot.ru/static

# Копируем ваш index.html и другие файлы
sudo cp -r ~/static/* /var/www/fstbot.ru/static/

# Копируем index.html в корень (чтобы был доступен по /)
# sudo cp /var/www/fstbot.ru/static/index.html /var/www/fstbot.ru/

# Копируем код бота
sudo mkdir -p /opt/fstbot
sudo cp -r ~/laterner.github.io/* /opt/fstbot/
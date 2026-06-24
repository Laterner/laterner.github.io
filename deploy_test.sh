#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Деплой сайта fstbot.ru ===${NC}"

# Проверяем, запущен ли скрипт с правами суперпользователя
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Пожалуйста, запустите скрипт с правами суперпользователя (sudo)${NC}"
    exit 1
fi

# Пути
STATIC_DIR="./static"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
DOMAIN="fstbot.ru"
NGINX_CONF="$NGINX_SITES/$DOMAIN.conf"

# Проверяем наличие папки static
if [ ! -d "$STATIC_DIR" ]; then
    echo -e "${RED}Папка static не найдена!${NC}"
    echo -e "${YELLOW}Создаю папку static...${NC}"
    mkdir -p "$STATIC_DIR"
fi

# Проверяем наличие index.html в папке static
if [ ! -f "$STATIC_DIR/index.html" ]; then
    echo -e "${RED}Файл index.html не найден в папке static!${NC}"
    echo -e "${YELLOW}Копирую заглушку в папку static...${NC}"
    # Создаем простую заглушку, если файла нет
    cat > "$STATIC_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html>
<head><title>fstbot.ru</title></head>
<body>
    <h1>Сайт в разработке</h1>
    <p>Скоро здесь появится контент</p>
</body>
</html>
EOF
fi

echo -e "${GREEN}✓ Файлы найдены${NC}"

# Создаем конфигурацию nginx
echo -e "${YELLOW}Создаю конфигурацию nginx...${NC}"

cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    listen [::]:80;
    
    server_name $DOMAIN www.$DOMAIN;
    
    root $(pwd)/$STATIC_DIR;
    index index.html;
    
    location / {
        try_files \$uri \$uri/ =404;
    }
    
    # Логи
    access_log /var/log/nginx/$DOMAIN-access.log;
    error_log /var/log/nginx/$DOMAIN-error.log;
}
EOF

echo -e "${GREEN}✓ Конфигурация создана: $NGINX_CONF${NC}"

# Активируем сайт
echo -e "${YELLOW}Активирую сайт...${NC}"

# Удаляем старую ссылку, если есть
if [ -L "$NGINX_ENABLED/$DOMAIN.conf" ]; then
    rm "$NGINX_ENABLED/$DOMAIN.conf"
fi

# Создаем новую ссылку
ln -s "$NGINX_CONF" "$NGINX_ENABLED/"

echo -e "${GREEN}✓ Сайт активирован${NC}"

# Проверяем конфигурацию nginx
echo -e "${YELLOW}Проверяю конфигурацию nginx...${NC}"

if nginx -t; then
    echo -e "${GREEN}✓ Конфигурация корректна${NC}"
    
    # Перезапускаем nginx
    echo -e "${YELLOW}Перезапускаю nginx...${NC}"
    
    if systemctl restart nginx; then
        echo -e "${GREEN}✓ Nginx успешно перезапущен${NC}"
    else
        echo -e "${RED}Ошибка при перезапуске nginx${NC}"
        echo -e "${YELLOW}Попытка перезапустить через service...${NC}"
        service nginx restart
    fi
    
    echo -e "${GREEN}=== Деплой завершен успешно! ===${NC}"
    echo -e "${GREEN}Сайт доступен по адресу: http://$DOMAIN${NC}"
else
    echo -e "${RED}Ошибка в конфигурации nginx!${NC}"
    echo -e "${YELLOW}Проверьте файл: $NGINX_CONF${NC}"
    exit 1
fi
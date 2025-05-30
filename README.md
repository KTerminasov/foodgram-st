## Запуск проекта через Docker

1. Установите и запустите докер.
2. Клонируйте репозитарий проекта.
3. В корне проекта создайте файл .env, указав в нем следующие переменные:
```
  POSTGRES_USER=
  POSTGRES_PASSWORD=
  POSTGRES_DB=
  
  DB_HOST=
  DB_PORT=
```
4. Перейдите в папку infra и выполните команды:
```
docker compose -f docker-compose.yml up
docker compose -f docker-compose.yml exec backend python manage.py migrate
docker compose -f docker-compose.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

## Подгрузка данных.
В папке data/ содержатся фикстуры ingridients.json с ингридиентами и test_data.json с несколькими созданными пользователями и рецептами.

1. Скопировать нужный файл с данными в контейнер.
```
docker compose -f docker-compose.yml cp data/нужный_файл.json backend:/app/test_data.json
```
2. Загрузить данные из фикстуры.
```
docker compose -f docker-compose.yml exec backend python manage.py loaddata нужный_файл.json
```
   

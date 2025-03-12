# Система алертов
Проект детектирования аномальных изменений данных о работе приложения и отправке оповещений в чат-бот с использованием Airflow.

## Задача 

База в Clickhouse пополняется в режиме реального времени данными об активности пользователей в приложении (просмотр ленты новостей и отправка сообщений). Необходимо реализовать алгоритм, который каждые 15 минут будет оценивать основные показатели и определять, допустимы ли изменения этих показателей. В случае значительных отклонений должна быть предусмотрена отправка уведомления в чат Telegram.

### Подробнее о данных

Данные об активности в ленте содержатся в таблице feed_actions со следующими полями:

|user_id|post_id|action|time               |gender|age|country|city            |os     |source |exp_group|
|-------|-------|------|-------------------|------|---|-------|----------------|-------|-------|---------|
|123767 |2040   |view  |29/06/24 20:06     |1     |21 |Russia |Samara          |Android|organic|1        |
|129655 |2116   |like  |29/06/24 20:06     |0     |26 |Russia |Saint Petersburg|iOS    |organic|4        |

Данные об активности в мессенджере содержатся в таблице message_actions со следующими полями:

|user_id|receiver_id|time  |source             |exp_group|gender|age    |country         |city   |os     |
|-------|-----------|------|-------------------|---------|------|-------|----------------|-------|-------|
|3829   |121735     |20/08/24 15:20|ads                |2        |1     |42     |Russia          |Moscow |iOS    |
|12802  |129537     |20/08/24 15:20|ads                |3        |1     |14     |Russia          |Gelendzhik|iOS

### Определение допустимых значений для метрик

Основные показатели работы ленты новостей - это число уникальных пользователей, количество просмотров и  количество лайков.

Основные показатели работы мессенджера - это число уникальных пользователей и количество сообщений.

Колебания метрик в течение недели в SUPERSET:

![лента-новостей-показатели-активности-2025-03-11T08-36-15 328Z](https://github.com/user-attachments/assets/7e16060f-2473-4ccd-971d-0e9ca7c4cc84)

За исключением локального пика ярко выраженной зависимости активности от дня недели не обнаруживается. Наблюдается сезонность в течение дня.

Колебания метрик в течение дня в SUPERSET:

![лента-новостей-показатели-активности-2025-03-11T08-36-54 657Z](https://github.com/user-attachments/assets/a817d3c2-a51c-4c2e-b74a-7d1f6ee6bdac)

Таким образом, при расчете допустимого интервала необходимо изменения метрики в течение дня. 
Схематично алгоритм расчета границ показан на картинках ниже:
![МКР](https://github.com/user-attachments/assets/36e9fbc3-b636-4e89-ba63-7943b8ccd6f4)

![Сглаживание МКР](https://github.com/user-attachments/assets/26addbca-6923-4b5c-9da5-04106cc54df4)

Рассчитав границы допустимого интервала, функция check_anomaly_feed сравнивает последнее значение метрики в датафрейме с граничными значениями и, в случае выхода за пределы интервала, присваивает флагу is_alert значение 1.

Далее функция run_alerts при is_alert == 1 формирует сообщение вида: 

Метрика like:1262

отклонение от последнего значения: 20,02%

![1741795441603](https://github.com/user-attachments/assets/dbba4d18-c391-41d0-a0ce-6cac12845bb1)

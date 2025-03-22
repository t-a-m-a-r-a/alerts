# Система алертов
Проект детектирования аномальных изменений данных о работе приложения и отправке оповещений в чат-бот с использованием Airflow.

### Контекст

База в Clickhouse пополняется в режиме реального времени данными об активности пользователей в приложении (просмотр ленты новостей и отправка сообщений). Необходимо реализовать алгоритм, который каждые 15 минут будет оценивать основные показатели и определять, допустимы ли изменения этих показателей. В случае значительных отклонений должна быть предусмотрена отправка уведомления в чат Telegram.

### Стек проекта

![Python](https://img.shields.io/badge/-Python-75A8D3?style=flat-square&logo=Python&logoColor=white)
![SQL](https://img.shields.io/badge/-SQL-326690?style=flat-square&logo=SQL&logoColor=white)
![Clickhouse](https://img.shields.io/badge/-Clickhouse-151515?style=flat-square&logo=Clickhouse&logoColor=white)
![Superset](https://img.shields.io/badge/-Superset-151515?style=flat-square&logo=Superset&logoColor=white)
![Airflow](https://img.shields.io/badge/-Airflow-B7472A?style=flat-square&logo=Airflow&logoColor=white)

## Решение 

### Данные

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


### Шаг 1
Проанализировала колебания метрик в SUPERSET, выявила дневную сезонность, которую необходимо учесть при расчете допустимого интервала для метрик.
Колебания в течение недели:

![лента-новостей-показатели-активности-2025-03-11T08-36-15 328Z](https://github.com/user-attachments/assets/7e16060f-2473-4ccd-971d-0e9ca7c4cc84)

Колебания в течение дня:

![лента-новостей-показатели-активности-2025-03-11T08-36-54 657Z](https://github.com/user-attachments/assets/a817d3c2-a51c-4c2e-b74a-7d1f6ee6bdac)

### Шаг 2

Рассчитала допустимый интервал для каждой метрики с помощью метода межквартильного размаха.

Схематично о методе:

![МКР](https://github.com/user-attachments/assets/36e9fbc3-b636-4e89-ba63-7943b8ccd6f4)

![Сглаживание МКР](https://github.com/user-attachments/assets/26addbca-6923-4b5c-9da5-04106cc54df4)
 
### Шаг 3

Создала скрипт, который рассчитывает для текущего значения метрики допустимые границы, сравнивает и в случае выхода за пределы границ формирует сообщение с численными значениями метрики и графиком.
Настроила запуск скрипта каждые 15 минут с помощью Airflow.

## Результат 

Чат бот в случае алерта в режиме реального времени присылает сообщение вида: 

Метрика like: 1262

отклонение от последнего значения: 20,02%

![1741795441603](https://github.com/user-attachments/assets/dbba4d18-c391-41d0-a0ce-6cac12845bb1)

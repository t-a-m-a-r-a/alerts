import pandas as pd
import telegram
import pandahouse as ph
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date, datetime, timedelta
import io
import sys
import os

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

my_token = '7207649694:AAFGlqUj0K5N1QrfSLYaArbJaWx90W4vb2w'
bot = telegram.Bot(token=my_token) # получаем доступ

connection = {'host': 'https://clickhouse.lab.karpov.courses',
'database':'simulator_20240720',
'user':'student',
'password':'dpo_python_2020'
}

# Дефолтные параметры, которые прокидываются в таски
default_args = {
    'owner': 't.shashkina',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 9, 4),
}

# Интервал запуска DAG
schedule_interval = '*/15 * * * *'

def check_anomaly_feed(df, metric, a=5, n=5):
    df['q25'] = df[metric].shift(1).rolling(n).quantile(0.25)
    df['q75'] = df[metric].shift(1).rolling(n).quantile(0.75)
    df['iqr'] = df['q75'] - df['q25']
    df['up'] = df['q75'] + a* df['iqr']
    df['low'] = df['q25'] - a* df['iqr']
    
    df['up'] = df['up'].rolling(n+1, center=True, min_periods=1).mean()
    df['low'] = df['low'].rolling(n+1, center=True, min_periods=1).mean()
    
    if df[metric].iloc[-1] < df['low'].iloc[-1] or df[metric].iloc[-1] > df['up'].iloc[-1]: 
        is_alert = 1
    else:
        is_alert = 0
   
    return is_alert, df

def check_anomaly_message(df, metric, a=3, n=6):
    df['q25'] = df[metric].shift(1).rolling(n).quantile(0.25)
    df['q75'] = df[metric].shift(1).rolling(n).quantile(0.75)
    df['iqr'] = df['q75'] - df['q25']
    df['up'] = df['q75'] + a* df['iqr']
    df['low'] = df['q25'] - a* df['iqr']
    
    df['up'] = df['up'].rolling(n+1, center=True, min_periods=1).mean()
    df['low'] = df['low'].rolling(n+1, center=True, min_periods=1).mean()
    
    if df[metric].iloc[-1] < df['low'].iloc[-1] or df[metric].iloc[-1] > df['up'].iloc[-1]: 
        is_alert = 1
    else:
        is_alert = 0
   
    return is_alert, df

def make_alert(chat=None):
    chat_id = chat or 1338994141
    my_token = '7207649694:AAFGlqUj0K5N1QrfSLYaArbJaWx90W4vb2w'
    bot = telegram.Bot(token=my_token) # получаем доступ
    
    query = """SELECT ts, date, hm, users_feed, views, likes, CTR, users_message, messages
                FROM
                    (SELECT
                        toStartOfFifteenMinutes(time) as ts,
                        toDate(ts) as date,
                        formatDateTime(ts, '%R') as hm,
                        uniqExact(user_id) as users_feed,
                        countIf(action='view') as views,
                        countIf(action='like') as likes,
                        countIf(action='like') / countIf(action='view') as CTR
                    FROM simulator_20240720.feed_actions
                    WHERE ts >=  today() - 1 and ts < toStartOfFifteenMinutes(now())
                    GROUP BY ts, date, hm
                    )t1
                FULL JOIN
                    (SELECT
                        toStartOfFifteenMinutes(time) as ts,
                        toDate(ts) as date,
                        formatDateTime(ts, '%R') as hm,
                        uniqExact(user_id) as users_message,
                        count(receiver_id) as messages
                    FROM simulator_20240720.message_actions
                    WHERE ts >=  today() - 1 and ts < toStartOfFifteenMinutes(now())
                    GROUP BY ts, date, hm
                    )t2
                USING (ts, date, hm)
                ORDER BY ts"""
    data = ph.read_clickhouse(query, connection=connection)
    
    metrics_feed_list = ['users_feed', 'views', 'likes']
    metrics_message_list = [ 'CTR', 'users_message', 'messages']

    for metric in metrics_feed_list:
        # print(metric)
        df = data[['ts','date','hm', metric]].copy()
        is_alert, df = check_anomaly_feed(df, metric)
        
        if is_alert == 1:
            msg = ''' Метрика {metric}:\nтекущее значение {current_val:.2f}\nотклонение от последнего значения {last_val_diff:.2%}'''.format(metric=metric,
                                                                                                                                              current_val=df[metric].iloc[-1],
                                                                                                                                              last_val_diff=abs(1 - df[metric].iloc[-1]/df[metric].iloc[-2]))
            sns.set(rc={'figure.figsize' : (16,10)})
            plt.tight_layout()
            
            ax = sns.lineplot(x=df['ts'], y=df[metric], label='metric')
            ax = sns.lineplot(x=df['ts'], y=df['up'], label='up')
            ax = sns.lineplot(x=df['ts'], y=df['low'], label='low')
            
            for ind, label in enumerate(ax.get_xticklabels()):
                if ind % 2 == 0:
                    label.set_visible(True)
                else:
                    label.set_visible(False)
                    
            ax.set(xlabel='time')
            ax.set(ylabel=metric)
            
            ax.set_title(metric)
            ax.set(ylim=(0, None))
                    
            plot_object = io.BytesIO()
            ax.figure.savefig(plot_object)
            plot_object.seek(0)
            plot_object.name = '{0}.png'.format(metric)
            plt.close()
            
            bot.sendMessage(chat_id=chat_id, text=msg)
            bot.sendPhoto(chat_id=chat_id, photo=plot_object)
        
    for metric in metrics_message_list:
        # print(metric)
        df = data[['ts','date','hm', metric]].copy()
        is_alert, df = check_anomaly_message(df, metric)
        
        if is_alert == 1:
            msg = ''' Метрика {metric}:\nтекущее значение {current_val:.2f}\nотклонение от последнего значения {last_val_diff:.2%}'''.format(metric=metric,
                                                                                                                                              current_val=df[metric].iloc[-1],
                                                                                                                                              last_val_diff=abs(1 - df[metric].iloc[-1]/df[metric].iloc[-2]))
            sns.set(rc={'figure.figsize' : (16,10)})
            plt.tight_layout()
            
            ax = sns.lineplot(x=df['ts'], y=df[metric], label='metric')
            ax = sns.lineplot(x=df['ts'], y=df['up'], label='up')
            ax = sns.lineplot(x=df['ts'], y=df['low'], label='low')
            
            for ind, label in enumerate(ax.get_xticklabels()):
                if ind % 2 == 0:
                    label.set_visible(True)
                else:
                    label.set_visible(False)
                    
            ax.set(xlabel='time')
            ax.set(ylabel=metric)
            
            ax.set_title(metric)
            ax.set(ylim=(0, None))
                    
            plot_object = io.BytesIO()
            ax.figure.savefig(plot_object)
            plot_object.seek(0)
            plot_object.name = '{0}.png'.format(metric)
            plt.close()
            
            bot.sendMessage(chat_id=chat_id, text=msg)
            bot.sendPhoto(chat_id=chat_id, photo=plot_object)
    
    return


@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def dag_shashkina_feed_message_alert_to_bot():
          
    @task()
    def feed_message_alert_to_bot():
        make_alert(-969316925)
        
    feed_message_alert_to_bot()
        
dag_shashkina_feed_message_alert_to_bot = dag_shashkina_feed_message_alert_to_bot()
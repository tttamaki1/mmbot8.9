


#Timestamp for this request is outside of the recvWindow.
#↑PCの時計がずれている
#ntp.nict.jpからインターネット経由での時刻配信を受信
#タスクスケジューラで設定する

# -*- coding: utf-8 -*-

#API制限　20req/秒　→　0.05sec/req
import pandas as pd
import datetime
import time
import ccxt
from pprint import pprint
import numpy as np
import math
import talib
import mplfinance as mpf
import threading
from binance.client import Client
#import nest_asyncio
#nest_asyncio.apply()
import warnings
warnings.simplefilter('ignore')


#------------------------------------------------------------------------------#
#log設定
import logging
logger = logging.getLogger('LoggingTest')
logger.setLevel(10)
fh = logging.FileHandler('log_mm_bf.log')
logger.addHandler(fh)
sh = logging.StreamHandler()
logger.addHandler(sh)
formatter = logging.Formatter('%(asctime)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
sh.setFormatter(formatter)

#------------------------------------------------------------------------------#

mc = mpf.make_marketcolors(up='#0821C7', down='#C70808', volume='#F2C84B', 
    edge='#F2CED1', wick={'up':'#049DBF', 'down':'#D93D4A'}) 
cs  = mpf.make_mpf_style(marketcolors=mc, gridcolor="lightgray")

binance_api_key = 
binance_api_secret = 

binance = ccxt.binance({'apiKey': str(binance_api_key),'secret': str(binance_api_secret),})

client = Client(binance_api_key, binance_api_secret)

binance_base = ccxt.binance()

percent = 0
y_percent = []
x_time = []
price_list = []
position_size = 0
price = 0

FIAT = 'USDT'
symbol = "BTCUSDT"
symbol2 = "BTC/USD"

CYCLE = 3#何秒周期でBOTを回すか
atr_time_period = 6
EFFECT = 1.1

def fetch_ticker(symbol,base):
    value = []
    while value == []: 
        try:
            value = base.fetch_ticker(symbol=symbol)
        except Exception as e:
            time.sleep(0.2)
            print('Exception Messege : {}'.format(e))
    price = float(value['last'])       

    return price

def get_kline(symbol):
            
    kline = []
    while len(kline) == 0:
        try:
            kline =  binance_base.fetch_ohlcv(symbol=symbol,     # 暗号資産[通貨]
                           timeframe = '1m',    # 時間足('1m', '5m', '1h', '1d')
                           since=None,           # 取得開始時刻(Unix Timeミリ秒)
                           limit=26,           # 取得件数(デフォルト:100、最大:500)
                           params={}             # 各種パラメータ
                          )
            
        except Exception as e:
            time.sleep(0.01)
            logger.info(e)


    # DataFrameに突っ込む各列のデータを切り出す
    date=[] 
    open=[]
    high=[]
    low=[]
    close=[]
    volume = []
    for i in kline:
        date.append(i[0])
        open.append(i[1])
        high.append(i[2])
        low.append(i[3])
        close.append(i[4])
        volume.append(i[5])

    df=pd.DataFrame({"date":date, "open":open, "high":high, "low":low, "close":close, 'volume':volume})
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)# indexをdateに設定
    df['open'] = pd.to_numeric(df['open']) 
    df['high'] = pd.to_numeric(df['high']) 
    df['low'] = pd.to_numeric(df['low']) 
    df['close'] = pd.to_numeric(df['close']) 
    df['volume'] = pd.to_numeric(df['volume']) 
    
    return df 
     
def get_chart(df_3s_ohlcv,t):

    binance_trades_info = []
    while len(binance_trades_info) == 0:
        try:
            binance_trades_info = binance_base.fetch_trades(symbol=symbol, limit=750)
        except Exception as e:
           time.sleep(0.2)
           logger.info(e)
           pass
    
    lst_trades = [[t["timestamp"], t["side"], t["amount"], t["price"]] for t in binance_trades_info]
    df = pd.DataFrame(lst_trades, columns=["timestamp", "side", "amount", "price"])

    #df['timestamp'] = df['timestamp']+32400000
    s = t * 1000
    #s = df['timestamp'].iloc[-1]
    #print(str(t-s))
    df = df[df['timestamp'] > s - CYCLE * 1000]
    #print(t)
    #print(df['timestamp'].iloc[-1])
    tick = len(df)
    #print(tick)
    
    df['buy_total'] = df['amount'][df['side']=='buy'].sum()
    df['sell_total'] = df['amount'][df['side']=='sell'].sum()
      
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df = df.set_index("timestamp")
 
    new_df_ohlcv_3s = df.resample(str(CYCLE) + "S").agg({"price" : "ohlc","amount"  : "sum",}).ffill()
    
    new_df_ohlcv_3s.columns = ["open", "high", "low", "close", "volume",]

    new_df_ohlcv_3s['buy_total'] = 0
    new_df_ohlcv_3s['sell_total'] = 0
    new_df_ohlcv_3s['buy_total'] = df['buy_total'].iloc[-1]
    new_df_ohlcv_3s['sell_total'] = df['sell_total'].iloc[-1]
    
    if len(df_3s_ohlcv) == 0:
        df_3s_ohlcv = df_3s_ohlcv.append(new_df_ohlcv_3s.iloc[-1])
    else:   
        df_3s_ohlcv = df_3s_ohlcv.append(new_df_ohlcv_3s.iloc[-1])
          
    if len(df_3s_ohlcv) > 50:    
        df_3s_ohlcv = df_3s_ohlcv[1:]

    return df_3s_ohlcv,tick

def get_info(symbol,df_3s_ohlcv,t):
    
    df_3s_ohlcv,tick = get_chart(df_3s_ohlcv,t)
    #tick = df_3s_ohlcv['tick'].iloc[-1]
    
    #open = df_3s_ohlcv['open']
    high = df_3s_ohlcv['high']
    low = df_3s_ohlcv['low']
    close = df_3s_ohlcv['close']
    volume = df_3s_ohlcv['volume']
 
    df_3s_ohlcv['ATR'] = talib.ATR(high, low, close, timeperiod=atr_time_period) 
    df_3s_ohlcv['volume_EMA'] = talib.EMA(volume, timeperiod=10)
    atr = df_3s_ohlcv['ATR'].iloc[-1]

    if len(df_3s_ohlcv) >= 15: 
        df_3s_ohlcv['lowest'] =  df_3s_ohlcv['close'].rolling(15).min()
        lowest = df_3s_ohlcv['lowest'].iloc[-1]    
    else:
        lowest = 0 

    
    if len(df_3s_ohlcv) > 5:
        
        df_3s_ohlcv['buy_total_mean'] = df_3s_ohlcv['buy_total'].rolling(5).mean()
        df_3s_ohlcv['sell_total_mean'] = df_3s_ohlcv['sell_total'].rolling(5).mean()
        buy_total_mean = float(df_3s_ohlcv['buy_total_mean'].iloc[-1])
        sell_total_mean = float(df_3s_ohlcv['sell_total_mean'].iloc[-1]) 
        
    else:
        buy_total_mean = 0
        sell_total_mean = 0
     
    volume_30s = df_3s_ohlcv['volume_EMA'].iloc[-1]
    
    kline_df = get_kline(symbol)
    
    close = kline_df['close']
    kline_df['ema5'] = talib.EMA(close, timeperiod=5)
    kline_df['ema4'] = talib.EMA(close, timeperiod=4)
    kline_df['ema3'] = talib.EMA(close, timeperiod=3)
    
    ema5 = kline_df['ema5'].iloc[-1]
    
    ema5_ratio = ema5 / kline_df['ema5'][len(kline_df)-2]
 
    price = kline_df['close'].iloc[-1]   
 
    disparity = (price - ema5) / ema5 * 100
    
    boost_atr = 1.2445* math.exp(0.2871*atr) 
        
    delta = boost_atr * 1.2
    

    return price, atr,boost_atr,delta,volume_30s, tick,disparity,df_3s_ohlcv,kline_df,buy_total_mean,sell_total_mean,lowest,ema5_ratio


def limit(symbol,side, size, order_price):# 指値注文する関数

    if side == 'buy':
        #trailingDelta = 3 #0.03%
        #params = {'trailingDelta': trailingDelta }
        try:
            binance.createOrder(symbol=symbol, type='limit', side='buy', amount=size, price=order_price)
        except Exception as e:
            time.sleep(0.2)
            logger.info(e)  
        
    else:

        #trailingDelta = 3 
        #stopPrice = order_price-order_price*0.0006
        #params = {'stopPrice': stopPrice }
        try:
            binance.createOrder(symbol=symbol, type='limit', side='sell', amount=size, price=order_price)#, params)
            #value = binance.create_order(symbol=symbol, type = 'limit', side = side, amount = size, price = price)
        except Exception as e:
            time.sleep(0.2)
            logger.info(e)        


def market(symbol,side, size):# 成行注文する関数

    try:
        binance.create_order(symbol=symbol, type='market', side=side, amount=size)
    except:
        pass
 
def cancel(symbol,id):# 注文をキャンセルする関数

    try:
        binance.cancelOrder(symbol = symbol, id = id)
    except Exception as e:
        time.sleep(0.2)
        #logger.info(e)


def cancel_all_order(symbol,sell_order_amount,buy_order_amount,sell_order_id,buy_order_id,position_size,amount_min):
    
    while sell_order_amount > 0 or buy_order_amount > 0 or position_size > 0:
        if sell_order_amount > 0 or buy_order_amount > 0:
            try:
               client._delete('openOrders', True, data={'symbol': symbol})
               time.sleep(0.1)
            except:
                pass
            
        if position_size > 0:
           if position_size< amount_min  * 1.1:
                market(symbol,'buy', amount_min+ 0.0006)
                time.sleep(0.1)
                market(symbol,'sell', position_size)
                time.sleep(0.1)
           else:    
                market(symbol,'sell', position_size) 
                time.sleep(0.1)
             
        buy_order_amount,buy_order_id,sell_order_amount,sell_order_id = fetch_open_orders()
        position_size,available_balance,used_amount = get_asset(client,'BTC',FIAT)
          
    return position_size,buy_order_amount,sell_order_amount

def get_asset(client,coin,FIAT):
    
    value = []
    while value == []:
        try:
            value = client.get_asset_balance(asset=coin)
        except Exception as e:
            time.sleep(0.05)
            print('Exception Messege : {}'.format(e))
        
    position_size = float(value['free'])  + float(value["locked"])
    
    value = [] 
    while value == []: 

        try:
            value = client.get_asset_balance(asset=FIAT)
            
        except Exception as e:
            time.sleep(0.05)
            print('Exception Messege : {}'.format(e))    
        
    available_balance = float(value['free'])
    used_amount = float(value["locked"] ) 
        
    return position_size,available_balance,used_amount

def fetch_open_orders():

    buy_order_amount = 0
    sell_order_amount = 0
    buy_order_id = ''
    sell_order_id = ''
    try:
        orders = binance.fetchOpenOrders(symbol)
        #pprint(orders)
        for i, x in enumerate(orders):
            if orders[i]['side'] == 'buy':
                buy_order_amount = orders[i]['amount']
                buy_order_id = orders[i]['id']
                
            if orders[i]['side'] == 'sell':
                sell_order_amount = orders[i]['amount']
                sell_order_id = orders[i]['id']       
    except Exception as e:
        time.sleep(0.1)
        logger.info(e)
        return 0, '',0,''
       
    return buy_order_amount,buy_order_id,sell_order_amount,sell_order_id      

def fetch_best_orderprice(symbol,buy_price,sell_price,volume_30s,buy_total_mean,sell_total_mean):
    
    new_buy_order_price = 0
    new_sell_order_price = 0
    result_1 = ''
    result_2 = ''
    total_bid = 0
    total_ask = 0
      
    orderbook = []
    params = {'limit': 500}
    while len(orderbook) == 0:
        try:
            orderbook = binance_base.fetchOrderBook(symbol=symbol,params=params)   
        except Exception as e:
            time.sleep(0.1)
            logger.info(e)
    
    
    for i ,x in enumerate(orderbook['bids']):
        total_bid += float(orderbook['bids'][i][1])

        if float(orderbook['bids'][i][0]) < buy_price:
            break

        if total_bid > sell_total_mean: #板の指値の量が、sellの量を上回った時に、
           new_buy_order_price = float(orderbook['bids'][i-1][0]+0.04)
           result_1 = 'b:' + '{:.2f}'.format(buy_price) + '　→　' + '{:.2f}'.format(new_buy_order_price)
           total_bid = -1
           break
       
    for i ,x in enumerate(orderbook['asks']):
        total_ask += float(orderbook['asks'][i][1])

        if float(orderbook['asks'][i][0]) > sell_price:
            break

        if total_ask > buy_total_mean:
           new_sell_order_price = float(orderbook['asks'][i-1][0]+0.04)
           result_2 = 's:' + '{:.2f}'.format(sell_price) + '　→　' +'{:.2f}'.format(new_sell_order_price)
           total_ask = -1
           break       
            
    if new_buy_order_price == 0:
        new_buy_order_price = buy_price
             
    if new_sell_order_price == 0:
        new_sell_order_price = sell_price
     
               
    return new_buy_order_price,new_sell_order_price, result_1,result_2,total_bid,total_ask

def main():

    li = []
    position_size = 0
    
    price = fetch_ticker(symbol=symbol,base=binance_base)
    position_size,available_balance,used_amount = get_asset(client,'BTC',FIAT)  
    order_lot = round(available_balance/price * 0.245,4)
    #order_lot = 0.0005
    max_lot = order_lot * 4
    
    buy_order_price = price
    sell_order_price = price
    buy_order_amount = 0
    sell_order_amount = 0
    trade_start = 0
    pause_til = 0
    last_sell_order_amount = 0
    timeout_count = 0
    
    isPausing = False
    df_3s_ohlcv = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    start = time.time()

    while True:
        
        t = int(time.time())
    
        if t % CYCLE == 0 and start + CYCLE < time.time():

            start = time.time()
            
            buy_order_amount,buy_order_id,sell_order_amount,sell_order_id = fetch_open_orders() #0.025s
            
            price, atr,boost_atr,delta,volume_30s, tick,disparity,df_3s_ohlcv,kline_df,buy_total_mean,sell_total_mean,lowest,ema5_ratio = get_info(symbol,df_3s_ohlcv,t)

            amount_min = 10/(price+0.0004*price)#10@24000

            last_close = kline_df['close'].iloc[-2]


            if price < last_close - atr :
                while not (buy_order_amount == 0 and sell_order_amount == 0 and position_size == 0): 
                    #cancel_all_order
                    position_size,buy_order_amount,sell_order_amount = cancel_all_order(symbol,sell_order_amount,buy_order_amount,sell_order_id,buy_order_id,position_size,amount_min)
                    time.sleep(0.1)
                    position_size,available_balance,used_amount = get_asset(client,'BTC',FIAT)
                    buy_order_amount,buy_order_id,sell_order_amount,sell_order_id = fetch_open_orders()
                    
     
            if np.isnan(atr) == False:                       
                trade_start = 1     
 
            if len(y_percent) < 30:      
                x_time.insert(len(x_time) - 1,time.time())
                price_list.insert(len(price_list) - 1,price)
            else: 
                del y_percent[0]
                del x_time[0]
                del price_list[0]
                x_time.append(time.time())

                price_list.append(price)
                           
          
            position_size,available_balance,used_amount = get_asset(client,'BTC',FIAT) #0.03s    
                
            delta = boost_atr * EFFECT
            if position_size == 0:
                s_offset = 0
            else:
                s_offset = delta * position_size / max_lot #position_sizeが大きいほど、offsetがおおきくなる
      
                
            volume_30s_threshold = 1.25
            
            disparity_threshold = 0.091 #9%
  
            buy_order_price = price - delta - s_offset 
            sell_order_price = price + delta - s_offset
   
            buy_order_price,sell_order_price, result_1,result_2,total_bid,total_ask = fetch_best_orderprice(symbol,buy_order_price,sell_order_price,volume_30s,buy_total_mean,sell_total_mean)
            
            if len( df_3s_ohlcv) > atr:
 
                if sell_order_amount > 0:
                    if (last_sell_order_amount== 0):
                        timeout_count += 1     
                    elif sell_order_amount == last_sell_order_amount:
                        timeout_count += 1
                    elif sell_order_amount > last_sell_order_amount:
                        timeout_count = 0
                    else:
                        timeout_count = 0
                    last_sell_order_amount = sell_order_amount     
                else: 
                    timeout_count = 0 
                #print(timeout_count)    
    
                #total_worth = (available_balance + used_amount + position_size * price)  / price

                if position_size <= max_lot/4:
                    count = 5
                elif position_size <= max_lot*2/4:
                    count = 4
                elif position_size <= max_lot*3/4:
                    count = 3
                elif position_size <= max_lot*4/4:
                    count = 2               

                #d = df_3s_ohlcv['close'].iloc[-1] / df_3s_ohlcv['close'].iloc[-5] 
                        
                if (atr/price > 0.00074
                    or time.time() < pause_til
                    or price < last_close - 0.000208*price #5@24000
                    or (total_bid != -1 and total_bid < 0.4)
                    or (timeout_count >= count)):

                    while not (buy_order_amount == 0 and sell_order_amount == 0 and position_size == 0): 
                        #cancel_all_order
                        position_size,buy_order_amount,sell_order_amount = cancel_all_order(symbol,sell_order_amount,buy_order_amount,sell_order_id,buy_order_id,position_size,amount_min)
                        time.sleep(0.5)
                        position_size,available_balance,used_amount = get_asset(client,'BTC',FIAT)
                        

                    if atr/price > 0.00074: #23740でatrが45
                    
                        duration = 30
                        pause_til = int(time.time() + duration)
                        print('PAUSE UNTIL ' + str(datetime.datetime.fromtimestamp(pause_til)))
                        
                    if timeout_count >= count and position_size == 0:
                            print('TIME　OUT')
                            timeout_count = 0
                            
                    if price < last_close:
                        pause_til = int(time.time() + 9)
             
            if trade_start == 1 and isPausing == False:

                order_lot = round(available_balance/price * 0.245,4)
                #order_lot = 0.0005
                max_lot = order_lot * 4  
    
                #BUY
                if (time.time() > pause_til
                    and order_lot <= max_lot - position_size
                    and volume_30s > volume_30s_threshold
                    and disparity < disparity_threshold
                    and buy_order_price > lowest
                    and buy_order_price > last_close 
                    and atr > 0.000125*price#3@24000
                    #and (ema5_ratio > 1.0 or (ema5_ratio < 1.0 and buy_order_price < last_close - 0.000208*price)) #5@24000
                    and (buy_order_price > last_close + 0.000208*price) #5@24000
                    and (total_bid == -1 or (total_bid >= 0 and total_bid > sell_total_mean))):
                    
                 
                    if buy_order_amount == 0:
                        limit(symbol,'buy', round(order_lot,4), buy_order_price) 
                    else:      
                        t1 = threading.Thread(target=cancel, args=(symbol, buy_order_id))
                        t2 = threading.Thread(target=limit, args=(symbol,'buy', round(order_lot ,4), buy_order_price))
                
                        t1.start()
                        t2.start()

                        t1.join()
                        t2.join() 
                                                          
                else:
                     
                    if buy_order_amount > 0:
                        cancel(symbol, buy_order_id)
                
                # SELL
                if position_size > 0:
                    
                    if position_size < amount_min  * 1.1:
                         market(symbol,'buy', amount_min+ 0.0006)
                         time.sleep(0.1)
                         market(symbol,'sell', position_size)
                         time.sleep(0.1)
                    else:
                    
                        if sell_order_amount == 0:
                            limit(symbol,'sell', position_size, sell_order_price)
                        else:
                            t1 = threading.Thread(target=cancel, args=(symbol, sell_order_id))
                            t2 = threading.Thread(target=limit, args=(symbol,'sell', position_size, sell_order_price))
                            
                            t1.start()
                            t2.start()
                            
                            t1.join()
                            t2.join() 
                          
        
            if len(li) >= 2:
                li.insert(2,buy_order_price)
                del li[0]
            else:
                li.insert(0,buy_order_price)
                
        
            #if buy_order_amount > 0 and len(li) >= 2:                  
               #mpf.plot(df_3s_ohlcv, type='candle', volume=True,hlines = li[0], style=cs)
            #else:
               #mpf.plot(df_3s_ohlcv, type='candle', volume=True , style=cs) 

           
            try:
                
                total = available_balance + used_amount + position_size * price
    
                if position_size == 0:
                    size_format =  ' pos: ' + '------'
                else:
                    size_format = ' pos: ' + '{:.4f}'.format(position_size)
                    
                if sell_order_amount == 0:
                    sell_order_amount_format = " sel: " + '------'
                else:
                    sell_order_amount_format = " sel: " + '{:.4f}'.format(sell_order_amount)                     
                    

                print('USDT: ' + '{:.3f}'.format(total)\
                      + size_format\
                      + sell_order_amount_format\
                      + ' dis: ' + '{:.3f}'.format(disparity)\
                      + ' v_30s: ' + '{:.2f}'.format(volume_30s)\
                      + ' p: ' + '{:.1f}'.format(price)\
                      + ' t_bi: ' + '{:.2f}'.format(total_bid)\
                      + ' sell_total_mean: ' + '{:.2f}'.format(sell_total_mean)\
                      + ' t_as: ' + '{:.2f}'.format(total_ask)\
                      + ' buy_total_mean: ' + '{:.2f}'.format(buy_total_mean)\
                      + ' atr: ' + '{:.2f}'.format(atr)\
                      + ' b_atr: ' + '{:.2f}'.format(boost_atr)\
                      #+ ' d: ' + '{:.4f}'.format(d)\
                      + ' : ' + str(datetime.datetime.fromtimestamp(int(start)))\
                      + ' tick: ' + str(tick)\
                      
                          )
            except:
                pass     

            new_df = pd.DataFrame({'time': [datetime.datetime.fromtimestamp(int(start))],
                      'timestamp': [t],
                      'asset': [round(total,2)],
                      'sell': [round(sell_order_amount,4)],
                      'buy': [round(buy_order_amount,4)],
                      'disparity': [round(disparity,3)],
                      'last_price': [round(price,1)],
                      'volume_30s': [round(volume_30s,2)],
                      'tick': [round(tick,1)],
                      'atr': [round(atr,2)],
                      'b_atr': [round(boost_atr,2)],
                      'open_3s': [df_3s_ohlcv['open'].iloc[-1]],
                      'high_3s': [df_3s_ohlcv['high'].iloc[-1]],
                      'low_3s': [df_3s_ohlcv['low'].iloc[-1]],
                      'close_3s': [df_3s_ohlcv['close'].iloc[-1]],
                      'volume_3s': [df_3s_ohlcv['volume'].iloc[-1]],
                      'ema3_1m': [kline_df['ema3'].iloc[-1]],
                      'ema4_1m': [kline_df['ema4'].iloc[-1]],
                      'ema5_1m': [kline_df['ema5'].iloc[-1]],
                      'open_1m': [kline_df['open'].iloc[-1]],
                      'high_1m': [kline_df['high'].iloc[-1]],
                      'low_1m': [kline_df['low'].iloc[-1]],
                      'close_1m': [kline_df['close'].iloc[-1]],
                      'volume_1m': [kline_df['volume'].iloc[-1]],                      
                      
                      
                      })


            
            log_df = pd.read_csv('mmbot_log_8.21.csv')
            log_df = log_df.append(new_df)
            log_df.to_csv('mmbot_log_8.21.csv',index=False)
            

                      
if __name__ == '__main__':
    
    try:
        main()
    except KeyboardInterrupt:
        print("terminated ")   



           

                


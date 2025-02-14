from module.setting import instStockChart, instCpCybos, instCpTdUtil, instCpTd0311, instCpTd6033, instCpTdNew5331A, instCpTd5339, instCpTd0314, inStockMst
from final_module.final_dbconnect import DBConnection_trading, DBConnection_present

from pandas.tseries.offsets import BDay
from datetime import date, datetime

import pandas as pd
import time




############# 실시간 데이터 업데이트 #########################################################################################################################################

# 날짜 지정 필수
today = str(date.today()).replace('-','')
yesterday=str(date.today() - BDay(1)).replace('-','').split(' ')[0]

# 실시간 데이터 수집
def get_realtime_stock_info(code, today):

    if instCpCybos.GetLimitRemainCount(0) < 2:
        while True:
            if instCpCybos.GetLimitRemainCount(0) > 2:
                break
            time.sleep(0.1)
    
    instStockChart.SetInputValue(0, 'A'+ code) # 종목명
    instStockChart.SetInputValue(1, ord('2')) # 1 : 기간으로 요청, 2: 개수로 요청
    instStockChart.SetInputValue(3, today) # 요청 시작일
    instStockChart.SetInputValue(2, today) # 요청 종료일
    instStockChart.SetInputValue(4, 1) # 요청 개수
    '''
    # 요청할 데이터 종류(리스트 형태로 요청 가능)
    0 : 날짜, 1 : 시간 - hhmm, 2 : 시가, 3 : 고가, 4 : 저가, 5 : 종가
    6 : 전일대비, 7 : 없음, 8 : 거래량, 9 : 거래대금, 10 : 누적체결매도수량
    11 : 누적체결매수수량, 12 : 상장주식수, 13 : 시가총액, 14 : 외국인주문한도수량, 15 : 외국인주문가능수량
    16 : 외국인현보유수량, 17 : 외국인현보유비율, 18 : 수정주가일자, 19 : 수정주가비율, 20 : 기관순매수
    21 : 기관누적순매수, 22 : 등락주선, 23 : 등락비율, 24 : 예탁금, 25 : 주식회전율
    26 : 거래성립률
    '''
    instStockChart.SetInputValue(5, [0,1, 2, 3, 4, 5, 8, 9, 10, 11])
    instStockChart.SetInputValue(6, ord('m')) # 'D' : 일봉, 'm' : 분봉
    instStockChart.SetInputValue(9, ord('1'))

    instStockChart.BlockRequest() # 위 정보로 요청

    numrow, numcolumn = instStockChart.GetHeaderValue(3), instStockChart.GetHeaderValue(2)

    index = []
    for i in range(numrow):
        index_ = str(instStockChart.GetDataValue(0,i))
        index.append(index_)

    stock_info = pd.DataFrame(columns=numcolumn, index=index)

    for num in range(numrow):
        for col in range(len(numcolumn)):
            # 1,2,3,4,5,6,7,8,9, 10
            stock_info.iloc[num, col] = str(instStockChart.GetDataValue(col,num))

    if instCpCybos.GetLimitRemainCount(1) < 6:
        while True:
            if instCpCybos.GetLimitRemainCount(1) > 6:
                break
            time.sleep(0.1)

    return stock_info.iloc[0:1]

## 실시간으로 들어오는 정보를 DB에 삽입
def sqlalchemy_trading_insert(update_df, code, type, conn, account_name):

    update_df['년'] = update_df['날짜'].apply(str).str[:4]
    update_df['월'] = update_df['날짜'].apply(str).str[4:6]
    update_df['일'] = update_df['날짜'].apply(str).str[6:8]
    update_df.sort_index(ascending=False, inplace=True)
    account_name = account_name.lower()
    update_df.to_sql(name=f'{account_name}_{today}_{code}', con=conn, if_exists=type, index=False)
    conn.close()



#####################################################################################################################################################################################

###### 매수 매도 잔고 조회 #########################################################################################################################################

# 일반 매수 매도 함수
# buysell => str, code => str, quantity => int, price => int
# ex) ds_trade_stock('2', 'A005930', 1, 64000)
def ds_trade_stock(buysell, code, quantity, price):

    if instCpCybos.GetLimitRemainCount(0) < 2:
        while True:
            if instCpCybos.GetLimitRemainCount(0) > 2:
                break
            time.sleep(0.1)

    # 주문 초기화
    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        return False


    # 주식 매수 주문
    acc = instCpTdUtil.AccountNumber[0] #계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd0311.SetInputValue(0, buysell)   # 1: 매도, 2: 매수
    instCpTd0311.SetInputValue(1, acc )   #  계좌번호
    instCpTd0311.SetInputValue(2, accFlag[0])   # 상품구분
    instCpTd0311.SetInputValue(3, 'A' + code)   # 종목코드
    instCpTd0311.SetInputValue(4, quantity)   # 매도, 매수 수량
    instCpTd0311.SetInputValue(5, price)   # 주문단가
    instCpTd0311.SetInputValue(7, '0')   # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
    instCpTd0311.SetInputValue(8, '01')   # 주문호가 구분코드 - 01: 보통 03: 시장가

    # 매수 주문 요청
    nRet = instCpTd0311.BlockRequest()
    if (nRet != 0) :
        print('주문요청 오류 ', quantity, ', 오류코드 : ', nRet)    
        # 0: 정상,  1: 통신요청 실패, 2: 주문확인창에서 취소, 3: 그외의 내부 오류, 4: 주문요청제한 개수 초과 , 5: 주문수량 없음
    else:
        print('주문 정상 접수', ', 매수 수량 : ', quantity)
        return True
    
    rqStatus = instCpTd0311.GetDibStatus() # Dib Server 상태 확인
    errMsg = instCpTd0311.GetDibMsg1() # 확인 메시지 출력
    if rqStatus != 0:
        print('Trade_Stock Dib 연결 실패 : ', rqStatus, errMsg)



# 시장가 매도 함수
def ds_trade_end(buysell, code, quantity):

    if instCpCybos.GetLimitRemainCount(0) < 2:
        while True:
            if instCpCybos.GetLimitRemainCount(0) > 2:
                break
            time.sleep(0.1)

    # 주문 초기화
    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        return


    # # 주식 매수 주문
    acc = instCpTdUtil.AccountNumber[0] #계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd0311.SetInputValue(0, buysell)   # 1: 매도, 2: 매수
    instCpTd0311.SetInputValue(1, acc )   # 계좌번호
    instCpTd0311.SetInputValue(2, accFlag[0])   # 상품구분
    instCpTd0311.SetInputValue(3, 'A' + code)   # 종목코드
    instCpTd0311.SetInputValue(4, quantity)   # 매도, 매수 수량
    # instCpTd0311.SetInputValue(5, price)   # 주문단가
    instCpTd0311.SetInputValue(7, '0')   # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
    instCpTd0311.SetInputValue(8, '03')   # 주문호가 구분코드 - 01: 보통 03: 시장가

    # 매수 주문 요청
    nRet = instCpTd0311.BlockRequest()
    if (nRet != 0) :
        print('주문요청 오류 ', quantity, ', 오류코드 : ', nRet)    
        # 0: 정상,  1: 통신요청 실패, 2: 주문확인창에서 취소, 3: 그외의 내부 오류, 4: 주문요청제한 개수 초과 , 5: 주문수량 없음
    else:
        print('주문 정상 접수', ', 매도 수량 : ', quantity)
        return True

    rqStatus = instCpTd0311.GetDibStatus() # Dib Server 상태 확인
    errMsg = instCpTd0311.GetDibMsg1() # 확인 메시지 출력
    if rqStatus != 0:
        print('Trade_Stock Dib 연결 실패 : ', rqStatus, errMsg)

# 이상 종목 확인
def ds_stock_status(code):

    if instCpCybos.GetLimitRemainCount(1) < 6:
        while True:
            if instCpCybos.GetLimitRemainCount(1) > 6:
                break
            time.sleep(0.1)

    inStockMst.SetInputValue(0, 'A' + code)
    inStockMst.BlockRequest()
    sign1 = chr(inStockMst.GetHeaderValue(66)) # 관리종목 여부
    sign2 = chr(inStockMst.GetHeaderValue(67)) # 투자경고 여부
    sign3 = chr(inStockMst.GetHeaderValue(68)) # 거래정지 여부

    if (sign1 == 'N') & (sign2 == '1') & (sign3 == 'N'):
        return False
        
    else:
        print('이상 종목 발견 리스트에서 제외됩니다.')
        return True

# 미체결 잔량 확인
def ds_n_conclude_check():

    if instCpCybos.GetLimitRemainCount(0) < 2:
        while True:
            if instCpCybos.GetLimitRemainCount(0) > 2:
                break
            time.sleep(0.1)
    
    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        # return
    
    rqStatus = instCpTd6033.GetDibStatus() # Dib Server 상태 확인
    errMsg = instCpTd6033.GetDibMsg1() # 확인 메시지 출력
    if rqStatus != 0:
        print('Account_Value Dib 연결 실패 : ', rqStatus, errMsg)
    
    acc = instCpTdUtil.AccountNumber[0]  # 계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd5339.SetInputValue(0, acc)
    instCpTd5339.SetInputValue(1, accFlag[0])

    instCpTd5339.BlockRequest()

    cnt = instCpTd5339.GetHeaderValue(5)

    order_list = []
    code_list = []
    nconclude_list = []

    for i in range(cnt):
        # print("종목코드 종목명 체결잔고수량 체결장부단가 평가금액 평가손익")
        order_number = instCpTd5339.GetDataValue(1, i)  # 주문번호
        code = instCpTd5339.GetDataValue(3, i)  # 종목코드
        nconclude = instCpTd5339.GetDataValue(11, i) # 주문 수량
        
        order_list.append(order_number)
        code_list.append(code)
        nconclude_list.append(nconclude)

    n_conclude_data = {'종목코드': code_list
                   , '미체결수량' : nconclude_list
                   , '주문번호' : order_list
                   }
    n_conclude_df = pd.DataFrame(n_conclude_data)

    return n_conclude_df

# 미체결 잔량 취소 함수
def ds_order_cancel(code, ordernum):

    if instCpCybos.GetLimitRemainCount(0) < 2:
        while True:
            if instCpCybos.GetLimitRemainCount(0) > 2:
                break
            time.sleep(0.1)

    # 주문 초기화
    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        return

    # 주식 매수 주문
    acc = instCpTdUtil.AccountNumber[0] #계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd0314.SetInputValue(1, ordernum)  #  원주문 번호 - 정정을 하려는 주문 번호
    instCpTd0314.SetInputValue(2, acc)  # 계좌번호
    instCpTd0314.SetInputValue(3, accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
    instCpTd0314.SetInputValue(4, 'A' + code)  # 종목코드
    instCpTd0314.SetInputValue(5, 0)  # 정정 수량, 0 이면 잔량 취소임

    # 매수 주문 요청
    nRet = instCpTd0314.BlockRequest()
    if (nRet != 0) :
        print('주문요청 오류', nRet)    
        # 0: 정상,  1: 통신요청 실패, 2: 주문확인창에서 취소, 3: 그외의 내부 오류, 4: 주문요청제한 개수 초과 
    else:
        print('주문 정상 접수')

# 보유 잔고 조회
def ds_account_stock_check():

    if instCpCybos.GetLimitRemainCount(1) < 6:
        while True:
            if instCpCybos.GetLimitRemainCount(1) > 6:
                break
            time.sleep(0.1)
    
    # 주문 초기화
    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        return
    
    rqStatus = instCpTd6033.GetDibStatus() # Dib Server 상태 확인
    errMsg = instCpTd6033.GetDibMsg1() # 확인 메시지 출력

    if rqStatus != 0:
        print('Account_Stock Dib 연결 실패 : ', rqStatus, errMsg)
    
    acc = instCpTdUtil.AccountNumber[0]  # 계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd6033.SetInputValue(0, acc)
    instCpTd6033.SetInputValue(1, accFlag[0])
    instCpTd6033.SetInputValue(2, 50) # 요청 갯수(최대 50)

    instCpTd6033.BlockRequest()

    cnt = instCpTd6033.GetHeaderValue(7)

    code_list = [0]
    name_list = [0]
    amount_list = [0]
    buyPrice_list = [0]
    evalValue_list = [0]
    evalPerc_list = [0]
    current_value = [0]

    for i in range(cnt):
        code = instCpTd6033.GetDataValue(12, i)  # 종목코드
        name = instCpTd6033.GetDataValue(0, i)  # 종목명
        # cashFlag = instCpTd6033.GetDataValue(1, i)  # 신용구분
        # date = instCpTd6033.GetDataValue(2, i)  # 대출일
        amount = instCpTd6033.GetDataValue(7, i) # 체결잔고수량
        buyPrice = instCpTd6033.GetDataValue(17, i) # 체결장부단가
        evalValue = instCpTd6033.GetDataValue(9, i) # 평가금액(천원미만은 절사 됨)
        evalPerc = instCpTd6033.GetDataValue(11, i) # 평가손익
        
        code_list.append(code)
        name_list.append(name)
        amount_list.append(amount)
        buyPrice_list.append(buyPrice)
        evalValue_list.append(evalValue)
        evalPerc_list.append(evalPerc)
        current_value.append(amount*buyPrice)
    
    status_data = {'종목코드': code_list
                   , '종목명' : name_list
                   , '보유수량' : amount_list
                   , '평단가' : buyPrice_list
                   , '평가금액' : evalValue_list
                   , '수익율' : evalPerc_list
                   , '장부금액' : current_value
                   }
    status_df = pd.DataFrame(status_data)

    return status_df

# 계좌 정보 DB 업데이트
def ds_account_db_update(conn):

    if instCpCybos.GetLimitRemainCount(1) < 6:
        while True:
            if instCpCybos.GetLimitRemainCount(1) > 6:
                break
            time.sleep(0.1)

    initCheck = instCpTdUtil.TradeInit(0)
    if (initCheck != 0):
        print('주문 초기화 실패, 연결 상태 확인 필요')
        # return
    
    rqStatus = instCpTd6033.GetDibStatus() # Dib Server 상태 확인
    errMsg = instCpTd6033.GetDibMsg1() # 확인 메시지 출력
    if rqStatus != 0:
        print('Dib 연결 실패 : ', rqStatus, errMsg)
    
    acc = instCpTdUtil.AccountNumber[0]  # 계좌번호
    accFlag = instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

    instCpTd6033.SetInputValue(0, acc)
    instCpTd6033.SetInputValue(1, accFlag[0])
    instCpTd6033.SetInputValue(2, 50) # 요청 갯수(최대 50)

    instCpTd6033.BlockRequest()

    account_name = instCpTd6033.GetHeaderValue(0)
    account_value = instCpTd6033.GetHeaderValue(9) + instCpTd6033.GetHeaderValue(11) # 0 : 계좌명, 1 : 결제 잔고수량, 2 : 체결 잔고수량, 3 : 평가금액, 4 : 평가손익
    # account_value_2 = instCpTd6033.GetHeaderValue(8) # 5 : 없음, 6 : 대출금액, 7 : 수신개수, 8 : 수익율, 9 : D+2 예상 예수금
    # account_value_3 = instCpTd6033.GetHeaderValue(11) # 10 : 대주평가금액, 11 : 잔고평가금액, 12 : 대주금액

    try:
        sql = "INSERT INTO web_data.account VALUES({0}, '{1}', {2});".format(today,account_name, account_value)
        conn.execute(sql)
        print('계좌 평가금 DB 생성 완료')
        conn.close()
    except:
        sql = "UPDATE web_data.account SET acc_value = '{2}' WHERE date = '{0}' and acc_name = '{1}'".format(today,account_name, account_value)
        conn.execute(sql)
        conn.close()
        print('계좌 평가금 DB 업데이트')
    
    return account_name, account_value

# 보유 잔고 DB 업데이트
def account_status_update(df, conn, account_name):
    args = df.values.tolist()
    account_name = account_name.lower()

    sql_update = f'INSERT INTO {account_name}_account_status VALUES (%s,%s,%s,%s,%s,%s,%s)'

    cursor =  conn.cursor()

    cursor.executemany(sql_update, args)
    conn.commit()
    conn.close()

# 보유 잔고 DB 삭제
def account_status_delete(conn, account_name):
    account_name = account_name.lower()
    sql = f'DELETE FROM web_data.{account_name}_account_status'
    
    conn.execute(sql)
    conn.close()

# 매매 내역 DB 업데이트
def trading_history(conn, account_name, code_name, code, buy_num, sell_num, amount, ratio, pyungga, jangbu, buy_predict, sell_predict):
    now = datetime.now()
    time_ = str(now.year) +'-' + str(now.month) + '-' + str(now.day) + ' ' + str(now.hour) +':' + str(now.minute)
    account_name = account_name.lower()
    profit = str(int(pyungga) - int(jangbu))
    args = [(str(account_name), str(time_), str(code_name), 'A' + str(code), str(buy_num), str(sell_num), str(amount)
            , str(ratio), str(profit), str(buy_predict), str(sell_predict))]  # 계좌이름, 종목코드, 매수, 매도

    try: 
        sql_create = f'''create table web_data.{account_name}_history(
            account_name varchar(20)
            , his_time varchar(50)
            , code_name varchar(30)
            , stock_code varchar(20)
            , buy_num varchar(20)
            , sell_num varchar(20)
            , amount varchar(20)
            , ratio varchar(10)
            , profit varchar(20)
            , buy_predict varchar(20)
            , sell_predict varchar(20)
            )'''
        cur = conn.cursor()
        cur.execute(sql_create)

    except:
        pass

    sql_update = f'INSERT INTO web_data.{account_name}_history VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
    cursor =  conn.cursor()

    cursor.executemany(sql_update, args)
    conn.commit()
    conn.close()

# 매도 조건용 매매 내역 DB 업데이트
def sell_trading_history(conn, account_name, code, buy_num, buy_predict):
    args = [('A' + str(code), str(buy_num), str(buy_predict))]  # 계좌이름, 종목코드, 매수, 매도

    try: 
        sql_create = f'''create table web_data.{account_name}_sell_history(
            stock_code varchar(20)
            , buy_num varchar(20)
            , buy_predict varchar(20)
            )'''
            
        cur = conn.cursor()
        cur.execute(sql_create)

    except:
        pass

    sql_update = f'INSERT INTO web_data.{account_name}_sell_history VALUES (%s,%s,%s)'
    cursor =  conn.cursor()

    cursor.executemany(sql_update, args)
    conn.commit()
    conn.close()

# 매도 조건용 매매 내역 개별 DB 삭제
def sell_history_delete(conn, account_name, code):
    account_name = account_name.lower()
    sql = f"DELETE FROM web_data.{account_name}_sell_history where stock_code like '%%{code}'"
    
    conn.execute(sql)
    conn.close()

# 보유 잔고 정보 반환
def status_history(code):
    status_df = ds_account_stock_check()
    code_name = status_df[status_df['종목코드'] == 'A' + code]['종목명'].values[0]
    amount = status_df[status_df['종목코드'] == 'A' + code]['보유수량'].values[0]
    ratio = round(status_df[status_df['종목코드'] == 'A' + code]['수익율'].values[0], 4)
    pyungga = status_df[status_df['종목코드'] == 'A' + code]['평가금액'].values[0]
    jangbu = status_df[status_df['종목코드'] == 'A' + code]['장부금액'].values[0]

    return code_name, amount, ratio, pyungga, jangbu

############################################################################################################################################################################################

# 실시간 데이터 DB 저장
def stock_trading_db(code, account_name):
    # 실시간 분봉 데이터
    each_target_df = get_realtime_stock_info(code, today) 
    # DB 저장
    sqlalchemy_trading_insert(each_target_df, code, 'replace', DBConnection_trading().get_sqlalchemy_connect_ip(), account_name)
    
    return each_target_df
        
# 실시간 매매 진행 및 조건 설정
def real_trading(predict_df, cost, code, each_target_df, now, account_name, predict_max, predict_min):

    # 이상 종목 여부 확인
    if ds_stock_status(code):
        return code

    # 거래 종목 보유 여부 및 정보 확인
    try:
        status_df = ds_account_stock_check()
        code_name = status_df[status_df['종목코드'] == 'A' + str(code)]['종목명'].values[0]
    except:
        status_df = ds_account_stock_check()
        code_name = ' 보유하지 않은 종목'
        
    try:
        end_cost = int(each_target_df['종가'].values[0])   # 종가
        high_cost = int(each_target_df['고가'].values[0])   # 고가
        print('')
        print('========================================================================')
        print('대상 종목 코드 : ' + str(code) + ' 종목명 : ' + str(code_name))
        print('========================================================================')
        print('초기자금 : ' + str(cost) + ' 매도 확률 : ' + str(predict_df['0'].values[0]) + ' 매수 확률 : ' + str(predict_df['1'].values[0]))
        print('========================================================================')
        print('종목별 매수 금액 : ' + str(cost) + ' 종가 : ' + str(end_cost) + ' 고가 : ' + str(high_cost))
        print('========================================================================')
                

        status_db_df = status_df.copy()
        status_db_df.rename(columns={'종목코드': 'code', '종목명' : 'name', '보유수량' : 'amount', '평단가' : 'buyprice'
                                    , '평가금액' : 'evalValue' , '수익율' : 'ratio', '장부금액' : 'currentValue'}, inplace=True)

        account_status_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name)                                    
        account_status_update(status_db_df, DBConnection_present().get_pymysql_connection(), account_name)

        # 미체결 종목 및 수량 데이터 프레임 생성
        n_conclude_df = ds_n_conclude_check()

        # 미체결 잔량 처리
        try:
            n_conclude_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['미체결수량'].values[0]
            buy_num = (cost // int(end_cost)) - int(n_conclude_num) # 총 매수량

            if (predict_df['1'].values[0] > predict_df['0'].values[0]) & (float(status_db_df[status_db_df['code'] == 'A' + str(code)]['ratio'].values[0]) < 2.0):
                order_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['주문번호'].values[0]
                ds_order_cancel(code, order_num)
                print('미체결 주문 취소 완료')
                n_conclude_num = 0 

        except:
            buy_num = cost // int(end_cost) # 총 매수량
            n_conclude_num = 0

        # 현재 보유 수량이 없는 경우 진입
        if ('A' + code) not in status_df['종목코드'].values.tolist():

            if (int(now.strftime('%H%M')) >= 1520):
                print('장이 종료되어 리스트에서 종목을 제거합니다')
                print('')
                return code

            elif (predict_df['1'].values[0] > predict_df['0'].values[0]) & (end_cost < high_cost) & (buy_num > 0)\
                 & (int(now.strftime('%H%M')) < 1520) & (status_df['장부금액'].sum() < 45000000):
                 
                print('')
                print('++++++++++++++++++++++++++++ 신규 매수 위치 +++++++++++++++++++++++++++++')
                print('목표 매수 수량 : ' + str(buy_num))
                print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
                try:
                    if n_conclude_num == 0:
                        # if float(predict_df['비교'].values[0]) < -0.4:
                            # num = 500000 // end_cost
                        if (int(end_cost)) <= 100000:
                            num = 100000 // int(end_cost)
                        else:
                            num = 1
                        if ds_trade_stock('2', code, num , end_cost) == True:
                            code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                            time.sleep(0.3)
                            trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, num, 0
                                            , total_num, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                            time.sleep(0.3)
                            sell_trading_history(DBConnection_present().get_pymysql_connection(), account_name, code, num, predict_df['1'].values[0])
                            time.sleep(0.3)
                except:
                    print('현재 매수 매도를 할 수 없습니다.')
                    print('실전 / 모의투자 또는 개장 시간을 확인하세요.')
                print('')
            else:
                print('신규 매수 조건을 만족하지 않습니다')
                print('')

        # 현재 보유 수량이 있는 경우 진입
        else:

            amount = status_df[status_df['종목코드'] == 'A' + str(code)]['보유수량'].values[0]
            end = status_df[status_df['종목코드'] == 'A' + str(code)]['평단가'].values[0]

            current_value = status_df[status_df['종목코드'] == 'A' + str(code)]['장부금액'].values[0]
            buy_num = ((cost-current_value) // int(end_cost)) - int(n_conclude_num)

            if cost > current_value:
                predict_position = ((predict_max - predict_min) * ((cost - current_value) / cost)) + predict_min
            else:
                predict_position = predict_max

            print('========================================================================')
            print('현재 예측 위치값 : ' + str(predict_position) + ' 차이값 : ' + str(round(predict_position - predict_df['1'].values[0],3)))
            print('========================================================================')

            # 장 마감 전 보유 종목 전체 매도
            if (amount > 0) & (int(now.strftime('%H%M')) >= 1520):
                
                print('')
                print('**************************** 장 마감 전 매도 **************************')
                print(' 매도 가능 수량 : ' + str(amount))
                print('**********************************************************************')
                
                try:
                    if (n_conclude_num != amount) & (n_conclude_num != 0):
                        order_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['주문번호'].values[0]
                        ds_order_cancel(code, order_num)

                    code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                    if ds_trade_end('1', code, amount) == True:
                        time.sleep(1)
                        trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, 0, amount
                                        , 0, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                        time.sleep(1)
                        sell_history_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name, code)
                        time.sleep(1)
                        return code
                        
                except:
                    print('현재 매수 매도를 할 수 없습니다.')
                    print('실전 / 모의투자 또는 개장 시간을 확인하세요.')

                print('')

            # 수익율이 10% 이상 상승 시 강제 매도
            elif ((end*1.1) < float(end_cost)) & (amount > 0):

                print('')
                print('----------------------- 수익율 10% 초과 매도 위치 ------------------------')
                print(' 매도 가능 수량 : ' + str(amount))
                print('------------------------------------------------------------------------')
                try:
                    if n_conclude_num != 0:
                        order_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['주문번호'].values[0]
                        ds_order_cancel(code, order_num)
                    
                    if ds_trade_end('1', code, amount) == True:
                        code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                        time.sleep(0.3)
                        trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, 0, amount
                                        , 0, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                        time.sleep(0.3)
                        sell_history_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name, code)
                        time.sleep(0.3)
                        return code
                except:
                    print('현재 매수 매도를 할 수 없습니다.')
                    print('실전 / 모의투자 또는 개장 시간을 확인하세요.')
                print('')

            # 예측 값이 매수 -> 매도로 변경된 경우 매도 처리
            elif (predict_df['0'].values[0] > predict_df['1'].values[0]) & (amount > 0):
                print('')
                print('------------------------- 예측 값 변동 매도 위치 -------------------------')
                print(' 매도 가능 수량 : ' + str(amount))
                print('------------------------------------------------------------------------')

                ratio = round(float(status_df[status_df['종목코드'] == 'A' + code]['수익율'].values[0]), 4)

                if (float(ratio) < 1.0) & (float(ratio) > -1.0):
                    print(f'현재 수익율 {ratio}로 매도를 진행하지 않습니다.')
                
                else:
                    try:
                        if n_conclude_num != 0:
                            order_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['주문번호'].values[0]
                            ds_order_cancel(code, order_num)
                        
                        if ds_trade_end('1', code, amount) == True:
                            code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                            time.sleep(0.3)
                            trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, 0, amount
                                            , 0, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                            time.sleep(0.3)
                            sell_history_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name, code)
                            time.sleep(0.3)
                            return code

                    except:
                        print('현재 매수 매도를 할 수 없습니다.')
                        print('실전 / 모의투자 또는 개장 시간을 확인하세요.')
                print('')

            # 현재 예측 값이 매수 예측 값의 평균보다 미달할 경우 진입
                
            elif (predict_position - predict_df['1'].values[0] > 0.01 ) & (amount > 0):
                print('')
                print('---------------------- 예측 값 평균 이탈 매도 위치 ---------------------')
                print('현재 예측 위치값 : ' + str(predict_position) + ' 매도 가능 수량 : ' + str(amount))
                print('------------------------------------------------------------------------')

                ratio = round(float(status_df[status_df['종목코드'] == 'A' + code]['수익율'].values[0]), 4)

                if (float(ratio) < 1.0) & (float(ratio) > -1.0):
                    print(f'현재 수익율 {ratio}로 매도를 진행하지 않습니다.')
                
                else:
                    try:
                        if n_conclude_num != 0:
                            order_num = n_conclude_df[n_conclude_df['종목코드'] == 'A' + str(code)]['주문번호'].values[0]
                            ds_order_cancel(code, order_num)
                        
                        if ds_trade_end('1', code, amount) == True:
                            code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                            time.sleep(0.3)
                            trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, 0, amount
                                            , 0, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                            time.sleep(0.3)
                            sell_history_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name, code)
                            time.sleep(0.3)

                            if int(jangbu) > 2500000:
                                return code

                    except:
                        print('현재 매수 매도를 할 수 없습니다.')
                        print('실전 / 모의투자 또는 개장 시간을 확인하세요.')
                print('')

            # 추가 매수 조건 시 진입
            elif (predict_df['1'].values[0] > predict_df['0'].values[0]) & (end_cost < high_cost) & (buy_num > 0) \
                & (int(now.strftime('%H%M')) < 1520) & (status_df['장부금액'].sum() < 45000000):
                
                print('')
                print('++++++++++++++++++++++++++++ 추가 매수 위치 ++++++++++++++++++++++++++++')
                print('목표 매수 수량 : ' + str(buy_num))
                print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

                try:
                    if n_conclude_num == 0:
                        # if float(predict_df['비교'].values[0]) < -0.4:
                            # num = 500000 // end_cost
                        if int(end_cost) <= 500000:
                            num = 500000 // int(end_cost)
                        else:
                            num = 1
                        
                        if ds_trade_stock('2', code, num , end_cost) == True:
                            code_name, total_num, ratio, pyungga, jangbu = status_history(code)
                            time.sleep(0.3)
                            trading_history(DBConnection_present().get_pymysql_connection(), account_name, code_name, code, num, 0
                                            , total_num, ratio, pyungga, jangbu, predict_df['1'].values[0], predict_df['0'].values[0])
                            time.sleep(0.3)
                            sell_trading_history(DBConnection_present().get_pymysql_connection(), account_name, code, num, predict_df['1'].values[0])
                            time.sleep(0.3)

                except:
                    print('현재 매수 매도를 할 수 없습니다.')
                    print('실전 / 모의투자 또는 개장 시간을 확인하세요.')
                print('')
                
            else:
                print('추가 매수 및 매도 조건을 만족하지 않습니다.')
                print('종목별 매수 금액 : ' + str(cost) + ' 종가 : ' + str(end_cost) + ' 고가 : ' + str(high_cost) + ' 보유 수량 : ' + str(amount))

    except:
        print('매매를 시도하였으나 에러가 발생하였습니다 종목명 : ' + str(code_name))

    time.sleep(0.6)
    return 0


# 현재 DB 내 거래 종목 테이블 존재 여부 확인
def get_pymysql_predict_table_check(code, conn,account_name):
    sql = f"SELECT 1 FROM Information_schema.tables  WHERE table_schema = 'predict_data' AND table_name = '{account_name}_{today}_{code}'"

    cur = conn.cursor()
    count = cur.execute(sql)
    conn.close()

    return count

  
###########################################################################################################################################################################

# 실시간 매매 실행
def realtime_trading(stock_list , account_name, account_value):
    time_cnt = 0
    while True:
        now = datetime.now()
        if int(now.strftime('%H%M')) > 1540:
            account_status_delete(DBConnection_present().get_sqlalchemy_connect_ip(), account_name)
            _, final_account_value = ds_account_db_update(DBConnection_trading().get_sqlalchemy_connect_ip())
            print("!!!!!!매매 종료!!!!!!!!  -- 최종 예수 금액 : " + str(final_account_value))
            break
        
        elif (now.hour < 9) | (now.hour > 16):
            time_cnt += 1
            if time_cnt == 100:
                print('박대기중~~~~~~~')
                time_cnt = 0
            time.sleep(1)
            
        else:
            if len(stock_list) == 0:
                print('모든 종목 매도 완료')
                time.sleep(10)

            for code in stock_list:
                first_cost = account_value // 5 # 1000만원
                each_target_df = stock_trading_db(code, account_name)
                try:
                    get_pymysql_predict_table_check(code, DBConnection_trading().get_pymysql_connection(), account_name)

                except:
                    # DB에 테이블이 존재하지 않으면 sleep
                    print('Trading_Data가 존재하지 않습니다.')
                    time.sleep(1)
                
                try:
                    sql = f"SELECT * FROM predict_data.{account_name}_{today}_{code} order by id desc limit 1"
                    pred_data = DBConnection_trading().get_sqlalchemy_connect_ip().execute(sql)
                    predict_df = pd.DataFrame(pred_data.fetchall())  # DB내 테이블을 DF로 변환

                except:
                    print('SQL에 존재하지 않음. 계좌명 : ' + str(account_name) + ' 날짜 : ' + str(today) + ' 종목코드 : ' + str(code))
                
                try:
                    sql = f"SELECT * FROM web_data.{account_name}_sell_history where stock_code like '%%{code}' and buy_num > 0"
                    mean_pred_data = DBConnection_trading().get_sqlalchemy_connect_ip().execute(sql)
                    mean_predict_df = pd.DataFrame(mean_pred_data.fetchall())  # DB내 테이블을 DF로 변환
                    mean_predict = mean_predict_df['buy_predict'].astype('float')
                    predict_max = mean_predict.max()
                    predict_min = mean_predict.min()

                except:
                    print('')
                    print('SQL에 데이터가 충분하지 않음. 계좌명 : ' + str(account_name) + ' 날짜 : ' + str(today) + ' 종목코드 : ' + str(code))
                    mean_predict = 0.0
                    predict_max = 0.0
                    predict_min = 0.0
                
                try:
                    sell_code = real_trading(predict_df, first_cost, code, each_target_df, now, account_name, predict_max, predict_min)
                except:
                    print('트레이딩 에러 발생')

                try:
                    if sell_code == 0:
                        continue
                    else:
                        stock_list.remove(sell_code)
                except:
                    print('매매 종목 삭제 중 에러 발생')
#-*- coding: utf-8 -*-


import json
import hashlib
import requests
import random
import datetime
import traceback
import configparser
import os
import time
import pymysql
import sys

def db_operate(sql):
	connect = pymysql.Connect(
		host='your ip',
		port=your port,
		user='your account',
		passwd='password!',
		db='top',
		charset='utf8'
	)

	cursor = connect.cursor()
	cursor.execute(sql)
	r=cursor.fetchall()
	connect.commit()
	cursor.close()
	connect.close()
	return r
# 连接数据库

path=os.getcwd()
now=datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
hour=datetime.datetime.now().strftime('%H')

url_invite='https://www.top.one/register?inviter=R1N529W372D152'
url_server='https://server.top.one/'
url_trade='https://trade.top.one/'
url_market='https://depth.top.one/'
url_api='api/apiToken'
url_time='api/time'
header_data = {'Content-type': 'application/json'}


random_number=random.randint(100000,999999)
try:
	print('程序初始化中，启动时间[%s]......' % now)
	print('\t读取配置文件......',end='')
	cp = configparser.ConfigParser()
	configFile=path+'\\top.ini'
	cp.read(configFile,encoding='gb2312')
	#cp.readfp(codecs.open(configFile, "r", "utf-8-sig"))
	config={}
	config['account']=str(cp.get('config','TOPONE帐号')).lower().strip()
	config['appID']=cp.get('config','appID').strip()
	config['appKey']=cp.get('config','appKey').strip()
	config['tradePair']=cp.get('config','交易对').strip().upper()
	config['tradeAmount']=float(str(cp.get('config','单次交易数量')).strip())#单次交易数量
	config['tradeCurrencyMax']=int(str(cp.get('config','交易总金额')).strip())#交易总金额
	config['tradeCountMax']=int(str(cp.get('config','交易总次数')).strip())#交易总次数
	config['tradeInterval']=5   #交易间隔时间（秒）
	config['tradePriceType']=1  
	config['tradeCurrencyMin']=0.011 #minimum trade per time
	config['tradeAddMin']=float(str(cp.get('config','交易最小增幅')).strip())#交易最小增幅
	config['tradePriceDesc']=''

	config['token']=cp.get('system','token').strip()
	config['token_update_time']=cp.get('system','token_update_time').strip()

	if(len(config['appID'])!=32):
		print('appID错误，应为32位字符，请检查！')
		sys.exit()
	if(len(config['appKey'])!=32):
		print('appKey错误，应为32位字符，请检查！')
		sys.exit()

	print('OK')

	trade_count=0
	trade_currency=0
	print('\t白名单帐号验证中......',end='')
	sql="select account,appid from whitelist where account='%s'" % config['account']
	r=db_operate(sql)
	if(len(r)==0):#不是白名单
		print('\n\t帐号[%s]不是邀请注册白名单，请通过链接[%s]注册后联系开发者获取！' % (config['account'],url_invite))
		sys.exit()
	elif(len(r[0])==2):#帐号appid同时存在，判断是不是相符
		if(len(r[0][1])==32):
			if(r[0][1]!=config['appID']):
				print('\n\t帐号[%s]是邀请注册白名单，但appID[%s]不对，请使用该帐号正确的appID！' % (r[0][0],r[0][1]))
				sys.exit()
		else:#只有帐号，保存appid供下次验证
			sql = "update whitelist set appid='%s' where account='%s'" % (config['appID'], config['account'])
			db_operate(sql)
	print('[%s]是白名单' % r[0][0])

	print('\t获取服务器时间......',end='')

	time_frame=requests.get(url_server+url_time).json()['data']['time']
	print('OK')

	print('\ttoken有效性检测中......',end='')
	if (config['token_update_time']=='' or config['token']==''):
		config['token_update_time']='2001/01/01 01:01:00'
	time_diff = (datetime.datetime.now() - datetime.datetime.strptime(config['token_update_time'], '%Y/%m/%d %H:%M:%S')).seconds
	if(time_diff>3600 ):#
		print('过期!')
		print('\t获取Token中......', end='')
		url_param = 'appid=%s&random=%s&time=%s' % (config['appID'], str(random_number), str(time_frame))
		url_sig = 'appkey=%s&random=%s&time=%s' % (config['appKey'], str(random_number), str(time_frame))

		sig = hashlib.sha256(url_sig.encode('utf-8')).hexdigest()
		total_token_url = url_server + url_api + '?' + url_param + '&sig=' + sig
		token = requests.get(total_token_url)
		token = token.json()
		if (str(token['error_code']) != '0'):  # 出错
			print('获取Token失败！[%s]%s' % (token['error_code'], token['data']))
			sys.exit()
		token = token['data']['apitoken']
		config['token']=token
		cp.set('system','token',token)
		cp.set('system','token_update_time',now)
		cp.write(open(configFile, 'w'))
		print('OK')
	else:
		print('OK')

	print('\t获取余额中......',end='')

	token1=config['tradePair'][0:config['tradePair'].find('/')]
	token2=config['tradePair'][config['tradePair'].find('/')+1:99]
	post_data = {'method':'balance.query','params':[''+config['token']+'',token1,token2],'id':0}
	result = requests.post(url_trade, data=json.dumps(post_data), headers=header_data).json()
	if(result['error'] is not None):
		print('获取余额失败！[%s]%s' %(result['error']['code'],result['error']['message']))
		sys.exit()
	result = result['result']
	balance={token1:{},token2:{}}
	for b in result:
		balance[b['asset']]['total']=float(b['total'])
		balance[b['asset']]['freeze'] = float(b['freeze'])
		balance[b['asset']]['available']=float(b['available'])
		balance[b['asset']]['ethvalue']=float(b['ethvalue'])
	print('OK')

	if(balance[token1]['available']<config['tradeAmount']):
		print('\n\t可用余额不足！可用[%f]<配置单次交易数量[%f]，程序退出！' % (balance[token1]['available'],config['tradeAmount']))
		sys.exit()

	if (config['tradePriceType'] == 0):  
		config['tradePriceDesc']='买1买1中间值'
	elif (config['tradePriceType'] == 1):
		config['tradePriceDesc']='买1基础上增加最小值'
	elif (config['tradePriceType'] == 2):
		config['tradePriceDesc']='卖1基础上降低最小值'
	elif (config['tradePriceType'] == 3):
		config['tradePriceDesc']=str(config['tradePrice'])
		pass
	print('量化交易中，价格=[%s],单次数量=[%f%s]，总次数<[%i],总金额<[%.2f%s]' %
	      (config['tradePriceDesc'],config['tradeAmount'],token1,config['tradeCountMax'],config['tradeCurrencyMax'],token2))

	while (trade_count<config['tradeCountMax'] and trade_currency<config['tradeCurrencyMax']):
		#取市场行情
		print('\t获取市场行情中......', end='')
		post_data = {'method':'depth.query','params':[config['tradePair'],1],'id':0}
		result_market = requests.post(url_market, data=json.dumps(post_data), headers=header_data).json()
		result_market = result_market['result']
		if(result_market is None):
			print('\n获取行情失败，继续尝试！[%s]%s' %(result_market['error']['code'],result_market['error']['message']))
			continue

		order_book={'buy':{},'sell':{}}
		order_book['buy']['price']=float(result_market[0]['bids'][0][0])
		order_book['buy']['amount']=float(result_market[0]['bids'][0][1])
		order_book['sell']['price']=float(result_market[0]['asks'][0][0])
		order_book['sell']['amount']=float(result_market[0]['asks'][0][1])
		print('OK(买1＝[%.8f%s]，卖1＝[%.8f%s])' % (order_book['buy']['price'],token2,order_book['sell']['price'],token2))


		if(config['tradePriceType']==0):  #0：买1买1中间值，1：买1基础上增加最小值，2：卖2基础上降低最小值，#3：固定值（对应config['tradePrice']）
			config['tradePrice']=round((order_book['buy']['price']+order_book['sell']['price'])/2,9)
		elif(config['tradePriceType']==1):
			config['tradePrice']=order_book['buy']['price']+config['tradeAddMin']
		elif(config['tradePriceType']==2):
			config['tradePrice']=order_book['sell']['price']-config['tradeAddMin']
		elif(config['tradePriceType']==3):
			pass

		if(config['tradePrice']*config['tradeAmount']<config['tradeCurrencyMin']):
			config['tradeAmount']=config['tradeCurrencyMin']/config['tradePrice']
			print('\t交易总金额低于系统要求，自动调整交易数量为[%.2f]' % config['tradeAmount'])


		print('\t第[%i]次交易，价格＝[%.8f],数量=[%.2f],总价=[%.5f]ETH......' % (trade_count+1,config['tradePrice'],2*config['tradeAmount'],2*config['tradeAmount']*config['tradePrice']), end='')

		post_data = {'method':'order.limit','params':[config['token'],config['tradePair'],1,str(config['tradeAmount']),str(config['tradePrice']),0],'id':0}#sell
		result_sell_order = requests.post(url_trade, data=json.dumps(post_data), headers=header_data).json()
		if(result_sell_order['error'] is not None):
			r=input('\n\t下卖单失败,([%s]%s),continue?(Y/N)' %(result_sell_order['error']['code'],result_sell_order['error']['message']))
			if(r.upper()=='Y'):
				continue
			else:
				sys.exit()
		result_sell_order = result_sell_order['result']
		post_data = {'method':'order.limit','params':[config['token'],config['tradePair'],2,str(config['tradeAmount']),str(config['tradePrice']),0],'id':0}#buy
		result_buy_order = requests.post(url_trade, data=json.dumps(post_data), headers=header_data).json()
		if(result_buy_order['error'] is not None):
			r=input('\n\t下买单失败！[%s]%s,continue?(Y/N)' %(result_buy_order['error']['code'],result_buy_order['error']['message']))
			if(r.upper()=='Y'):
				continue
			else:
				sys.exit()
		result_buy_order = result_buy_order['result']
		trade_count+=1
		trade_currency+=config['tradeAmount']*config['tradePrice']*2
		print('成功(等候%.1f秒)！' % config['tradeInterval'] )
		time.sleep(config['tradeInterval'])


	print('执行完毕！共交易[%i]次，交易金额[%.8f]ETH' % (trade_count,trade_currency))

except Exception as e:
	traceback.print_exc()
finally:
	input('\n按回车键退出......')

#balance format
{
	"freeze": "0.6",  # 下单冻结
	"asset": "ETH",  # 资产名称
	"available": "999.2036012",  # 可用余额
	"total": "999.8036012",  # 总余额
	"btcvalue": "0",  # BTC估值
	"ethvalue": "999.8036012"  # ETH估值
}
	
# order format
	{
		"method": "order.limit",
		"params": [
			"token",  # Token
			"TOP/ETH",  # 市场
			2,  # 买卖 1 卖  2 买
			"1000",  # 数量
			"0.00001057",  # 价格
			1  # 是否使用top抵扣手续费 1是 0 否
		],
		"id": 0
	}

		
#order result format
{
	"error": 'null',
	"result": {
		"id": 26211,  # 订单ID
		"type": 1,  # 订单类型   1 限价单  2 市价单
		"market": "TOP/ETH",  # 市场
		"side": 2,  # 买卖方向   1 卖  2 买
		"ctime": 1526205633.6342139,  # 下单时间
		"mtime": 1526205633.6342139,  # 更新时间
		"price": "0.00001057",  # 下单价格
		"deal_money": "0",  # 成交额
		"status": 1,  # 订单状态   0 进行中  1 完成  2 撤单
		"amount": "10000",  # 下单量
		"left": "10000",  # 剩余量(未成交量)
		"deal_stock": "0"  # 成交量
	},
	"id": 0
}
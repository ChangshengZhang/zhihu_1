#!/usr/bin/python
# -*- coding: utf-8 -*-
# File Name: get_id.py
# Author: Changsheng Zhang
# mail: zhangcsxx@gmail.com
# Created Time: Mon Oct 15 20:45:31 2018

#########################################################################

import os
import requests
import datetime
import traceback
from bs4 import BeautifulSoup
import time
import re
import random
import sys
import asyncio
import concurrent.futures as cf
import json
from multiprocessing import Process


def _write_list_to_file(data,fp,mode = 'w',new_line_flag = 1):

    f = open(fp,mode)
    op_line = ''
    for item in data:
        op_line = op_line + str(item) + ','
    op_line = op_line.strip(',')
    if new_line_flag:
        op_line = op_line+'\n'
    f.write(op_line)
    f.close()

def _get_num_from_str(data):

    return re.findall(r'(\d+(,\s*\d+)*)',data)

def _delete_proxy(proxy):

    requests.get('http://127.0.0.1:5010/delete/?proxy={}'.format(proxy))

def _get_valid_proxy():

    valid_flag = False
    try_count = 0
    while (not valid_flag) and try_count < 5:
        proxy_list = requests.get('http://127.0.0.1:5010/get_all/').json()
        if len(proxy_list) <10:
            time.sleep(10*60)
            proxy_list = requests.get('http://127.0.0.1:5010/get_all/').json()
        proxy = random.choice(proxy_list)
        valid_flag = requests.get('http://127.0.0.1:5010/validate_proxy/?proxy={}'.format(proxy)).json()['result']
        if not valid_flag:
            _delete_proxy(proxy)
        try_count += 1
        print('try to get proxy NO. {}'.format(try_count))

    return proxy

def _get_html(url,proxy):

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}

    try:
        #proxy = _get_valid_proxy()
        print(proxy,url)
        data = requests.get(url,proxies = {'https':'https://{}'.format(proxy)},headers = headers, timeout = 5).text
        return data,proxy
    except Exception as e:
        print(e)
        traceback.print_exc()
        proxy = _get_valid_proxy()
        data = requests.get(url,proxies = {'https':'https://{}'.format(proxy)},headers = headers, timeout = 10).text
        return data,proxy

# get:
#   关注了,关注者,赞同，感谢
#   关注了和关注者的 url_token

class GetZhihuUser():

    last_update = ''
    user_name = ''
    proxy = ''

    def __init__(self,url_token):
        
        self.url_token = url_token
        self.proxy = _get_valid_proxy()
        self.data_type = 'followers'

        try:
            self.get_user_info()
        except Exception as e:
            print(e)
            traceback.print_exc()
            print('get user info occurs some error.')

        try:
            flag = self.get_follow_info(self.follower_num)
        except Exception as e:
            print(e)
            traceback.print_exc()
            print('get follow info has meet some error.')
        
    def get_user_info(self):

        user_url = 'https://www.zhihu.com/people/{}/activities'.format(self.url_token)
        main_pg,self.proxy = _get_html(user_url, self.proxy)
        soup = BeautifulSoup(main_pg,'html5lib')

        data = soup.find('div',attrs={'id':'data'})['data-state']
        data = json.loads(data)
        user_info = data['entities']['users'][self.url_token]

        self.user_name = user_info['name']
        self.agree_num = user_info['voteupCount']
        self.thanks_num = user_info['thankedCount']
        self.public_edit_num = user_info['logsCount']
        self.following_num = user_info['followingCount']
        self.follower_num = user_info['followerCount']
        self.collect_num = user_info['favoritedCount']
        print('get user info. follower num:',self.follower_num, ' following num:',self.following_num)

        try:
            activity_info = str(soup.findAll('div', class_ = 'ActivityItem-meta')[0].get_text())
            self.last_update = activity_info
        except:
            self.last_update = ''
    
        user_url = 'https://www.zhihu.com/people/{}/activities'.format(self.url_token)
    
        _write_list_to_file(['user_name','follower_num','last_update','agree_num','thanks_num','collect_num','public_edit_num','following_num','url'],'./data/basic_user/{}.csv'.format(self.url_token),mode = 'w')
        _write_list_to_file([self.user_name,self.follower_num,self.last_update,self.agree_num,self.thanks_num,self.collect_num,self.public_edit_num,self.following_num,user_url],'./data/basic_user/{}.csv'.format(self.url_token),mode = 'a')

    def get_follow_url_token(self,url,ii,op):

        ii = int(ii)
        html,self.proxy = _get_html(url+str(ii), self.proxy)

        soup = BeautifulSoup(html,'html5lib')

        follower_url_token = []
        data = soup.find('div',attrs = {'id':'data'})['data-state']
        data = json.loads(data)

        if self.data_type == 'followers':
            items = data['people']['followersByUser'][self.url_token]['ids']
        else:
            items = data['people']['followingByUser'][self.url_token]['ids']

        for item in items:
            if item!=None and item!=False and item!=True and item!='知乎用户':
                follower_url_token.append(item+'\n')

        f = open(op+'/'+str(ii)+'.csv', 'w')
        f.writelines(follower_url_token)
        f.close()
            
    def get_follow_info(self,follow_num):

        print('get {} info'.format(self.data_type))
        url_following = 'https://www.zhihu.com/people/{}/{}?page='.format(self.url_token,self.data_type)
        following_pg_max_num = int((int(follow_num) - 1)/20 + 1)
        following_op = './data/{}/{}'.format(self.data_type,self.url_token)

        if os.path.exists(following_op):
            existed_file = os.listdir('./data/'+self.data_type+'/'+self.url_token)
            if len(existed_file) == following_pg_max_num:
                print('{} already exists.'.format(self.url_token))
                return 0
        else:
            os.system('mkdir '+following_op)

        for ii in range(1, following_pg_max_num+1):
            print('get {}/{}th following info.'.format(ii,following_pg_max_num))
            try:
                self.get_follow_url_token(url_following,ii,following_op)
            except Exception as e:
                print(e)
                traceback.print_exc()
                try:
                    self.get_follow_url_token(url_following,ii,following_op)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                    pass
        return 0

async def run_thread():

    fn_list = open('./merged_base_fans.csv').readlines()
    fn_list = [fn.split(',')[0] for fn in fn_list[1:]]

    with cf.ThreadPoolExecutor(max_workers = 5) as executor:
        loop = asyncio.get_event_loop()
        futures = (loop.run_in_executor(executor, get_follow_, fn) for fn in fn_list)
        for result in await asyncio.gather(*futures):
            pass

# get follow list
def get_follow_(fn):

    a = GetZhihuUser(fn)

if __name__ =="__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_thread())
    loop.close()



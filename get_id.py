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
    while (not valid_flag) and try_count < 3:
        proxy = random.choice(requests.get('http://127.0.0.1:5010/get_all/').json())
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
        return data
    except:
        proxy = _get_valid_proxy()
        data = requests.get(url,proxies = {'https':'https://{}'.format(proxy)},headers = headers, timeout = 10).text
        return data

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

        try:
            self.get_user_info()
        except:
            print('get user info occurs some error.')
        try:
            flag = self.get_follow_info()
        except:
            print('get follow info has meet some error.')
        
    def get_user_info(self):

        user_url = 'https://www.zhihu.com/people/{}/activities'.format(self.url_token)
        main_pg = _get_html(user_url, self.proxy)
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
        html = _get_html(url+str(ii), self.proxy)

        soup = BeautifulSoup(html,'html5lib')
        follower_info = str(soup.findAll('div',style = 'display:none')[0])

        follower_url_token = []
        follower_count = []

        op_lines = []

        for tmp in follower_info.split(','):

            if 'urlToken' in tmp and not ('loading' in tmp) and not(self.url_token in tmp):
                tmp_token = tmp.split(':',1)[1].strip('"')
                if 'quot' in tmp_token:
                    follower_url_token.append(tmp_token.split(';')[1].split('&')[0])
                else:
                    follower_url_token.append(tmp_token)
        
            if 'followerCount' in tmp:
                follower_count.append(_get_num_from_str(tmp)[0][0])

        if self.follower_num == follower_count[-1]:
            for jj in range(len(follower_url_token)):
                op_lines.append(follower_url_token[jj]+','+follower_count[jj]+'\n')
        else:
            for jj in range(len(follower_url_token)):
                op_lines.append(follower_url_token[jj]+','+follower_count[jj+1]+'\n')

        f = open(op+'/'+str(ii)+'.csv', 'w')
        f.writelines(op_lines)
        f.close()
            
    def get_follow_info(self):

        print('get following info')
        url_following = 'https://www.zhihu.com/people/{}/following?page='.format(self.url_token)
        following_pg_max_num = int((int(self.following_num) - 1)/20 + 1)
        following_op = './data/following/{}'.format(self.url_token)

        if os.path.exists(following_op):
            existed_file = os.listdir('./data/following/'+self.url_token)
            if len(existed_file) == following_pg_max_num:
                print('{} already exists.'.format(self.url_token))
                return 0
        else:
            os.system('mkdir '+following_op)

        #if following_pg_max_num < 5:
        for ii in range(1, following_pg_max_num+1):
            print('get {}/{}th following info.'.format(ii,following_pg_max_num))
            self.get_follow_url_token(url_following,ii,following_op)

        return 0
        #else:
        #    loop = asyncio.get_event_loop()
        #    loop.run_until_complete(self.run_thread(url_following, following_op, following_pg_max_num))
        #    loop.close()


        #print('get follower info')
        #url_follower = 'https://www.zhihu.com/people/{}/followers?page='.format(self.url_token)
        #follower_pg_max_num = int((int(self.follower_num) -1)/20 + 1)
        #follower_op = './data/follower/{}'.format(self.url_token)

        #if follower_pg_max_num < 5:
        #    for ii in range(1, follower_pg_max_num+1):
        #        print('get {}/{}th follower info.'.format(ii,follower_pg_max_num))
        #        self.get_follow_url_token(url_follower,ii,follower_op)
        #else:
        #    loop = asyncio.get_event_loop()
        #    loop.run_until_complete(self.run_thread(url_follower, follower_op, follower_pg_max_num))
        #    loop.close()

async def run_thread():

    fn_list = open('./merged_id.csv').readlines()[0].split(',')

    with cf.ThreadPoolExecutor(max_workers = 3) as executor:
        loop = asyncio.get_event_loop()
        futures = (loop.run_in_executor(executor, get_follow_, fn) for fn in fn_list)
        for result in await asyncio.gather(*futures):
            pass

# get follow list
def get_follow_(fn):

    try:
        a = GetZhihuUser(fn)
    except:
        print(fn+' has some error.')

if __name__ =="__main__":

    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(run_thread())
    #loop.close()

    #fn_list = open('./merged_id.csv').readlines()[0].split(',')
    for kk in range(int(sys.argv[1]),int(sys.argv[2])):
        print(kk)
        fn_list = open('./id/{}'.format(kk)).readline().split(',')

        for ii in range(len(fn_list)):
            print('get {}:{}/{}th following info.'.format(kk,ii,len(fn_list)))
            get_follow_(fn_list[ii])


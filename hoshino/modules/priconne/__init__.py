'''
Author: AkiraXie
Date: 2021-01-30 00:39:25
LastEditors: AkiraXie
LastEditTime: 2021-01-30 00:41:48
Description: 
Github: http://github.com/AkiraXie/
'''
# 数据初始化：拷贝sample
import shutil
import os
pcrdatapath=os.path.join(os.path.dirname(__file__),'_pcr_data.py')
jsonpath=os.path.join(os.path.dirname(__file__),'gacha','config.json')
spcrdatapath=os.path.join(os.path.dirname(__file__),'_pcr_data_sample.py')
sjsonpath=os.path.join(os.path.dirname(__file__),'gacha','config_sample.json')
if not os.path.exists(pcrdatapath):
    shutil.copy(spcrdatapath,pcrdatapath)
if not os.path.exists(jsonpath):
    shutil.copy(sjsonpath,jsonpath)
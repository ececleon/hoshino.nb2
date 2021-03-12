'''
Author: AkiraXie
Date: 2021-01-28 23:36:14
LastEditors: AkiraXie
LastEditTime: 2021-03-12 18:06:23
Description: 
Github: http://github.com/AkiraXie/
'''
from hoshino import Bot, hsn_config
from nonebot import get_driver
driver=get_driver()

@driver.on_bot_connect
async def _(bot: Bot):
    for su in hsn_config.superusers:
        await bot.send_private_msg(user_id=int(su), message='生命周期上线~')

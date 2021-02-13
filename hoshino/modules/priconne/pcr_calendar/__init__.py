'''
Author: AkiraXie
Date: 2021-02-13 21:31:35
LastEditors: AkiraXie
LastEditTime: 2021-02-13 22:03:10
Description: 
Github: http://github.com/AkiraXie/
'''
from .util import check_ver, db_message
from hoshino import Service,  sucmd, scheduler, rule, Bot, Event
from hoshino.typing import T_State
from hoshino.util import text2Seg


svjp = Service('calendar-jp', enable_on_default=False)
svbl = Service('calendar-bili', enable_on_default=False)
svtw = Service('calendar-tw', enable_on_default=False)


@scheduler.scheduled_job('cron', hour='*/3', jitter=40)
async def db_check_ver():
    await check_ver('jp')
    await check_ver('bili')
    await check_ver('tw')


@scheduler.scheduled_job('cron', hour='14', minute='15', jitter=30)
async def _():
    await svjp.broadcast(text2Seg(await db_message('jp')), 'calendar-jp')
    await svbl.broadcast(text2Seg(await db_message('bili')), 'calendar-bilibili')
    await svtw.broadcast(text2Seg(await db_message('tw')), 'calendar-tw')


updatedb = sucmd('updatedb', rule.to_me())


@updatedb.handle()
async def _(bot: Bot):
    codejp = await check_ver('jp')
    codebl = await check_ver('bili')
    codetw = await check_ver('tw')
    successcount = 0
    failcount = 0
    for i in [codebl, codejp, codetw]:
        if i == 0:
            successcount += 1
        elif i == -1:
            failcount += 1
    if failcount != 0:
        await updatedb.finish(f'检测数据库更新失败,失败数量:{failcount}.请前往后台查看')
    else:
        await updatedb.finish(f'检测数据库版本成功,{successcount}个数据库有更新')


async def look_calendar(bot: Bot, event: Event, state: T_State):
    match = state['match']
    is_now = match.group(1) == '当前'
    is_future = match.group(1) == '预定'
    is_all = not match.group(1)
    if is_now:
        await bot.send(event, text2Seg(await db_message(state['region'], 'now')), at_sender=True)
    if is_future:
        await bot.send(event, text2Seg(await db_message(state['region'], 'future')), at_sender=True)
    if is_all:
        await bot.send(event, text2Seg(await db_message(state['region'], 'all')), at_sender=True)


twcal = svtw.on_regex(r'^台服(当前|预定)?日程$', state={
                      'region': 'tw'}, handlers=[look_calendar])
blcal = svbl.on_regex(r'^[b国]服(当前|预定)?日程$', state={
                      'region': 'bili'}, handlers=[look_calendar])
jpcal = svjp.on_regex(r'^日服(当前|预定)?日程$', state={
                      'region': 'jp'}, handlers=[look_calendar])

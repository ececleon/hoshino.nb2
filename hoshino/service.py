'''
Author: AkiraXie
Date: 2021-01-28 00:44:32
LastEditors: AkiraXie
LastEditTime: 2021-02-10 00:21:01
Description: 
Github: http://github.com/AkiraXie/
'''
import asyncio
import re
import os
import json
from collections import defaultdict
from nonebot.typing import T_ArgsParser, T_Handler
from nonebot.message import run_preprocessor, run_postprocessor
from hoshino.log import wrap_logger
from hoshino import Bot, service_dir as _service_dir, Message, MessageSegment
from hoshino.event import Event
from hoshino.matcher import Matcher, on_command, on_message,  on_startswith, on_endswith, on_notice, on_request, on_shell_command
from hoshino.permission import ADMIN, NORMAL, OWNER, Permission, SUPERUSER
from hoshino.util import get_bot_list
from hoshino.rule import ArgumentParser, Rule, to_me, regex, keyword
from hoshino.typing import Dict, Iterable, Optional, Union, T_State, Set, List, Type

_illegal_char = re.compile(r'[\\/:*?"<>|\.!！]')
_loaded_services: Dict[str, "Service"] = {}
_loaded_matchers: Dict["Type[Matcher]", "matcher_wrapper"] = {}


def _save_service_data(service: "Service"):
    data_file = os.path.join(_service_dir, f'{service.name}.json')
    with open(data_file, 'w', encoding='utf8') as f:
        json.dump({
            "name": service.name,
            "enable_group": list(service.enable_group),
            "disable_group": list(service.disable_group)
        }, f, ensure_ascii=False, indent=2)


def _load_service_data(service_name: str) -> dict:
    data_file = os.path.join(_service_dir, f'{service_name}.json')
    if not os.path.exists(data_file):
        return {}
    with open(data_file, encoding='utf8') as f:
        data = json.load(f)
        return data


class Service:
    def __init__(self, name: str, manage_perm: Permission = ADMIN, enable_on_default: bool = True, visible: bool = True):
        '''
        Descrption:  定义一个服务

        Params: 

        *`name` : 服务名字

        *`manage_perm` : 管理服务的权限,是一`Permission`实例,`ADMIN`和`OWNER`和`SUPERSUSER`是允许的

        *`enable_on_default` : 默认开启状态

        *`visible` : 默认可见状态
        '''
        assert not _illegal_char.search(
            name) or not name.isdigit(), 'Service name cannot contain character in [\\/:*?"<>|.] or be pure number'
        assert manage_perm in (
            ADMIN, OWNER, SUPERUSER), 'Service manage_perm is illegal'
        self.name = name
        self.manage_perm = manage_perm
        self.enable_on_default = enable_on_default
        self.visible = visible
        assert self.name not in _loaded_services, f'Service name "{self.name}" already exist!'
        _loaded_services[self.name] = self
        data = _load_service_data(self.name)
        self.enable_group = set(data.get('enable_group', []))
        self.disable_group = set(data.get('disable_group', []))
        self.logger = wrap_logger(self.name)
        self.matchers = []

    @staticmethod
    def get_loaded_services() -> Dict[str, "Service"]:
        return _loaded_services

    def set_enable(self, group_id):
        self.enable_group.add(group_id)
        self.disable_group.discard(group_id)
        _save_service_data(self)

    def set_disable(self, group_id):
        self.enable_group.discard(group_id)
        self.disable_group.add(group_id)
        _save_service_data(self)

    async def get_enable_groups(self) -> Dict[int, List[Bot]]:
        gl = defaultdict(list)
        for bot in get_bot_list():
            sgl = set(g['group_id'] for g in await bot.get_group_list())
            if self.enable_on_default:
                sgl = sgl - self.disable_group
            else:
                sgl = sgl & self.enable_group
            for g in sgl:
                gl[g].append(bot)
        return gl

    @property
    def config(self) -> dict:
        filename = f'hoshino/service_config/{self.name}.json'
        try:
            with open(filename, encoding='utf8') as f:
                return json.load(f)
        except:
            self.logger.error(f'Failed to load config')
            return dict()

    def check_enabled(self, group_id: int) -> bool:
        return bool((group_id in self.enable_group) or (
            self.enable_on_default and group_id not in self.disable_group))

    def check_service(self, only_to_me: bool = False, only_group: bool = True) -> Rule:
        async def _cs(bot: Bot, event: Event, state: T_State) -> bool:
            if not 'group_id' in event.__dict__:
                return not only_group
            else:
                group_id = event.group_id
                return self.check_enabled(group_id)
        rule = Rule(_cs)
        if only_to_me:
            rule = rule & (to_me())
        return rule

    def on_command(self, name: str, only_to_me: bool = False, aliases: Optional[Iterable] = None, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        if isinstance(aliases, str):
            aliases = set([aliases])
        elif not isinstance(aliases, set):
            if aliases:
                aliases = set([aliases]) if len(aliases) == 1 else set(aliases)
            else:
                aliases = set()
        kwargs['aliases'] = aliases
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.command', priority, command=name, only_group=only_group)
        matcher = on_command(name, **kwargs)
        mw.load_matcher(matcher)
        self.matchers.append(str(mw))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_shell_command(self, name: str, only_to_me: bool = False, aliases: Optional[Iterable] = None, parser: Optional[ArgumentParser] = None, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        if isinstance(aliases, str):
            aliases = set([aliases])
        elif not isinstance(aliases, set):
            if aliases:
                aliases = set([aliases]) if len(aliases) == 1 else set(aliases)
            else:
                aliases = set()
        kwargs['parser'] = parser
        kwargs['aliases'] = aliases
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.shell_command', priority, command=name, only_group=only_group)
        mw.load_matcher(on_shell_command(name, **kwargs))
        self.matchers.append(str(mw))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_startswith(self, msg: str, only_to_me: bool = False, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.startswith', priority, startswith=msg, only_group=only_group)
        mw.load_matcher(on_startswith(msg, **kwargs))
        self.matchers.append(str(mw))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_endswith(self, msg: str, only_to_me: bool = False, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.endswith', priority, endswith=msg, only_group=only_group)
        mw.load_matcher(on_endswith(msg, **kwargs))
        self.matchers.append(str(mw))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_keyword(self, keywords: Union[Set[str], str], normal: bool = True, only_to_me: bool = False, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        if isinstance(keywords, str):
            keywords = set([keywords])
        elif not isinstance(keywords, set):
            if keywords:
                keywords = set([keywords]) if len(
                    keywords) == 1 else set(keywords)
            else:
                keywords = set()
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = keyword(*keywords, normal) & rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.keyword', priority, keywords=str(keywords), only_group=only_group)
        mw.load_matcher(on_message(**kwargs))
        self.matchers.append(str(mw))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_regex(self, pattern: str, flags: Union[int, re.RegexFlag] = 0, normal: bool = True, only_to_me: bool = False, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        '''
        根据正则表达式进行匹配。
        可以通过 ``state["_matched"]`` 获取正则表达式匹配成功的文本。
        可以通过 ``state["match"]`` 获取正则表达式匹配成功后的`match`
        '''
        rule = self.check_service(only_to_me, only_group)
        rule = regex(pattern, flags, normal) & rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.regex', priority, pattern=str(pattern), flags=str(flags), only_group=only_group)
        self.matchers.append(str(mw))
        mw.load_matcher(on_message(rule, permission, **kwargs))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_message(self,  only_to_me: bool = False, only_group: bool = True, permission: Permission = NORMAL, **kwargs) -> "matcher_wrapper":
        kwargs['permission'] = permission
        rule = self.check_service(only_to_me, only_group)
        kwargs['rule'] = rule
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Message.message', priority, only_group=only_group)
        self.matchers.append(str(mw))
        mw.load_matcher(on_message(**kwargs))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_notice(self,  only_group: bool = True, **kwargs) -> "matcher_wrapper":
        rule = self.check_service(0, only_group)
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Notice', priority, only_group=only_group)
        self.matchers.append(str(mw))
        mw.load_matcher(on_notice(rule, **kwargs))
        _loaded_matchers[mw.matcher] = mw
        return mw

    def on_request(self, only_group: bool = True, **kwargs) -> "matcher_wrapper":
        rule = self.check_service(0, only_group)
        priority = kwargs.get('priority', 1)
        mw = matcher_wrapper(self,
                             'Request', priority, only_group=only_group)
        self.matchers.append(str(mw))
        mw.load_matcher(on_request(rule, **kwargs))
        _loaded_matchers[mw.matcher] = mw
        return mw

    async def broadcast(self, msgs: Optional[Iterable], tag='', interval_time=0.5):
        if isinstance(msgs, (str, Message, MessageSegment)):
            msgs = (msgs,)
        gdict = await self.get_enable_groups()
        for gid in gdict.keys():
            for bot in gdict[gid]:
                sid = int(bot.self_id)
                for msg in msgs:
                    await asyncio.sleep(interval_time)
                    try:
                        await bot.send_group_msg(self_id=sid, group_id=gid, message=msg)
                        self.logger.info(
                            f"{sid}在群{gid}投递{tag}成功")
                    except:
                        self.logger.error(f'{sid}在群{gid}投递{tag}失败')


class matcher_wrapper:
    '''
    封装了 ``nonebot.matcher.Matcher`` ,使之可以受Service干预。

    并将 ``Matcher`` 常见的类方法进行了封装，如果需要其他类方法，请调用 ``.matcher.* ``
    '''

    def __init__(self, sv: Service, type: str, priority: int, **info) -> None:
        self.sv = sv
        self.priority = priority
        self.info = info
        self.type = type

    def load_matcher(self, matcher: Type[Matcher]):
        self.matcher = matcher

    @staticmethod
    def get_loaded_matchers()->List[str]:
        return list(map(str, _loaded_matchers.values()))

    def handle(self):
        def deco(func: T_Handler):
            return self.matcher.handle()(func)
        return deco

    def __call__(self, func: T_Handler) -> T_Handler:
        return self.handle()(func)

    def receive(self):
        def deco(func: T_Handler):
            return self.matcher.receive()(func)
        return deco

    def got(self,
            key: str,
            prompt: Optional[Union[str, "Message", "MessageSegment"]] = None,
            args_parser: Optional[T_ArgsParser] = None):
        def deco(func: T_Handler):
            return self.matcher.got(key, prompt, args_parser)(func)
        return deco

    async def reject(self,
                     prompt: Optional[Union[str, "Message",
                                            "MessageSegment"]] = None,
                     **kwargs):
        return await self.matcher.reject(prompt, **kwargs)

    async def pause(self,
                    prompt: Optional[Union[str, "Message",
                                           "MessageSegment"]] = None,
                    **kwargs):
        return await self.matcher.pause(prompt, **kwargs)

    async def send(self, message: Union[str, "Message", "MessageSegment"],
                   **kwargs):
        return await self.matcher.send(message, **kwargs)

    async def finish(self,
                     message: Optional[Union[str, "Message",
                                             "MessageSegment"]] = None,
                     **kwargs):
        return await self.matcher.finish(message, **kwargs)

    def __str__(self) -> str:
        finfo = [f"{k}={v}" for k, v in self.info.items()]
        return (f"<Matcher from Sevice {self.sv.name}, priority={self.priority}, type={self.type}, "
                + ", ".join(finfo)+">")

    def __repr__(self) -> str:
        return self.__str__


@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    mw = _loaded_matchers.get(matcher.__class__, None)
    if mw:
        mw.sv.logger.info(f'Event will be handled by <lc>{mw}</>')


@run_postprocessor
async def _(matcher: Matcher, exception: Exception, bot: Bot, event: Event, state: T_State):
    mw = _loaded_matchers.get(matcher.__class__, None)
    if mw:
        if exception:
            mw.sv.logger.error(
                f'Event handling failed from <lc>{mw}</>', False)
        mw.sv.logger.info(f'Event handling completed from <lc>{mw}</>')

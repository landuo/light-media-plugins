# New sequence fixtures only. Original selected methods above are byte-derived from seal965.
# No original app, DB, service, socket, or external receiver is started.
class SiteOper:
 def list_order_by_pri(self):return [SimpleNamespace(id=501)]
class SitesHelper:
 def get_indexers(self):return [dict(id=501,name='Owned sequence site',domain='https://owned.invalid/',public=False)]
def conf(enabled=True,retry=''):
 c=cfg();c.update(enabled=enabled,cron='58 23 31 12 *',sign_sites=[501],retry_keyword=retry);return c
# Falsification of the draft's first-command assumption: init alone retains old success/retry[].
negative=plugin('negative-without-reset');init(negative,conf(retry='错误|失败'));negative.sign_in()
negative_before=copy.deepcopy(negative.kv);negative.posts=[];init(negative,conf(retry=''))
negative.sign_in(Event(dict(action='site_signin',channel=MessageChannel.Web,source='owned-user',user='owned-user')))
assert len(negative.calls)==1 and [x['title']for x in negative.posts]==['开始站点签到 ...']
negative_row=dict(case='config-only-empty-retry-does-not-clear-old-success',calls=len(negative.calls),history_before=negative_before,history_after=negative.kv,posts=negative.posts)
base=plugin('base');clone=plugin('clone');clone.__class__=type('AutoSignIncmd',(ASI,),{})
init(base,conf(retry='错误|失败'));base.sign_in();assert len(base.calls)==1
pre_reset=copy.deepcopy(base.kv)
# Explicit reset boundary: only owned memory history is cleared; reset API is not under test.
base.kv.clear();init(base,conf(retry=''));init(clone,conf(enabled=False,retry=''))
sequence=[];db=[];queue=[];notices=[]
chain=C();chain.messageoper=SimpleNamespace(add=lambda **kw:(db.append(copy.deepcopy(kw)),sequence.append(['db',kw.get('title'),kw.get('action')])));chain.eventmanager=SimpleNamespace(send_event=lambda **kw:(notices.append(copy.deepcopy(kw['data'])),sequence.append(['notice',kw['data'].get('title')])));chain.messagequeue=SimpleNamespace(send_message=lambda name,**kw:(queue.append(copy.deepcopy(kw['message'].model_dump())),sequence.append(['queue',kw['message'].title])));chain.messagehelper=SimpleNamespace(put=lambda *args,**kw:None)
EventType.NoticeMessage='NoticeMessage'
for a in (base,clone):a.chain=chain;a.post_message=lambda _a=a,**kw:BASE.post_message(_a,**kw)
# Fixed EventManager enable gate is executed; thread scheduling and module lookup are controlled.
EV=selected('app/core/event.py','EventManager',{'__get_handler_identifier','__get_class_from_callable','__is_handler_enabled','__safe_invoke_handler'})
gate=EV();gate._EventManager__disabled_handlers=set();gate._EventManager__disabled_classes=set()
deliveries=[]
def deliver(handler,event):
 deliveries.append(handler.__self__.case);handler(event)
gate._EventManager__invoke_handler_by_type_sync=deliver
core=next(n for n in ast.walk(ast.parse(SOURCES['app/chain/message.py']))if isinstance(n,ast.FunctionDef)and n.name=='_handle_message_core')
branch=copy.deepcopy(next(n for n in core.body if isinstance(n,ast.If)and getattr(n,'lineno',0)==349))
branch_fn=ast.FunctionDef(name='ordinary_branch',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n)for n in ['self','text','userid','channel','source','processing_status']],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[branch],decorator_list=[])
exec(compile(ast.fix_missing_locations(ast.Module(body=[branch_fn],type_ignores=[])),'app/chain/message.py:349-362','exec'),globals())
manager=SimpleNamespace(get_plugin_commands=lambda:[dict(pid=pid,**cmd)for pid,a in [('AutoSignIn',base),('AutoSignIncmd',clone)]for cmd in a.get_command()])
co=COMMAND();co.pluginmanager=manager;co.messagehelper=SimpleNamespace(put=lambda **kw:stamp('command_error',data=kw));co._plugin_commands=co._Command__build_plugin_commands();co.get=lambda cmd:co._plugin_commands.get(cmd)
web=top('app/api/endpoints/message.py','web_message');schemas=SimpleNamespace(Response=lambda **kw:kw)
command_bus=Bus();mc=SimpleNamespace(eventmanager=command_bus,_has_ai_prefix=lambda text:False)
web_calls=[]
def handle(**kw):
 web_calls.append(copy.deepcopy(kw));MC._record_user_message(chain,kw['channel'],kw['source'],kw['userid'],kw['username'],kw['text']);ordinary_branch(mc,kw['text'],kw['userid'],kw['channel'],kw['source'],None)
MessageChain=lambda:SimpleNamespace(handle_message=handle)
class Request:
 headers={'content-type':'application/json'}
 async def json(self):return {'text':'/site_signin'}
def run_command(label):
 before_calls=[len(base.calls),len(clone.calls)];before_messages=len(db);start_delivery=len(deliveries)
 # The fixed PluginManager enables/disables whole plugin classes by get_state; apply that
 # owned registry boundary, then execute the exact fixed EventManager gate.
 gate._EventManager__disabled_classes={EV._EventManager__get_handler_identifier(a.__class__)for a in (base,clone)if not a.get_state()}
 asyncio.run(web(request=Request(),text=None,current_user=SimpleNamespace(name='owned-user')))
 assert len(command_bus.events)==1
 command_event=command_bus.events.pop();co.command_event(Event(command_event[1]));assert len(eventmanager.events)==1
 kind,data=eventmanager.events.pop();assert kind==EventType.PluginAction and data['action']=='site_signin'
 for a in (base,clone):gate._EventManager__safe_invoke_handler(a.sign_in,Event(data))
 row=dict(case=label,calls_before=before_calls,calls_after=[len(base.calls),len(clone.calls)],attendance_total=len(base.calls)+len(clone.calls),message_count=len(db),new_messages=copy.deepcopy(db[before_messages:]),delivered=deliveries[start_delivery:],event=copy.deepcopy(data),history=dict(base=copy.deepcopy(base.kv),clone=copy.deepcopy(clone.kv)))
 rows.append(row)
run_command('command1-empty-retry-base-only-after-explicit-reset')
init(clone,conf(enabled=True,retry=''))
run_command('command2-empty-retry-broadcast-two-enabled')
before_reconfigure=dict(base=copy.deepcopy(base.kv),clone=copy.deepcopy(clone.kv))
init(base,conf(retry='错误|失败'));init(clone,conf(retry='错误|失败'))
assert before_reconfigure==dict(base=base.kv,clone=clone.kv),'init unexpectedly changed history'
run_command('command3-nonempty-retry-warmup-still-uses-stored-retry')
run_command('command4-nonempty-retry-dedups-after-warmup')
assert [r['attendance_total']for r in rows]==[2,4,6,6]
assert [r['message_count']for r in rows]==[3,8,13,16]
assert rows[0]['delivered']==['base'] and all(r['delivered']==['base','clone']for r in rows[1:])
assert [sum(m.get('title')=='站点签到完成！'for m in r['new_messages'])for r in rows]==[1,2,2,0]
assert all(r['event']['channel']==MessageChannel.Web and r['event']['source']=='owned-user'and r['event']['user']=='owned-user'for r in rows)
print(json.dumps(dict(classification='immutable333/netnone source-method synthetic replay: fixed Web endpoint, incoming history, ordinary command branch, Command event dispatch, fixed EventManager enabled gate, PluginBase/ChainBase outgoing message methods and installed sign_in/full__do; controlled memory stores, plugin registry, synchronous delivery, successful site result; no original app/DB/network/external receiver, no target Main',negative=negative_row,pre_reset_private_history=pre_reset,rows=rows,records=db,sequence=sequence,web_calls=web_calls,timeline=timeline,processing_finish=_Finish),ensure_ascii=False,indent=2,default=lambda x:x.value if isinstance(x,Enum)else str(x)))

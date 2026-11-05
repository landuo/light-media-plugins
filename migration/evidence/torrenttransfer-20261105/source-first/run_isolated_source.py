#!/usr/bin/env python3
"""Original AST classes only; synthetic host/client/codec dependencies, no host imports.

This is an execution oracle for source branch/state/effect order, not a bencode,
YAML, network, Go-target, browser or real-host acceptance test.
"""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from types import SimpleNamespace as NS
from typing import Any, List, Dict, Tuple, Optional, Union
from zoneinfo import ZoneInfo
import tempfile

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
SOURCE = TASK / "source-snapshot"
OBS = []
TRACE = []


class Log:
    def __getattr__(self, _):
        return lambda *a, **k: None


class Scheduler:
    def __init__(self, **kw):
        self.kw, self.jobs, self.running = kw, [], False

    def add_job(self, func, trigger, **kw):
        self.jobs.append((func.__name__, trigger, kw))

    def get_jobs(self):
        return self.jobs

    def print_jobs(self):
        pass

    def start(self):
        self.running = True

    def remove_all_jobs(self):
        self.jobs.clear()

    def shutdown(self):
        self.running = False


class Cron:
    @staticmethod
    def from_crontab(value):
        if len(value.split()) != 5:
            raise ValueError("synthetic invalid cron")
        return value


class Plugin:
    def __init__(self):
        self.effects = []
        self.saved = {}
        self.systemmessage = NS(put=lambda *a, **kw: self.effects.append(("message", a, kw)))

    def update_config(self, config):
        self.effects.append(("config", copy.deepcopy(config)))

    def save_data(self, key, value):
        self.saved[key] = copy.deepcopy(value)
        self.effects.append(("history", key, copy.deepcopy(value)))

    def post_message(self, **kw):
        self.effects.append(("notification", copy.deepcopy(kw)))


class Helpers:
    services = {}

    def get_service(self, name):
        return self.services.get(name)

    def get_configs(self):
        return {k: NS(name=k) for k in self.services}

    def is_downloader(self, kind, service):
        return bool(service and service.type == kind)


class Client:
    def __init__(self, kind):
        self.kind, self.completed, self.calls = kind, [], []
        self.query, self.add_result, self.tag_hash = ([], False), None, "new-hash"

    def is_inactive(self):
        return False

    def get_completed_torrents(self):
        self.calls.append(("completed", {}))
        return self.completed

    def get_torrents(self, **kw):
        self.calls.append(("query", copy.deepcopy(kw)))
        if isinstance(self.query, Exception):
            raise self.query
        return self.query

    def add_torrent(self, **kw):
        self.calls.append(("add", copy.deepcopy(kw)))
        if self.add_result is not None:
            return self.add_result
        return (True, []) if self.kind == "qbittorrent" else NS(hashString="new-hash")

    def get_torrent_id_by_tag(self, **kw):
        self.calls.append(("tag-id", copy.deepcopy(kw)))
        return self.tag_hash

    def delete_torrents(self, **kw):
        self.calls.append(("delete", copy.deepcopy(kw)))
        return False

    def recheck_torrents(self, **kw):
        self.calls.append(("recheck", copy.deepcopy(kw)))
        return False

    def start_torrents(self, **kw):
        self.calls.append(("start", copy.deepcopy(kw)))
        return False


def decode_fixture(raw):
    table = {
        b"with-announce": {"announce": "https://tracker.invalid/announce", "info": {}},
        b"without-announce": {"info": {}},
        b"announce-list-only": {"announce-list": [["https://old.invalid"]], "info": {}},
        b"one-tracker": {"trackers": [["https://tracker.invalid/announce"]]},
        b"many-trackers": {"trackers": [["a", "b"], ["c"]]},
        b"no-trackers": {},
    }
    if raw not in table:
        raise ValueError("synthetic decode failure")
    return copy.deepcopy(table[raw])


def encode_fixture(value):
    return json.dumps(value, sort_keys=True).encode()


def source_class(relative, class_name, env):
    path = SOURCE / relative
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    unit = ast.Module(body=[cls], type_ignores=[])
    exec(compile(unit, str(path), "exec"), env)
    return env[class_name]


def record(case, function):
    try:
        observed = function()
        OBS.append({"id": case, "status": "passed", "observed": observed})
    except Exception as exc:
        OBS.append({"id": case, "status": "failed", "exception": type(exc).__name__, "message": str(exc)})


def equal(actual, expected):
    assert actual == expected, (actual, expected)
    return actual


with tempfile.TemporaryDirectory(prefix="isolated-source-", dir=HERE) as tmp:
    root = Path(tmp)
    (root / "config").mkdir()
    (root / "builtin").mkdir()
    (root / "temp").mkdir()
    settings = NS(CONFIG_PATH=root/"config", INNER_CONFIG_PATH=root/"builtin", TEMP_PATH=root/"temp", TZ="UTC")
    (settings.INNER_CONFIG_PATH / "category.yaml").write_text("# synthetic builtin\nmovie:\n  fallback:\n")
    env = dict(globals(), _PluginBase=Plugin, settings=settings, CategoryHelper=lambda: NS(init=lambda: TRACE.append("reload")),
               DownloaderHelper=Helpers, logger=Log(), Qbittorrent=Client, Transmission=Client,
               TorrentDictionary=dict, ServiceInfo=NS, NotificationType=NS(SiteMessage="SiteMessage"),
               StringUtils=NS(generate_random_str=lambda n: "R"*n), BackgroundScheduler=Scheduler,
               CronTrigger=Cron, pytz=NS(timezone=ZoneInfo), bdecode=decode_fixture, bencode=encode_fixture)
    CE = source_class("categoryeditor/__init__.py", "CategoryEditor", env)
    TT = source_class("torrenttransfer/__init__.py", "TorrentTransfer", env)
    CL = source_class("torrenttransfermusic/__init__.py", "TorrentTransfermusic", env)

    def ce_apply():
        p = CE()
        TRACE.clear()
        text = "# synthetic policy 中文\nmovie:\n  example:\n"
        p.init_plugin({"enabled": True, "content": text, "unknown": 1})
        equal(CE.user_yaml.read_text(), text)
        equal(TRACE, ["reload"])
        equal([e[0] for e in p.effects], ["message", "config"])
        equal(p.effects[-1][1], {"enabled": False, "content": text})
        return {"file_exact": True, "reload": 1, "effects": [e[0] for e in p.effects], "state": p.get_state()}
    record("CE-T02", ce_apply)

    def ce_empty():
        p = CE(); p.init_plugin({"enabled": True})
        equal(CE.user_yaml.read_text(), "")
        equal(p.get_state(), False)
        return p.effects[-1][1]
    record("CE-T03", ce_empty)

    def ce_disabled():
        CE.user_yaml.write_text("unchanged")
        p=CE(); p.init_plugin({"content":"no write"})
        equal(p.get_state(), None); equal(p.effects, []); equal(CE.user_yaml.read_text(), "unchanged")
        return {"state":p.get_state(),"effects":p.effects}
    record("CE-T01", ce_disabled)

    def ce_form():
        schema,defaults=CE().get_form()
        equal(defaults["content"], (settings.INNER_CONFIG_PATH/"category.yaml").read_text())
        return {"default_is_builtin":True,"enabled":defaults["enabled"],"ace":schema[0]["content"][1]["content"][0]["content"][0]["props"]}
    record("CE-T08", ce_form)

    def ce_write_failure():
        p=CE(); p.user_yaml=settings.CONFIG_PATH
        try: p.init_plugin({"enabled":True,"content":"x"})
        except IsADirectoryError: pass
        else: raise AssertionError("expected write failure")
        equal(p.get_state(), True); equal(p.effects,[])
        return {"state":True,"effects":[]}
    record("CE-T04", ce_write_failure)

    # Installed helper classification method: exact original AST, no constructor,
    # loader, third-party YAML implementation or real host imports are executed.
    host_path=TASK/"host-reference/app/modules/themoviedb/category.py"
    host_scope=dict(env,WeakSingleton=type,CommentedMap=dict,CategoryConfig=NS)
    host_cls=next(n for n in ast.parse(host_path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=="CategoryHelper")
    exec(compile(ast.Module(body=[host_cls],type_ignores=[]),str(host_path),"exec"),host_scope)
    category=host_scope["CategoryHelper"].get_category
    categories=[
        ("empty-metadata",{"fallback":None},{},""),
        ("empty-categories",{}, {"x":1},""),
        ("first-catch-all",{"first":None,"second":{"genre_ids":"16"}},{"genre_ids":[16]},"first"),
        ("and-country-genre",{"animation":{"genre_ids":"16","origin_country":"CN,TW"},"fallback":None},{"genre_ids":[16],"origin_country":["cn"]},"animation"),
        ("and-reject",{"animation":{"genre_ids":"16","origin_country":"CN,TW"},"fallback":None},{"genre_ids":[16],"origin_country":["JP"]},"fallback"),
        ("missing-attr",{"a":{"origin_country":"!CN"},"fallback":None},{"genre_ids":[16]},"fallback"),
        ("release-range",{"recent":{"release_year":"2020-2023"},"fallback":None},{"release_date":"2022-01-01"},"recent"),
        ("release-tv-fallback",{"recent":{"release_year":"2020-2023"},"fallback":None},{"first_air_date":"2023-12-01"},"recent"),
        ("negative-range",{"a":{"release_year":"!2020-2023"},"fallback":None},{"release_date":"2022-01-01"},"fallback"),
        ("negative-range-pass",{"a":{"release_year":"!2020-2023"},"fallback":None},{"release_date":"2019-01-01"},"a"),
        ("rule-no-whitespace-trim",{"a":{"original_language":"en, zh"},"fallback":None},{"original_language":"zh"},"fallback"),
        ("casefold-production-country",{"a":{"production_countries":"cn"},"fallback":None},{"production_countries":[{"iso_3166_1":"CN"}]},"a"),
        ("generic-list",{"a":{"x":"2,4"},"fallback":None},{"x":[1,2,3]},"a"),
        ("false-rule-value-ignored",{"a":{"x":False},"fallback":None},{"any":1},"a"),
        ("string-range-endpoints",{"a":{"original_language":"EN-US"},"fallback":None},{"original_language":"us"},"a"),
        ("reversed-range-becomes-empty",{"a":{"release_year":"2023-2020"},"fallback":None},{"release_date":"1990-01-01"},"a"),
    ]
    for name,policy,metadata,expected in categories:
        record("CE-T11-"+name,lambda policy=policy,metadata=metadata,expected=expected:equal(category(policy,metadata),expected))

    def invalid_rule_type():
        try:category({"a":{"genre_ids":16}},{"genre_ids":[16]})
        except AttributeError:return {"raised":"AttributeError"}
        raise AssertionError("original nonstring value must fail at split")
    record("CE-T11-nonstring-rule",invalid_rule_type)

    def fresh(kind="qbittorrent", dest="qbittorrent", overrides=None, cls=TT):
        a,b=Client(kind),Client(dest)
        Helpers.services={"source":NS(name="source",type=kind,instance=a),"target":NS(name="target",type=dest,instance=b)}
        p=cls(); p._recheck_torrents={}; p._is_recheck_running=False; p._event=Event()
        config=p.get_form()[1]
        config.update(enabled=False,autostart=False,notify=False,fromdownloader="source",todownloader="target",fromtorrentpath=str(root/"seeds"),frompath="/data",topath="/target")
        (root/"seeds").mkdir(exist_ok=True)
        config.update(overrides or {})
        p.init_plugin(config)
        torrent={"hash":"h","tags":"foo,bar","category":"music","save_path":"/data/folder","state":"pausedUP"} if kind=="qbittorrent" else NS(hashString="h",labels=["foo","bar"],download_dir="/data/folder")
        a.completed=[torrent]
        (root/"seeds"/"h.torrent").write_bytes(b"with-announce")
        for path in (root/"seeds"/"h.fastresume",settings.TEMP_PATH/"h.torrent"):
            path.unlink(missing_ok=True)
        return p,a,b,torrent,config

    record("TT-T002", lambda: [equal(fresh(overrides={"add_torrent_tags":s})[0]._torrent_tags,e) for s,e in [("a, b",["a"," b"]),("  a,b  ",["a","b"]),("   ",[""]),("",[])]])
    record("TT-T024", lambda:[equal(TT._TorrentTransfer__convert_save_path(*x),y) for x,y in [(("","/a","/b"),"/b"),(("/a/x","","/b"),"/a/x"),(("/a/x","/a",""),"/a/x"),(("/abc/x","/a","/b"),"/bbc/x"),(("/z/x","/a","/b"),None)]])

    def run_transfer(overrides=None, mutate=None, kind="qbittorrent", dest="qbittorrent", cls=TT):
        p,a,b,t,c=fresh(kind,dest,overrides,cls)
        if mutate: mutate(p,a,b,t,c)
        p.transfer()
        return p,a,b

    def add_count(result):
        return len([c for c in result[2].calls if c[0]=="add"])

    record("TT-T013",lambda:equal(add_count(run_transfer({"nopaths":"/data/fol"})),0))
    record("TT-T016",lambda:[equal(add_count(run_transfer({"includecategory":s})),v) for s,v in [("other,music",1),("other, music",0)]])
    record("TT-T017",lambda:[equal(add_count(run_transfer({"transferemptylabel":flag,"includelabels":"must"},lambda p,a,b,t,c:t.update(tags=""))),v) for flag,v in [(True,1),(False,0)]])
    record("TT-T018",lambda:[equal(add_count(run_transfer({"nolabels":s})),v) for s,v in [("x,bar",0),("x, bar",1)]])
    record("TT-T019",lambda:[equal(add_count(run_transfer({"includelabels":s})),v) for s,v in [("foo,bar",1),("foo,missing",0)]])

    def missing_before_dup():
        p,a,b=run_transfer({"deleteduplicate":True},lambda p,a,b,t,c:((root/"seeds"/"h.torrent").unlink(),setattr(b,"query",([{"hash":"h"}],False))))
        equal([x[0] for x in b.calls],[]);equal([x[0] for x in a.calls],["completed"])
        return {"destination_calls":[],"source_delete_calls":0}
    record("TT-T021",missing_before_dup)

    def dup_delete():
        p,a,b=run_transfer({"deleteduplicate":True},lambda p,a,b,t,c:setattr(b,"query",([{"hash":"h"}],False)))
        calls=[x for x in a.calls if x[0]=="delete"]
        equal(calls,[("delete",{"delete_file":False,"ids":["h"]})]);equal(p.saved,{})
        return {"delete":calls[0][1],"history":p.saved}
    record("TT-T022",dup_delete)

    def no_trackers():
        p,a,b=run_transfer(mutate=lambda p,a,b,t,c:((root/"seeds"/"h.torrent").write_bytes(b"without-announce"),(root/"seeds"/"h.fastresume").write_bytes(b"no-trackers")))
        equal(add_count((p,a,b)),1)
        equal([x[1]["content"] for x in b.calls if x[0]=="add"],[b"without-announce"])
        return {"forwarded_trackerless":True,"temp_exists":(settings.TEMP_PATH/"h.torrent").exists()}
    record("TT-T032",no_trackers)

    def trackers():
        p,a,b=run_transfer(mutate=lambda p,a,b,t,c:((root/"seeds"/"h.torrent").write_bytes(b"without-announce"),(root/"seeds"/"h.fastresume").write_bytes(b"many-trackers")))
        content=next(x[1]["content"] for x in b.calls if x[0]=="add")
        decoded=json.loads(content)
        equal(decoded["announce"],"a");equal(decoded["announce-list"],[["a","b"],["c"]]);equal((root/"seeds"/"h.torrent").read_bytes(),b"without-announce")
        return {"synthetic_codec_output":decoded,"source_unchanged":True}
    record("TT-T031",trackers)

    def tuple_false():
        p,a,b=run_transfer(mutate=lambda p,a,b,t,c:setattr(b,"add_result",(False,[])))
        equal(any(x[0]=="tag-id" for x in b.calls),True);equal(bool(p.saved),True)
        return {"false_tuple_still_lookup":True,"history_written":True}
    record("TT-T039",tuple_false)

    def verification_matrix():
        observations=[]
        for skip in (False,True):
            for auto in (False,True):
                p,a,b=run_transfer({"skipverify":skip,"autostart":auto},lambda p,a,b,t,c:setattr(b,"query",([{"hash":"new-hash","state":"checkingUP"}],False)) if False else None)
                # A nonempty duplicate query would skip the add; empty query on immediate
                # checker clears the queue, so inspect call paths, not final queue for auto.
                count=sum(x[0]=="recheck" for x in b.calls)
                equal(count,0 if skip else 1)
                if not auto: equal(bool(p._recheck_torrents),not skip)
                observations.append({"skip":skip,"auto":auto,"recheck_calls":count})
        return observations
    record("TT-T041",verification_matrix)

    def source_delete_history():
        p,a,b=run_transfer({"deletesource":True})
        equal([x[1] for x in a.calls if x[0]=="delete"],[{"delete_file":False,"ids":["h"]}])
        equal(p.saved,{"source-h":{"to_download":"target","to_download_id":"new-hash","delete_source":True,"delete_duplicate":False}})
        return p.saved
    record("TT-T043-T044",source_delete_history)

    def queue_case(query):
        p,a,b,*_=fresh();p._recheck_torrents={"target":["new-hash"]};b.query=query;p.check_recheck()
        return p._recheck_torrents["target"],p._is_recheck_running
    record("TT-T052",lambda:[equal(queue_case(query),expected) for query,expected in [((None,True),(["new-hash"],False)),(([],False),([],False)),(([],True),([],False))]])

    def start_false():
        p,a,b,*_=fresh();p._recheck_torrents={"target":["h1","h1","h2"]};b.query=([{"hash":"h1","state":"pausedUP"},{"hash":"h2","state":"checkingUP"}],False);p.check_recheck()
        equal(p._recheck_torrents["target"],["h2"])
        return {"start_calls":[x[1] for x in b.calls if x[0]=="start"],"remaining":p._recheck_torrents["target"]}
    record("TT-T053",start_false)

    def query_error_gate():
        p,a,b,*_=fresh();p._recheck_torrents={"target":["h"]};b.query=RuntimeError("synthetic client failure")
        try:p.check_recheck()
        except RuntimeError:pass
        else:raise AssertionError("expected error")
        equal(p._is_recheck_running,True)
        return {"gate_stuck":True,"queue_unchanged":p._recheck_torrents["target"]}
    record("TT-T054",query_error_gate)

    record("TT-T050",lambda:[equal(TT._TorrentTransfer__can_seeding({"state":s},"qbittorrent"),e) for s,e in [("pausedUP",True),("stoppedUP",True),("pausedDL",False),("checkingUP",False),("pausedup",False)]])
    record("TT-T051",lambda:[equal(TT._TorrentTransfer__can_seeding(NS(status=NS(stopped=s),percent_done=p),"transmission"),e) for s,p,e in [(True,1,True),(True,.999,False),(False,1,False)]])

    def one_shot():
        p,a,b,t,c=fresh(overrides={"onlyonce":True,"autostart":False})
        equal(c["onlyonce"],False);equal(p._scheduler.running,True);equal(p._scheduler.jobs[0][0:2],("transfer","date"))
        return {"scheduled":p._scheduler.jobs[0][0:2],"flag_persisted":p.effects[-1][1]["onlyonce"],"enabled":p._enabled}
    record("TT-T007",one_shot)

    def stop_retains():
        p,a,b,*_=fresh();p._recheck_torrents={"target":["h"]};p._is_recheck_running=True;p._scheduler=Scheduler();p._scheduler.running=True;p.stop_service()
        equal(p._recheck_torrents,{"target":["h"]});equal(p._is_recheck_running,True);equal(p._scheduler,None);equal(p._event.is_set(),False)
        return {"queue":p._recheck_torrents,"running_gate":True,"scheduler":None,"event":False}
    record("TT-T056",stop_retains)

    def four_types():
        result=[]
        for src in ("qbittorrent","transmission"):
            for dst in ("qbittorrent","transmission"):
                p,a,b=run_transfer(kind=src,dest=dst)
                add=next(x[1] for x in b.calls if x[0]=="add")
                equal(add["is_paused"],True);equal(add["download_dir"],"/target/folder");equal(len(p.saved),1)
                result.append({"from":src,"to":dst,"paused":True,"history":True})
        return result
    record("TT-SYNTHETIC-4TYPES",four_types)

    def clone():
        base,a,b=run_transfer(cls=TT);other,c,d=run_transfer(cls=CL)
        equal(TT.plugin_config_prefix,"torrenttransfer_");equal(CL.plugin_config_prefix,"torrenttransfermusic_")
        equal(base.saved,other.saved)
        return {"same_business_effects":True,"separate_class_identity":True,"platform_lifecycle_unverified":True}
    record("TT-T061-BUSINESS",clone)

files={p:hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() for p in ("categoryeditor/__init__.py","torrenttransfer/__init__.py","torrenttransfermusic/__init__.py")}
files["installed-host/app/modules/themoviedb/category.py"]=hashlib.sha256(host_path.read_bytes()).hexdigest()
output={"kind":"isolated-original-source-AST-with-synthetic-dependencies","source_hashes":files,"limitations":["Original plugin classes executed with synthetic host/client/scheduler/timezone/codec adapters; no app imports, live configuration, sockets, real messages or actual client mutations", "Codec is synthetic fixture dispatch/JSON encoding: does not verify bencode or YAML behavior", "No target implementation, browser, actual host or restart-process acceptance executed"],"passed":sum(o["status"]=="passed" for o in OBS),"failed":sum(o["status"]=="failed" for o in OBS),"observations":OBS}
path=HERE/"source-isolated-observations.json"
path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"passed":output["passed"],"failed":output["failed"],"evidence":str(path)}))
raise SystemExit(1 if output["failed"] else 0)

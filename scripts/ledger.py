#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py —— 投递台账本地桥接（v7 新增）

本脚本是「脚本层」与「云端资料库《BOSS投递台账》」之间的本地桥。
云端台账（database：lo6GPT9hiOeRMKFp41S1HZ 或运行环境中的同名节点）由
**运行本技能的智能体（AI）**负责读写（脚本跑在终端、拿不到资料库鉴权），
脚本只负责在本地落一份「去重种子」与「待同步队列」，把两端串起来：

  1. 投递前：智能体先从云端台账查到历史已投 jobId 集合，用
       `ledger.py seed <jobId数组JSON>`  写入本地 ledger_seen.json
     → _live_driver 的 _delivered_jids() 会合并它，实现「跨轮去重」，
       避免同一岗位在下一轮被重复投递。

  2. 投递后：cmd_deliver 成功时自动调用 `ledger.mark`，把这条投递记录
     追加进 ledger_pending.json（待同步队列）。

  3. 收尾：智能体读取 ledger_pending.json，把队列里的记录逐条写入云端
     台账（按「岗位ID」去重），再 `ledger.py flush` 清空本地队列。

用法：
  python scripts/ledger.py seed  '["jobId1","jobId2",...]'   # 播种历史已投 jobId
  python scripts/ledger.py mark  '<单条投递记录JSON>'          # 追加一条待同步记录
  python scripts/ledger.py peek                                # 查看待同步队列
  python scripts/ledger.py seen                                # 查看去重种子数量
  python scripts/ledger.py flush                               # 清空待同步队列（同步完成后）

工作目录：默认当前目录（受 BOSS_WORKDIR 环境变量控制，与其它脚本一致）。
"""
import os
import sys
import json
import time

WORKDIR = os.environ.get("BOSS_WORKDIR") or os.getcwd()
SEEN_FILE = os.path.join(WORKDIR, "ledger_seen.json")
PENDING_FILE = os.path.join(WORKDIR, "ledger_pending.json")


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def seed(jids):
    """把历史已投 jobId 集合写入去重种子（合并去重，不覆盖已有）。"""
    cur = set(_load(SEEN_FILE, []))
    cur.update(str(j) for j in jids if j)
    _save(SEEN_FILE, sorted(cur))
    return {"seeded_total": len(cur), "new": len(cur) - len(set(_load(SEEN_FILE, [])) - cur)}


def seen_jids():
    """返回当前去重种子里的全部 jobId（供 _live_driver 合并去重）。"""
    return set(_load(SEEN_FILE, []))


def mark(record):
    """把一条投递记录追加进待同步队列（按 jobId 去重，避免重复入队）。"""
    rec = dict(record or {})
    jid = rec.get("岗位ID") or rec.get("jobId") or ""
    if not jid:
        return {"ok": False, "reason": "记录缺少 jobId，无法入队"}
    queue = _load(PENDING_FILE, [])
    if any((r.get("岗位ID") or r.get("jobId")) == jid for r in queue):
        return {"ok": False, "reason": f"jobId {jid} 已在待同步队列", "dup": True}
    rec["jobId"] = jid
    queue.append(rec)
    _save(PENDING_FILE, queue)
    return {"ok": True, "pending_total": len(queue), "jobId": jid}


def peek():
    queue = _load(PENDING_FILE, [])
    return {"pending_total": len(queue), "records": queue}


def flush():
    _save(PENDING_FILE, [])
    return {"flushed": True}


def _main(argv):
    if not argv:
        print(json.dumps({"error": "缺少子命令：seed / mark / peek / seen / flush"}, ensure_ascii=False))
        return 1
    cmd = argv[0]
    if cmd == "seed":
        jids = json.loads(argv[1]) if len(argv) > 1 else []
        print(json.dumps(seed(jids), ensure_ascii=False))
    elif cmd == "mark":
        rec = json.loads(argv[1]) if len(argv) > 1 else {}
        print(json.dumps(mark(rec), ensure_ascii=False))
    elif cmd == "peek":
        print(json.dumps(peek(), ensure_ascii=False))
    elif cmd == "seen":
        print(json.dumps({"seen_total": len(seen_jids())}, ensure_ascii=False))
    elif cmd == "flush":
        print(json.dumps(flush(), ensure_ascii=False))
    else:
        print(json.dumps({"error": f"未知子命令：{cmd}"}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

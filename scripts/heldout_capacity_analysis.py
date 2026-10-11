"""Capacity and crossing-edge analysis of the held-out replay (run on the server, read-only).

Feeds Section 6.3: pinned-prefix size, C_{B,t}=B//2-|P|, forced wipes, delayed edges that
cross a compression, and the size of every origin a policy deletes versus C_{B,t}.
"""
import json, statistics as st
from collections import defaultdict, Counter
import sys
B=(sys.argv[1] if len(sys.argv)>1 else 'experiments/racc_deliverables_20260915/model_v2/rv1_heldout').rstrip('/')+'/'
def jl(p):
    with open(p) as f:
        for l in f:
            if l.strip(): yield json.loads(l)
groups=defaultdict(list)
for g in jl(B+'formal_dataset/groups.jsonl'): groups[g['stream_id']].append(g)
gidx={(g['stream_id'],g['group_index']):g for gl in groups.values() for g in gl}
dec={}
for r in jl(B+'formal_dataset/online_inputs.jsonl'): dec[(r['stream_id'],r['decision_action_event_id'])]=r['decision_group_index']
edges=[e for e in jl(B+'formal_dataset/strict_edges.jsonl')]
T=list(jl(B+'replay_delayed/triggers.jsonl'))
streams_replayed={t['stream_id'] for t in T}
pinned={}; liveafter={}
for v in jl(B+'replay_delayed/decision_views.jsonl'):
    k=(v['budget'],v['arm'],v['stream_id'])
    if k not in pinned and len(v['live_event_ids'])==2: pinned[k]=v['history_tokens']
    liveafter[(v['budget'],v['arm'],v['stream_id'],v['decision_action_event_id'])]=set(v['live_original_event_ids'])
P=[v for (b,a,s),v in pinned.items() if b==28672 and a=='Default-Recency']
print('pinned prefix streams',len(P),'median',st.median(P),'min',min(P),'max',max(P))
arms=sorted({t['arm'] for t in T})
delayed=[e for e in edges if e['distance_action_groups']>=2]
print('edges',len(edges),'delayed',len(delayed),'delayed in replayed streams',sum(e['stream_id'] in streams_replayed for e in delayed),'repos',len({e['repo'] for e in delayed}))
for b in (28672,57344):
  for a in arms:
    tt=[t for t in T if t['budget']==b and t['arm']==a]
    bys=defaultdict(list)
    for t in tt: bys[t['stream_id']].append(t)
    cross=0; lost_sizes=[]; covered=0; lostn=0
    caps=[]; forced=0; wipes=0
    for t in tt:
        k=(b,a,t['stream_id'])
        if k not in pinned: continue
        C=t['target_tokens']-pinned[k]; caps.append(C)
        fg=set(t['forgotten_event_ids']); la=liveafter.get((b,a,t['stream_id'],t['decision_action_event_id']),set())
        lg=[g for g in groups[t['stream_id']] if set(g['event_ids'])<=(fg|la)]
        if not lg: continue
        if all(set(g['event_ids'])<=fg for g in lg):
            wipes+=1
            if C<min(g['source_tokens'] for g in lg): forced+=1
    seen=set()
    for e in delayed:
        crossed=False
        for t in bys.get(e['stream_id'],[]):
            d=dec.get((e['stream_id'],t['decision_action_event_id']))
            if d is None or not (e['origin_group_index']<d<=e['consume_group_index']): continue
            crossed=True
            if set(e['origin_event_ids'])&set(t['forgotten_event_ids']) and (e['stream_id'],e['origin_group_index']) not in seen:
                seen.add((e['stream_id'],e['origin_group_index']))
                g=gidx[(e['stream_id'],e['origin_group_index'])]; C=t['target_tokens']-pinned[(b,a,e['stream_id'])]
                lostn+=1; covered+= g['source_tokens']>C; lost_sizes.append(g['source_tokens'])
        cross+=crossed
    print(b,a,'triggers',len(tt),'wipes',wipes,'forced(C=B/2-|P|)',forced,'cap med',st.median(caps) if caps else None,'max',max(caps) if caps else None,'neg',sum(c<0 for c in caps),'| crossing delayed',cross,'| origins deleted',lostn,'size>C',covered,'min size',min(lost_sizes) if lost_sizes else None)

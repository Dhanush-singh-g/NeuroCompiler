"""Explicit post-study partial-label view; raw timing study remains immutable."""
from src.benchmarks.paired import MENU,verify

POLICY={'version':1,'objective':'native CPU service time',
    'admission':'O3 control passes; per-candidate control passes; admit all signs',
    'aliases':'identical-to-O3 candidates have exact zero relative gain',
    'missing':'unqualified candidate target absent, never imputed as zero or a win',
    'cv':'all held-out predictions must have qualified outcomes for model selection',
    'scope':'post-study training-method revision; frozen development remains prospective'}


def partial_labels(raw):
    _,diagnostics=verify(raw)
    rows=[]
    for ident,m in raw['manifests'].items():
        d=diagnostics.get(ident)
        if not d or not d['cpu_control']['control_pass']:continue
        stats={'O3':d['outcomes']['O3']};missing=[]
        for c in list(MENU)[1:]:
            s=d['outcomes'].get(c)
            if m['aliases'][c]=='O3':stats[c]=d['outcomes']['O3']
            elif s and s.get('candidate_control',{}).get('control_pass'):stats[c]=s
            else:missing.append(c)
        rows.append({'case':ident,'family':m['family'],'features':m['features'],
                     'outcomes':stats,'unqualified_choices':missing})
    return rows

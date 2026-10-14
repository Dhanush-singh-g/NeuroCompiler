"""Collect complete controlled synthetic training menus; resumable."""
import argparse
import json
import random
from pathlib import Path

from src.benchmarks.compact import PROTOCOL, effect, measure_cell, save, summarize
from src.benchmarks.kernels import KERNEL_PROTOCOL, KERNELS, freeze_kernel, verify_kernel
from src.features.transform import FEATURE_NAMES, extract_manifest


def verify(report, complete=True):
    if report["protocol"] != KERNEL_PROTOCOL or report["runtime_protocol"] != PROTOCOL:
        raise ValueError("Kernel timing protocol changed")
    if complete and (not report["complete"] or set(report["manifests"]) != set(KERNELS)):
        raise ValueError("Incomplete kernel coverage")
    seen = set()
    for m in report["manifests"].values():
        verify_kernel(m)
    for r in report["records"]:
        key = (r["case"],r["choice"],r["role"],r["block"])
        if key in seen:
            raise ValueError("Duplicate cell")
        seen.add(key)
        m=report["manifests"][r["case"]]
        if not m["eligible"] or r["block"] not in range(PROTOCOL["blocks"]):
            raise ValueError("Cell outside qualified scope")
        if r["role"]=="qualification": pair=("O3","O3")
        elif r["role"]=="candidate_control": pair=(r["choice"],r["choice"])
        elif r["role"]=="effect": pair=("O3",r["choice"])
        else: raise ValueError("Unknown role")
        if (r["left"],r["right"])!=pair or r["choice"] not in m["aliases"] or m["aliases"][r["choice"]]!=r["choice"]:
            raise ValueError("Invalid cell comparison")
        for values in (r["left_seconds"],r["right_seconds"]):
            import numpy as np
            if len(values)!=PROTOCOL["pairs"] or not np.isfinite(values).all() or any(v<=0 for v in values):
                raise ValueError("Invalid timings")
    if complete:
        for name,m in report["manifests"].items():
            if not m["eligible"]: continue
            cells=[r for r in report["records"] if r["case"]==name]
            q=[r for r in cells if r["role"]=="qualification"]
            if len(q)!=4: raise ValueError("Missing qualification")
            if effect(q)["control_pass"]:
                for c in set(m["aliases"].values())-{"O3"}:
                    for role in ("effect","candidate_control"):
                        if sum(r["choice"]==c and r["role"]==role for r in cells)!=4:
                            raise ValueError("Incomplete menu")
        if report["labels"]!=summarize(report): raise ValueError("Raw label mismatch")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resume",action="store_true")
    args=p.parse_args()
    path=Path("results/kernel_train.json")
    if path.exists():
        if not args.resume:p.error("Output exists; use --resume")
        r=json.loads(path.read_text());verify(r,complete=r["complete"])
        if r["complete"]:print("Completed kernels verified; no timing repeated");return
    else:
        r={"protocol":KERNEL_PROTOCOL,"runtime_protocol":PROTOCOL,"complete":False,
           "manifests":{},"profiles":{},"records":[],"labels":[],"feature_names":FEATURE_NAMES,"static_cases":{}}
        save(path,r)
    for name in KERNELS:
        if name not in r["manifests"]:
            print("BUILD",name,flush=True)
            m=freeze_kernel(name,Path("data/processed/kernel_train")/name)
            r["manifests"][name]=m
            r["profiles"][name]={"eligible":m["eligible"],"seconds":m["calibration"][-1]["seconds"]}
            r["static_cases"][name]=extract_manifest(m)
            save(path,r)
            print("PROFILE",name,m["arguments"],m["eligible"],flush=True)
    rng=random.Random(KERNEL_PROTOCOL["seed"])
    done={(x["case"],x["choice"],x["role"],x["block"]) for x in r["records"]}
    for phase in ("qualification","candidates"):
        for block in range(PROTOCOL["blocks"]):
            jobs=[]
            for name,m in r["manifests"].items():
                if not m["eligible"]:continue
                if phase=="qualification":jobs.append((name,"O3","O3","qualification"))
                else:
                    q=[c for c in r["records"] if c["case"]==name and c["role"]=="qualification"]
                    if not effect(q)["control_pass"]:continue
                    for c in dict.fromkeys(m["aliases"].values()):
                        if c!="O3":jobs.extend([(name,c,c,"candidate_control"),(name,"O3",c,"effect")])
            rng.shuffle(jobs)
            for name,left,right,role in jobs:
                first=rng.choice([True,False]);choice=right if role=="effect" else left
                key=(name,choice,role,block)
                if key in done:continue
                r["records"].append(measure_cell(r["manifests"][name],left,right,block,role,first))
                done.add(key);save(path,r)
                print("CELL",len(done),phase,block,name,choice,role,flush=True)
    r["labels"]=summarize(r);r["complete"]=True;verify(r);save(path,r)
    print("COMPLETE",len(r["labels"]),"controlled synthetic menus",flush=True)


if __name__=="__main__":main()

"""Actual LLVM10 pass transitions; reward collection is deliberately separate.

LLVM verification checks IR structure, not semantic equivalence or speed.
This environment never executes submitted native programs.
"""
import hashlib
import subprocess
import time
from pathlib import Path

import numpy as np

from src.features.transform import METRICS, parse_ir, aggregate

ACTIONS = {'STOP': [], 'mem2reg':['-mem2reg'], 'instcombine':['-instcombine'],
           'simplifycfg':['-simplifycfg'], 'gvn':['-gvn'],
           'licm':['-loop-simplify','-lcssa','-licm'],
           'loop_unroll':['-loop-simplify','-loop-unroll'],
           'vectorize':['-loop-simplify','-loop-vectorize']}
FEATURE_NAMES = [f'log_module_{m}' for m in METRICS]+[f'count_{a}' for a in ACTIONS]+['remaining_steps']


class LLVMEnvironment:
    def __init__(self, llvm_bin, directory, horizon=4):
        self.tools=Path(llvm_bin);self.root=Path(directory)
        if not 1 <= horizon <= 12:raise ValueError('Use a bounded horizon of 1–12.')
        self.root.mkdir(parents=True,exist_ok=False)
        self.horizon=horizon;self.history=[];self.done=False;self.started=False

    def _run(self, args):
        result=subprocess.run(list(map(str,args)),capture_output=True,timeout=20)
        if result.returncode:raise ValueError(result.stderr.decode(errors='replace')[:4000])
        return result.stdout.decode()

    def reset(self, bitcode):
        if self.started:raise ValueError('Use a fresh environment for another episode.')
        self.current=self.root/'state0.bc';self.current.write_bytes(Path(bitcode).read_bytes())
        self._run([self.tools/'opt','-verify',self.current,'-disable-output'])
        self.done=False;self.started=True
        return self.observe()

    def observe(self):
        if not self.started:raise ValueError('Reset the environment first.')
        ir=self._run([self.tools/'llvm-dis',self.current,'-o','-'])
        functions=parse_ir(ir);counts=aggregate(functions,functions)
        features=[*np.log1p(counts).tolist(),*[float(self.history.count(a)) for a in ACTIONS],
                  float(self.horizon-len(self.history))]
        return {'features':features,'instructions':int(counts[0]),'history':list(self.history),
                'bitcode_sha256':hashlib.sha256(self.current.read_bytes()).hexdigest(),
                'available_actions':[] if self.done else list(ACTIONS),'done':self.done}

    def step(self, action):
        if self.done:raise ValueError('Episode is terminal.')
        if action not in ACTIONS:raise ValueError('Unknown LLVM action.')
        before=self.observe();start=time.perf_counter()
        if action!='STOP':
            target=self.root/f'state{len(self.history)+1}.bc'
            self._run([self.tools/'opt',*ACTIONS[action],'-verify-each',self.current,'-o',target])
            self.current=target
        elapsed=time.perf_counter()-start
        self.history.append(action);self.done=action=='STOP' or len(self.history)>=self.horizon
        after=self.observe()
        return {'before':before,'after':after,'action':action,'transform_verified':True,
                'compile_elapsed_seconds':elapsed,'native_execution':False,
                'reward':None,'scope':'A verified LLVM transition, not a runtime reward or semantic correctness proof.'}

"""Experimental fitted Q iteration over qualified compiler transitions.

This is an offline RL engine, not a runtime-qualified compiler policy. A real
collector must provide state/action/next-state rewards in a single objective.
"""
import numpy as np


class TransitionLearner:
    def __init__(self, actions, objective, gamma=.9, iterations=20, ridge=1.):
        if objective not in ('runtime', 'instruction_count'):
            raise ValueError('Specify runtime or instruction_count; objectives cannot be mixed.')
        if not actions or len(set(actions)) != len(actions) or 'STOP' not in actions:
            raise ValueError('Use unique actions including STOP.')
        if not 0 <= gamma < 1 or iterations < 1 or ridge <= 0:
            raise ValueError('Invalid learning parameters.')
        self.actions, self.objective = list(actions), objective
        self.gamma, self.iterations, self.ridge = gamma, iterations, ridge

    def fit(self, transitions):
        rows = list(transitions)
        if not rows:
            raise ValueError('No qualified transitions to train on.')
        for row in rows:
            if row['split'] != 'train':
                raise ValueError('Training must exclude validation/development/test programs.')
            if row['objective'] != self.objective:
                raise ValueError('Mixed reward objectives are forbidden.')
            if row['action'] not in self.actions or type(row['done']) is not bool:
                raise ValueError('Invalid action/terminal state.')
            if row['action'] == 'STOP' and not row['done']:
                raise ValueError('STOP must terminate an episode.')
            if not row.get('transform_verified'):
                raise ValueError('LLVM transformation verification is required.')
            if self.objective == 'runtime' and not all(row.get(k) is True for k in
                    ('correctness_passed', 'baseline_control_passed', 'candidate_control_passed')):
                raise ValueError('Runtime rewards require correctness and both timing controls.')
            if not row['done'] and (not row['next_actions'] or not set(row['next_actions']) <= set(self.actions)):
                raise ValueError('Nonterminal transitions require supported next actions.')
        contexts = {r['context_id'] for r in rows}
        if len(contexts) != 1:
            raise ValueError('Do not pool incompatible compiler/machine/reward contexts.')
        states = np.asarray([r['state'] for r in rows], dtype=float)
        following = np.asarray([r['next_state'] for r in rows], dtype=float)
        rewards = np.asarray([r['reward'] for r in rows], dtype=float)
        if (states.ndim != 2 or states.shape[1] == 0 or following.shape != states.shape
                or not all(np.isfinite(v).all() for v in (states, following, rewards))):
            raise ValueError('Invalid finite state/reward arrays.')
        self.center = states.mean(axis=0)
        self.scale = states.std(axis=0); self.scale[self.scale < 1e-8] = 1.
        x = self._features(states); nx = self._features(following)
        self.supported = [a for a in self.actions if any(r['action'] == a for r in rows)]
        if any(a not in self.supported for r in rows if not r['done'] for a in r['next_actions']):
            raise ValueError('Bellman targets cannot use globally unobserved actions.')
        self.immediate = self._regress(x, rewards, rows)
        self.q = {a: np.zeros(x.shape[1]) for a in self.supported}
        self.bellman_residuals = []
        for _ in range(self.iterations):
            target = rewards.copy()
            for i, row in enumerate(rows):
                if not row['done']:
                    target[i] += self.gamma * max(float(nx[i] @ self.q[a]) for a in row['next_actions'])
            updated = self._regress(x, target, rows)
            residual = np.mean([(float(x[i] @ updated[r['action']])-target[i])**2 for i,r in enumerate(rows)])
            self.bellman_residuals.append(float(residual)); self.q = updated
        self.programs = sorted({r['program'] for r in rows})
        self.context_id = next(iter(contexts)); self.rows = len(rows)
        return self

    def _features(self, values):
        x = np.atleast_2d(values)
        if x.shape[1] != len(self.center) or not np.isfinite(x).all():
            raise ValueError('State feature schema mismatch.')
        return np.column_stack([(x-self.center)/self.scale, np.ones(len(x))])

    def _regress(self, x, target, rows):
        models = {}
        for action in self.supported:
            positions = [i for i,r in enumerate(rows) if r['action'] == action]
            a, y = x[positions], target[positions]
            # Equal total weight per original program for each action.
            counts = {p:sum(rows[i]['program']==p for i in positions) for p in {rows[i]['program'] for i in positions}}
            weights = np.asarray([1/counts[rows[i]['program']] for i in positions])
            penalty = np.eye(a.shape[1])*self.ridge; penalty[-1,-1] = 1e-10
            models[action] = np.linalg.solve(a.T@(weights[:,None]*a)+penalty, a.T@(weights*y))
        return models

    def choose(self, state, mode='rl', top_k=2, available=None):
        if mode not in ('sl','rl','hybrid') or top_k < 1:
            raise ValueError('Choose sl, rl or hybrid and a positive top_k.')
        allowed = self.supported if available is None else [a for a in available if a in self.supported]
        if not allowed:
            raise ValueError('No supported legal action.')
        x = self._features(np.asarray(state,dtype=float))[0]
        immediate = {a:float(x@self.immediate[a]) for a in allowed}
        q = {a:float(x@self.q[a]) for a in allowed}
        candidates = allowed
        if mode == 'hybrid':
            candidates = sorted(allowed,key=lambda a:immediate[a],reverse=True)[:top_k]
            if 'STOP' in allowed and 'STOP' not in candidates:
                candidates.append('STOP')
        scores = immediate if mode == 'sl' else q
        return {'action':max(candidates,key=lambda a:scores[a]), 'mode':mode,
                'immediate_scores':immediate, 'q_scores':q, 'candidates':candidates,
                'objective':self.objective, 'deployment_qualified':False,
                'scope':'Experimental offline prediction. Q values are not confidence or measured speedups.'}

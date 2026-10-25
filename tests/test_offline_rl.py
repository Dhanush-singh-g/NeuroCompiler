import tempfile
import subprocess
from pathlib import Path
import unittest
from src.rl.offline import TransitionLearner


def transitions():
    def row(state,action,reward,next_state,done):
        return dict(state=[state],action=action,reward=reward,next_state=[next_state],done=done,
                    next_actions=[] if done else ['profit','STOP'],program='synthetic_unit_fixture',
                    split='train',objective='instruction_count',context_id='unit_fixture_only',transform_verified=True)
    return [row(0,'prepare',0,1,False),row(0,'profit',1,0,True),row(0,'STOP',0,0,True),
            row(1,'profit',2,1,True),row(1,'STOP',0,1,True)]


class OfflineRLTests(unittest.TestCase):
    def learner(self):
        return TransitionLearner(['prepare','profit','STOP'],'instruction_count',ridge=1e-6).fit(transitions())

    def test_future_reward_changes_the_decision(self):
        agent=self.learner()
        self.assertEqual(agent.choose([0],'sl')['action'],'profit')
        self.assertEqual(agent.choose([0],'rl')['action'],'prepare')
        self.assertEqual(agent.choose([0],'hybrid',top_k=2)['action'],'prepare')
        self.assertEqual(agent.choose([0],'hybrid',top_k=1)['action'],'profit')
        self.assertFalse(agent.choose([0])['deployment_qualified'])

    def test_runtime_proxy_and_holdout_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            TransitionLearner(['prepare','profit','STOP'],'runtime').fit(transitions())
        rows=transitions();rows[0]['split']='test'
        with self.assertRaises(ValueError):
            self.learner().fit(rows)

    def test_unqualified_runtime_and_mixed_contexts_are_rejected(self):
        rows=transitions()
        for r in rows:r['objective']='runtime'
        with self.assertRaises(ValueError):
            TransitionLearner(['prepare','profit','STOP'],'runtime').fit(rows)
        rows=transitions();rows[0]['context_id']='other'
        with self.assertRaises(ValueError):self.learner().fit(rows)

    def test_unsupported_actions_and_bad_states_are_rejected(self):
        agent=self.learner()
        with self.assertRaises(ValueError):agent.choose([float('nan')])
        with self.assertRaises(ValueError):agent.choose([0],available=['unseen'])
        rows=transitions();rows[0]['next_actions']=['missing']
        with self.assertRaises(ValueError):agent.fit(rows)


class LLVMTransitionTests(unittest.TestCase):
    def test_trained_proxy_modes_compile_and_preserve_output(self):
        from src.presentation.server import toolchain
        from src.presentation.worker import analyze,execute
        from src.hybrid.sequential import load_agent
        try:config=toolchain()
        except ValueError as error:raise unittest.SkipTest(str(error))
        agent,model,digest=load_agent()
        self.assertEqual(model['training_rows'],512)
        self.assertEqual(len(model['training_programs']),8)
        self.assertTrue(digest)
        for mode in ('sl','rl','hybrid'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as scratch:
                root=Path(scratch)
                request={**config,'source':'#include <stdio.h>\nint main(int argc,char**argv){int s=0;for(int i=0;i<argc*100;i++)s+=i;printf("%d\\n",s);return 0;}',
                         'arguments':['a','b'],'stdin':'','iterations':0,'policy_mode':mode}
                result=analyze(root,request)
                self.assertEqual(result['decision']['mode'],mode)
                self.assertEqual(result['decision']['sequential']['objective'],'instruction_count')
                self.assertLessEqual(len(result['decision']['sequential']['trace']),4)
                self.assertEqual(execute(root/'reference',request,root)['stdout_preview'],'44850\n')
                self.assertEqual(execute(root/'LearnedPolicy/program',request,root)['stdout_preview'],'44850\n')

    def test_real_pass_and_stop_without_native_execution(self):
        from src.presentation.server import toolchain
        from src.rl.llvm_environment import LLVMEnvironment,FEATURE_NAMES
        try:tools=Path(toolchain()['llvm_bin'])
        except ValueError as error:raise unittest.SkipTest(str(error))
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch);source=root/'input.c';source.write_text('int main(int argc,char**argv){return argc+0;}')
            bc=root/'initial.bc'
            subprocess.run([str(tools/'clang'),'-O1','-Xclang','-disable-llvm-passes','-emit-llvm','-c',str(source),'-o',str(bc)],check=True,capture_output=True)
            env=LLVMEnvironment(tools,root/'episode')
            initial=env.reset(bc);transition=env.step('mem2reg')
            self.assertEqual(len(initial['features']),len(FEATURE_NAMES))
            self.assertTrue(transition['transform_verified'])
            self.assertIsNone(transition['reward'])
            self.assertFalse(transition['native_execution'])
            stopped=env.step('STOP');self.assertTrue(stopped['after']['done'])
            with self.assertRaises(ValueError):env.step('gvn')
            with self.assertRaises(ValueError):env.reset(bc)

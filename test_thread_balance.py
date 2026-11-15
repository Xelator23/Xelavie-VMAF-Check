import copy
import os
import unittest
from unittest.mock import patch
import vmaf_dv as dv

class ThreadBalanceTests(unittest.TestCase):
    def setup_case(self):
        self.geometry={'ref':(3840,1608,0,276),'enc':(1920,802,0,4)}
        self.envs=[{'UNCHANGED':'ref'},{'UNCHANGED':'enc'}]
        self.audits=[{'mode':'optimized-cpu-dv-v2'} for _ in range(2)]

    def apply(self,system='nt',cpus=24,plan=None):
        with patch.object(dv.os,'name',system),patch.object(dv.os,'cpu_count',return_value=cpus):
            dv.balance_sparse_threads(self.geometry,{'total_frames':1440} if plan is None else plan,self.envs,self.audits)

    def test_asymmetric_job_limits_only_encode(self):
        self.setup_case();original=dict(os.environ);self.apply()
        self.assertEqual(self.envs,[{'UNCHANGED':'ref'},{'UNCHANGED':'enc','LP_NUM_THREADS':'4'}])
        self.assertEqual(os.environ,original)
        self.assertEqual(self.audits[1]['mesa_threads'],4)
        self.assertNotIn('mesa_threads',self.audits[0])

    def test_platform_and_cpu_guards(self):
        for system,cpus in [('posix',24),('nt',8),('nt',None)]:
            self.setup_case();before=copy.deepcopy((self.envs,self.audits));self.apply(system,cpus)
            self.assertEqual((self.envs,self.audits),before)

    def test_explicit_mesa_override_wins(self):
        for index in (0,1):
            for value in ('0','8','auto'):
                self.setup_case();self.envs[index]['LP_NUM_THREADS']=value
                before=copy.deepcopy((self.envs,self.audits));self.apply()
                self.assertEqual((self.envs,self.audits),before)

    def test_dense_or_non_dv_paths_unchanged(self):
        self.setup_case();self.apply(plan={});self.assertNotIn('LP_NUM_THREADS',self.envs[1])
        for index in (0,1):
            self.setup_case();self.audits[index]['mode']='classic'
            self.apply();self.assertNotIn('LP_NUM_THREADS',self.envs[1])
            self.setup_case();self.envs[index]=None
            before=copy.deepcopy((self.envs,self.audits));self.apply()
            self.assertEqual((self.envs,self.audits),before)

    def test_other_geometries_unchanged(self):
        for ref,enc in [((1920,1080,0,0),(1920,1080,0,0)),
                        ((3840,2160,0,0),(3840,2160,0,0)),
                        ((3840,800,0,0),(1920,1080,0,0))]:
            self.setup_case();self.geometry={'ref':ref,'enc':enc};self.apply()
            self.assertNotIn('LP_NUM_THREADS',self.envs[1])

if __name__=='__main__':unittest.main()

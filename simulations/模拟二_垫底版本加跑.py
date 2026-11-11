# 临时模拟二：前两遍垫底的几个版本加跑，用新的数验证。不发任何提问。
import numpy as np, json, sys, os
from scipy import stats as sst
P=os.path.join(os.environ['LIVENERF_REPO'],'')
d=json.load(open(P+'data/standard_panel.json'))
k8=[]
for fam in d['families'].values():
    for iid in fam['ids']:
        c=fam['calibration'][iid]; k8.append((c['confirm_passes'], c['confirm_samples']))
k8=np.array(k8,float); p0=(k8[:,0]+1)/(k8[:,1]+2)
V=39; I=78
def logit(p): return np.log(p/(1-p))
def sig(x): return 1/(1+np.exp(-x))
def shifted(p,dpts):
    if dpts==0: return p.copy()
    lo,hi=0.0,10.0
    for _ in range(60):
        mid=(lo+hi)/2
        if (p-sig(logit(p)-mid)).mean()<dpts/100: lo=mid
        else: hi=mid
    return sig(logit(p)-(lo+hi)/2)
def run(dpts, K, mode, m_sus, N, seed, alpha=0.025, R1=2):
    # mode 'full': 第三遍全部版本各 1 遍，垫底的 K 个再多跑 m_sus-1 遍（它们一共 m_sus 遍新的）
    # mode 'target': 只给垫底的 K 个各跑 m_sus 遍，另挑 6 个对照版本各跑 2 遍
    rng=np.random.default_rng(seed)
    Pm=np.repeat(p0[:,None],V,axis=1); bad=20
    if dpts>0: Pm[:,bad]=shifted(p0,dpts)
    tcrit=sst.t.ppf(1-alpha/K, I-1)
    sel=0; conf_bad=0; conf_any_false=0; anyconf=0
    lowdev=[]; rng_span=[]
    for n in range(N):
        Y1=(rng.random((I,R1,V))<Pm[:,None,:])
        acc=Y1.mean(axis=(0,1))
        lowdev.append(acc.min()-acc.mean()); rng_span.append(acc.max()-acc.min())
        sus=np.argsort(acc)[:K]
        if bad in sus: sel+=1
        if mode=='full':
            ref_versions=[v for v in range(V) if v not in sus]; ref_passes=1
        else:
            cand=[v for v in range(0,V,6) if v not in sus][:6]
            if len(cand)<6:
                extra=[v for v in range(3,V,6) if v not in sus and v not in cand]; cand=(cand+extra)[:6]
            ref_versions=cand; ref_passes=2
        ref=(rng.random((I,ref_passes,len(ref_versions)))<Pm[:,None,ref_versions]).mean(axis=(1,2))
        anyc=False
        for s in sus:
            fs=(rng.random((I,m_sus))<Pm[:,[s]]).mean(axis=1)
            dd=fs-ref
            t=dd.mean()/(dd.std(ddof=1)/np.sqrt(I))
            if t< -tcrit:
                anyc=True
                if s==bad and dpts>0: conf_bad+=1
                else: conf_any_false+=1
        anyconf+=anyc
    return {'真差几个点':dpts,'追几个':K,'做法':mode,'嫌疑版本新跑几遍':m_sus,'进了垫底名单':round(sel/N,3),'被验证为差':round(conf_bad/N,3),'把没问题的版本错判成差':round(conf_any_false/N,4),
            '两遍里垫底版本比平均低(点,中位)':round(-100*float(np.median(lowdev)),1),'两遍里最高最低相差(点,中位)':round(100*float(np.median(rng_span)),1)}
if __name__=='__main__':
    N=4000
    for mode,m in (('full',4),('target',4),('full',3),('target',6)):
        for dpts in (0,4,5,6,7,8,10,12):
            print(json.dumps(run(dpts,3,mode,m,N,7+dpts),ensure_ascii=False),flush=True)
    # 没有差别时，一遍、两遍、三遍下 39 个版本的最高最低差
    rng=np.random.default_rng(5)
    for R in (1,2,3):
        sp=[];lo=[]
        for n in range(4000):
            acc=(rng.random((I,R,V))<p0[:,None,None]).mean(axis=(0,1)); sp.append(acc.max()-acc.min()); lo.append(acc.mean()-acc.min())
        sp=np.array(sp)*100; lo=np.array(lo)*100
        print(json.dumps({'没有差别时 遍数':R,'最高减最低 中位':round(float(np.median(sp)),1),'最高减最低 95%的情况不超过':round(float(np.percentile(sp,95)),1),'垫底比平均低 中位':round(float(np.median(lo)),1),'垫底比平均低 95%不超过':round(float(np.percentile(lo,95)),1)},ensure_ascii=False),flush=True)

# 临时模拟：比较几种判法。只读作者公开的题单文件，不发任何提问。
import numpy as np, json, sys, time, os
P=os.path.join(os.environ['LIVENERF_REPO'],'')
d=json.load(open(P+'data/standard_panel.json'))
k8=[]
for fam in d['families'].values():
    for iid in fam['ids']:
        c=fam['calibration'][iid]; k8.append((c['confirm_passes'], c['confirm_samples']))
k8=np.array(k8,float)
def pvec(a):
    return (k8[:,0]+a)/(k8[:,1]+2*a)
if len(sys.argv)>1 and sys.argv[1]=='calib':
    for a in [0,0.5,1,1.5,2,3,4]:
        p=pvec(a); print('a',a,'mean p',round(p.mean(),4),'mean p(1-p)',round((p*(1-p)).mean(),4),'-> 一遍一个版本的波动(点)',round(100*np.sqrt((p*(1-p)).mean()/78),2))
    print('作者47天实测一遍的波动 4.87 点 -> mean p(1-p) 约', round(0.0487**2*78,4))
    sys.exit()
A=float(sys.argv[2]) if len(sys.argv)>2 else 2.0
p0=pvec(A)
V=39; I=78
starts=[];ends=[]
for a in range(V):
    for b in range(a,V):
        if not (a==0 and b==V-1):
            starts.append(a); ends.append(b)
starts=np.array(starts); ends=np.array(ends); nin=ends-starts+1
w=np.sqrt(nin*(V-nin)/V)
is_single=(nin==1); is_suffix=(ends==V-1)
def stats(acc):
    cs=np.concatenate([np.zeros(acc.shape[:-1]+(1,)), np.cumsum(acc,axis=-1)],axis=-1)
    tot=cs[...,-1:]
    sin=cs[...,ends+1]-cs[...,starts]
    diff=sin/nin-(tot-sin)/(V-nin)
    return diff, diff*w
def logit(p): return np.log(p/(1-p))
def sig(x): return 1/(1+np.exp(-x))
def shifted(p,dpts):
    if dpts==0: return p.copy()
    lo,hi=0.0,10.0
    for _ in range(60):
        mid=(lo+hi)/2
        drop=(p-sig(logit(p)-mid)).mean()
        if drop<dpts/100: lo=mid
        else: hi=mid
    return sig(logit(p)-(lo+hi)/2)
def run(name, affected, dpts, R, N, B, seed):
    rng=np.random.default_rng(seed)
    Pm=np.repeat(p0[:,None],V,axis=1)
    if dpts>0:
        ps=shifted(p0,dpts)
        for v in affected: Pm[:,v]=ps
    rej={'A_raw':0,'A_std':0,'scan':0,'A_std_dir':0,'scan_dir':0,'single_only':0,'step_std_only':0,'scan_hit':0}
    for n in range(N):
        Y=(rng.random((I,R,V))<Pm[:,None,:]).astype(np.int8)
        acc=Y.mean(axis=(0,1))
        diff,z=stats(acc)
        obs_scan=np.abs(z).max(); obs_step_std=np.abs(z[is_suffix]).max(); obs_step_raw=np.abs(diff[is_suffix]).max(); obs_single=np.abs(diff[is_single]).max()
        Yb=np.broadcast_to(Y,(B,I,R,V)).copy()
        Yp=rng.permuted(Yb,axis=-1)
        accp=Yp.mean(axis=(1,2))
        dp,zp=stats(accp)
        def pv(obs,arr): return (1+(arr>=obs-1e-12).sum())/(B+1)
        p_scan=pv(obs_scan,np.abs(zp).max(axis=1))
        p_step_std=pv(obs_step_std,np.abs(zp[:,is_suffix]).max(axis=1))
        p_step_raw=pv(obs_step_raw,np.abs(dp[:,is_suffix]).max(axis=1))
        p_single=pv(obs_single,np.abs(dp[:,is_single]).max(axis=1))
        # 两遍方向一样
        accr=Y.mean(axis=0)  # [R,V]
        dr,zr=stats(accr)
        def samedir(mask):
            idx=np.where(mask)[0]; j=idx[np.abs(z[mask]).argmax()]
            s=np.sign(diff[j]); return bool(np.all(np.sign(dr[:,j])==s)), j
        if p_step_raw<0.025 or p_single<0.025: rej['A_raw']+=1
        a_std=False; a_std_dir=False
        if p_step_std<0.025:
            a_std=True; ok,_=samedir(is_suffix); a_std_dir=a_std_dir or ok
            rej['step_std_only']+=1
        if p_single<0.025:
            a_std=True; ok,_=samedir(is_single); a_std_dir=a_std_dir or ok
            rej['single_only']+=1
        rej['A_std']+=a_std; rej['A_std_dir']+=a_std_dir
        if p_scan<0.05:
            rej['scan']+=1
            ok,j=samedir(np.ones(len(nin),bool))
            rej['scan_dir']+=ok
            if dpts>0:
                aff=set(affected); found=set(range(starts[j],ends[j]+1))
                if len(aff&found)/len(aff|found)>=0.5: rej['scan_hit']+=1
    out={k:round(v/N,3) for k,v in rej.items()}
    print(json.dumps({'情景':name,'差几个点':dpts,'遍数':R,'N':N,**out},ensure_ascii=False),flush=True)
if __name__=='__main__':
    N=int(sys.argv[3]) if len(sys.argv)>3 else 200
    B=int(sys.argv[4]) if len(sys.argv)>4 else 500
    sc=[('没有差别',[],0)]
    sc+=[('后21个版本整段变低',list(range(18,39)),x) for x in (2,3,4,5)]
    sc+=[('最后6个版本变低',list(range(33,39)),x) for x in (3,4,6)]
    sc+=[('单个版本变低',[20],x) for x in (8,10,12,15)]
    sc+=[('连着3个版本变低',[19,20,21],x) for x in (5,7,9)]
    sc+=[('中间连着13个版本变低',list(range(14,27)),x) for x in (3,4,5)]
    t0=time.time()
    for R in (2,3):
        for i,(nm,aff,x) in enumerate(sc):
            run(nm,aff,x,R,(N*3 if x==0 else N),B,1000*R+i)
    print('用时',round(time.time()-t0),'秒',flush=True)

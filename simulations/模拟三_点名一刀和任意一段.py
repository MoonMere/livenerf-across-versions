# 临时模拟三：点名的一刀（2.1.303 起）加任意连着的一段，照最后要用的线算。不发任何提问。
import numpy as np, json, sys, time, importlib.util
import os
spec=importlib.util.spec_from_file_location('sim1',os.path.join(os.path.dirname(os.path.abspath(__file__)),'模拟一_几种判法对比.py'))
ARGV=list(sys.argv); sys.argv=['sim1.py','lib','1']; s1=importlib.util.module_from_spec(spec); spec.loader.exec_module(s1)
V=39; I=78; NAMED=21   # 前 21 个是 2.1.280 到 2.1.302，后 18 个是 2.1.303 到 2.1.322
named_mask=(s1.starts==NAMED)&(s1.ends==V-1)
def run(name, affected, dpts, R, N, B, seed):
    rng=np.random.default_rng(seed)
    Pm=np.repeat(s1.p0[:,None],V,axis=1)
    if dpts>0:
        ps=s1.shifted(s1.p0,dpts)
        for v in affected: Pm[:,v]=ps
    c={'点名一刀@2%':0,'任意一段@2%':0,'任意一刀@2%':0,'单个版本@2%':0,'点名或任意一段':0,'任意一段@2%且方向一样且至少3点':0}
    for n in range(N):
        Y=(rng.random((I,R,V))<Pm[:,None,:]).astype(np.int8)
        acc=Y.mean(axis=(0,1)); diff,z=s1.stats(acc)
        Yp=rng.permuted(np.broadcast_to(Y,(B,I,R,V)).copy(),axis=-1); dp,zp=s1.stats(Yp.mean(axis=(1,2)))
        def pv(obs,arr): return (1+(arr>=obs-1e-12).sum())/(B+1)
        p_named=pv(abs(z[named_mask][0]),np.abs(zp[:,named_mask][:,0]))
        p_scan=pv(np.abs(z).max(),np.abs(zp).max(axis=1))
        p_step=pv(np.abs(z[s1.is_suffix]).max(),np.abs(zp[:,s1.is_suffix]).max(axis=1))
        p_single=pv(np.abs(z[s1.is_single]).max(),np.abs(zp[:,s1.is_single]).max(axis=1))
        a=p_named<0.02; b=p_scan<0.02
        c['点名一刀@2%']+=a; c['任意一段@2%']+=b; c['任意一刀@2%']+=(p_step<0.02); c['单个版本@2%']+=(p_single<0.02); c['点名或任意一段']+=(a or b)
        if b:
            j=np.abs(z).argmax(); dr,_=s1.stats(Y.mean(axis=0))
            if np.all(np.sign(dr[:,j])==np.sign(diff[j])) and abs(diff[j])>=0.03: c['任意一段@2%且方向一样且至少3点']+=1
    print(json.dumps({'情景':name,'差几个点':dpts,'遍数':R,'N':N,**{k:round(v/N,3) for k,v in c.items()}},ensure_ascii=False),flush=True)
if __name__=='__main__':
    R=int(ARGV[1]); N=int(ARGV[2]); B=int(ARGV[3])
    sc=[('没有差别',[],0)]
    sc+=[('从2.1.303起整段变低',list(range(21,39)),x) for x in (2,3,4,5)]
    sc+=[('从2.1.300起整段变低',list(range(18,39)),x) for x in (3,4,5)]
    sc+=[('2.1.300到2.1.312这13个变低',list(range(18,31)),x) for x in (3,4,5,6)]
    sc+=[('连着3个版本变低',[24,25,26],x) for x in (6,8,10)]
    sc+=[('单个版本变低',[25],x) for x in (10,12,15)]
    for i,(nm,aff,x) in enumerate(sc):
        run(nm,aff,x,R,(N*3 if x==0 else N),B,500*R+i)

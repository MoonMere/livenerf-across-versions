# 模拟四：去掉点名的一刀以后，「任意连着的一段」的线从 2% 放到 4%，看能看出多大的差别。不发任何提问。
# 用法：python3 这个文件 遍数 每种情景造几份数据 每份打乱几次
# 2026-11-11 中午写的。Soren 说 2.1.303 是发帖人的猜测，不该当成专门的判断点，所以重算。
import numpy as np, json, sys, importlib.util, os
spec=importlib.util.spec_from_file_location('sim1',os.path.join(os.path.dirname(os.path.abspath(__file__)),'模拟一_几种判法对比.py'))
ARGV=list(sys.argv); sys.argv=['sim1.py','lib','1']; s1=importlib.util.module_from_spec(spec); spec.loader.exec_module(s1)
V=39; I=78
def run(name, affected, dpts, R, N, B, seed):
    rng=np.random.default_rng(seed)
    Pm=np.repeat(s1.p0[:,None],V,axis=1)
    if dpts>0:
        ps=s1.shifted(s1.p0,dpts)
        for v in affected: Pm[:,v]=ps
    keys=['任意一段@2%','任意一段@4%','任意一段@4%且方向一样且至少3点','任意一段@5%','任意一段@5%且方向一样且至少3点']
    c={k:0 for k in keys}
    for n in range(N):
        Y=(rng.random((I,R,V))<Pm[:,None,:]).astype(np.int8)
        acc=Y.mean(axis=(0,1)); diff,z=s1.stats(acc)
        Yp=rng.permuted(np.broadcast_to(Y,(B,I,R,V)).copy(),axis=-1); dp,zp=s1.stats(Yp.mean(axis=(1,2)))
        p_scan=(1+(np.abs(zp).max(axis=1)>=np.abs(z).max()-1e-12).sum())/(B+1)
        j=np.abs(z).argmax(); dr,_=s1.stats(Y.mean(axis=0))
        ok=bool(np.all(np.sign(dr[:,j])==np.sign(diff[j])) and abs(diff[j])>=0.03)
        c['任意一段@2%']+=(p_scan<0.02)
        c['任意一段@4%']+=(p_scan<0.04)
        c['任意一段@5%']+=(p_scan<0.05)
        if p_scan<0.04 and ok: c['任意一段@4%且方向一样且至少3点']+=1
        if p_scan<0.05 and ok: c['任意一段@5%且方向一样且至少3点']+=1
    print(json.dumps({'情景':name,'差几个点':dpts,'遍数':R,'N':N,**{k:round(v/N,3) for k,v in c.items()}},ensure_ascii=False),flush=True)
if __name__=='__main__':
    R=int(ARGV[1]); N=int(ARGV[2]); B=int(ARGV[3])
    sc=[('没有差别',[],0)]
    sc+=[('从2.1.303起整段变低',list(range(21,39)),x) for x in (3,4,5)]
    sc+=[('从2.1.300起整段变低',list(range(18,39)),x) for x in (3,4,5)]
    sc+=[('2.1.300到2.1.312这13个变低',list(range(18,31)),x) for x in (3,4,5,6)]
    sc+=[('连着3个版本变低',[24,25,26],x) for x in (6,8,10)]
    sc+=[('最后6个版本变低',list(range(33,39)),x) for x in (4,6,8)]
    for i,(nm,aff,x) in enumerate(sc):
        run(nm,aff,x,R,(N*3 if x==0 else N),B,900*R+i)

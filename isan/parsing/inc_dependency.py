#!/usr/bin/python3
import collections
import pickle
import sys
import random
import isan.common.perceptrons as perceptrons
import isan.parsing.dep_codec as codec
"""
"""

class Defalt_Features:
    def set_raw(self,raw):
        """
        对需要处理的句子做必要的预处理（如缓存特征）
        """
        self.raw=raw
    def __call__(self,stat):
        ind,stack_top=stat
        top1,top2=stack_top
        s1_w,s1_t=None,None
        if top1:
            s1_w,s1_t=top1[2]
        s2_w,s2_t=None,None
        if top2:
            s2_w,s2_t=top2[2]
        q0_w,q0_t=self.raw[ind] if ind<len(self.raw) else (None,None)
        q1_w,q1_t=self.raw[ind+1] if ind+1<len(self.raw) else (None,None)
        
        fv=[('s1w',s1_w),('s1t',s1_t),('s1ws1t',s1_w,s1_t),
            ('s2w',s2_w),('s2t',s2_t),('s2ws2t',s2_w,s2_t),
            ('q0w',q0_w),('q0t',q0_t),('q0wq0t',q0_w,q0_t),
            ('s1ws2w',s1_w,s2_w),('s1ts2t',s1_t,s2_t),
            ('s1tq0t',s1_t,q0_t),('s1ws1ts2t',s1_w,s1_t,s2_t),
            ('s1ts2ws2t',s1_t,s2_w,s2_t),('s1ws1ts2w',s1_w,s1_t,s2_w),
            ('s1ws2ws2t',s1_w,s2_w,s2_t),('s1ws1ts2ws2t',s1_w,s1_t,s2_w,s2_t),
            ('s1tq0tq1t',s1_t,q0_t,q1_t),('s1ts2tq0t',s1_t,s2_t,q0_t),
            ('s1wq0tq1t',s1_w,q0_t,q1_t),('s1ws2tq0t',s1_w,s2_t,q0_t),
                ]
        return fv
        
class Model :
    """
    """
    @staticmethod
    def result_to_actions(result):
        stack=[]
        actions=[]
        #print(">>",result)
        record=[[ind,head,0] for ind,head in enumerate(result)]
        for ind,head,_ in record:
            if head!=-1:
                record[head][2]+=1
        for ind,head in enumerate(result):
            actions.append('s')
            stack.append([ind,result[ind],record[ind][2]])
            while len(stack)>=2:
                #print(stack)
                if stack[-1][2]==0 and stack[-1][1]!=-1 and stack[-1][1]==stack[-2][0]:
                    actions.append('l')
                    stack.pop()
                    stack[-1][2]-=1
                elif stack[-2][2]==0 and stack[-2][1]!=-1 and stack[-2][1]==stack[-1][0]:
                    actions.append('r')
                    stack[-2]=stack[-1]
                    stack.pop()
                    stack[-1][2]-=1
                else:
                    break
        return actions

    @staticmethod
    def actions_to_result(actions):
        ind=0
        stack=[]
        arcs=[]
        for a in actions:
            if a=='s':
                stack.append(ind)
                ind+=1
            elif a=='l':
                arcs.append((stack[-1],stack[-2]))
                stack.pop()
            elif a=='r':
                arcs.append((stack[-2],stack[-1]))
                stack[-2]=stack[-1]
                stack.pop()
        arcs.append((stack[-1],-1))
        arcs.sort()
        arcs=[x for _,x in arcs]
        return arcs

    def __init__(self):
        self.shift_weights=perceptrons.Features()#特征
        self.lreduce_weights=perceptrons.Features()#特征
        self.rreduce_weights=perceptrons.Features()#特征
        self.features=Defalt_Features()

    def cal_score(self,step):
        for stat,info in self.steps[step].items():
            for alpha in info['alphas']:
                alpha[0]=0
                alpha[1]=2
                #print(stat,alpha[:])
                pass
    def find_thrink(self,step):
        self.cal_score(step)
        for stat,info in self.steps[step].items():
            info['alphas'].sort(key=lambda x:x['c'],reverse=True)
        beam=[(info,stat) for stat,info in self.steps[step].items()]
        beam.sort(reverse=True,key=lambda x:x[0]['alphas'][0]['c'])
        beam=beam[:min(len(beam),4)]
        return [stat for _,stat in beam]

    def find_next(self,step):
        for k in self.find_thrink(step):
            fv=self.features(k)
            self._gen_next(step,k,fv)


    
    def _gen_next(self,step,stat,fv):
        ind,stack_top=stat
        stat_info=self.steps[step][stat]
        alphas=stat_info['alphas']
        betas=stat_info.setdefault('betas',{})
        predictors=stat_info['pi']
        c,v=alphas[0]['c'],alphas[0]['v']
        #shift
        if ind<len(self.raw):
            key=(ind+1,((ind,ind+1,self.raw[ind]),stack_top[0]))
            if key not in self.steps[step+1]:
                self.steps[step+1][key]={'pi':set(),'alphas':[]}
            new_stat_info=self.steps[step+1][key]
            new_stat_info['pi'].add((step,stat))
            xi=self.shift_weights(fv)
            new_stat_info['alphas'].append({
                        'c':c+xi,
                        'v':0,
                        'a':'s',
                        'p':((step,stat),)})
            betas['s']=[key]
        if stack_top[0]!=None and stack_top[1]!=None:
            right,left=stack_top

            for p_step,predictor in predictors:
                last_stat_info=self.steps[p_step][predictor]
                assert('betas' in last_stat_info)
                last_fv=self.features(predictor)
                last_xi=self.shift_weights(last_fv)
                last_c,last_v=last_stat_info['alphas'][0]['c'],last_stat_info['alphas'][0]['v']
                #left-reduce
                key=(ind,((left[0],right[1],left[2] ),predictor[1][1]))
                if key not in self.steps[step+1]:
                    self.steps[step+1][key]={'pi':set(),'alphas':[]}
                new_stat_info=self.steps[step+1][key]
                new_stat_info['pi'].update(last_stat_info['pi'])
                lamda=self.lreduce_weights(fv)
                delta=lamda+last_xi
                new_stat_info['alphas'].append({
                            'c':last_c+v+delta,
                            'v':last_v+v+delta,
                            'a':'l',
                            'p':((step,stat),(p_step,predictor))})
                betas['l']=[key]

                #right-reduce
                key=(ind,((left[0],right[1],right[2]),predictor[1][1]))
                if key not in self.steps[step+1]:
                    self.steps[step+1][key]={'pi':set(),'alphas':[]}
                new_stat_info=self.steps[step+1][key]
                new_stat_info['pi'].update(last_stat_info['pi'])
                rho=self.rreduce_weights(fv)
                delta=rho+last_xi
                new_stat_info['alphas'].append({
                            'c':last_c+v+delta,
                            'v':last_v+v+delta,
                            'a':'r',
                            'p':((step,stat),(p_step,predictor))})
                betas['r']=[key]

    def update(self,actions,training_step,delta):
        stat=None
        stack=[]
        ind=0
        raw=self.raw
        for action in actions:
            stat=(ind,(stack[-1] if len(stack)>0 else None,
                        stack[-2] if len(stack)>1 else None))
            #print(stat)
            fv=self.features(stat)
            
            if action=='s':
                self.shift_weights.updates(fv,delta,training_step)
                stack.append((ind,ind+1,raw[ind]))
                ind+=1
            else:
                left=stack[-2][0]
                right=stack[-1][1]
                if action=='l':
                    self.lreduce_weights.updates(fv,delta,training_step)
                    stack[-2]=(left,right,stack[-2][2])
                    stack.pop()
                if action=='r':
                    self.rreduce_weights.updates(fv,delta,training_step)
                    stack[-2]=(left,right,stack[-1][2])
                    stack.pop()

            

    def decode(self,raw):
        self.raw=raw
        self.features.set_raw(raw)
        self.steps=[{} for i in range(2*len(raw))]
        self.steps[0][(0,(None,None))]={'pi':set(),
                    'alphas':[{'c' : 0, 'v' : 0, 'a': None }]}#初始状态
        for i in range(len(raw)*2-1):
            self.find_next(i)
            for k in self.steps[i]:
                #print(i,k)
                pass
            
        stat=self.find_thrink(len(raw)*2-1)[0]
        step=len(raw)*2-1
        actions=[None for x in range(step)]
        stats=[None for x in range(step)]
        def find(step,stat,begin,end,actions):
            if begin==end: return
            info=self.steps[step][stat]
            alpha=info['alphas'][0]
            assert(end==len(actions)or 'betas' in info)
            action=alpha['a']
            actions[end-1]=alpha['a']
            if alpha['a']=='s': 
                last_ind,last_stat=alpha['p'][0]
                stats[last_ind]=last_stat
                return
            last,reduced=alpha['p']
            r_ind,r_stat=reduced
            last_ind,last_stat=last
            actions[r_ind]='s'
            stats[last_ind]=last_stat
            stats[r_ind]=r_stat
            find(r_ind,r_stat,begin,r_ind,actions)
            find(last_ind,last_stat,r_ind+1,end-1,actions)
        find(step,stat,0,step,actions)
        return actions    
    def average(self,step):
        
        self.shift_weights.average(step)
        self.lreduce_weights.average(step)
        self.rreduce_weights.average(step)
        pass

    def save(self,filename):
        file=open(filename,'bw')
        pickle.dump(self.shift_weights,file)
        pickle.dump(self.lreduce_weights,file)
        pickle.dump(self.rreduce_weights,file)
        file.close()
    def load(self,filename):
        file=open(filename,'rb')
        self.shift_weights=pickle.load(file)
        self.lreduce_weights=pickle.load(file)
        self.rreduce_weights=pickle.load(file)
        file.close()
        

def train(model,training):
    stats=model
    step=0
    for i in range(10):
        std,cor=0,0
        for ln,line in enumerate(open(training)):
            step+=1
            #if ln>100:break
            line=line.strip()
            sen=codec.decode(line)
            raw=[(word,tag) for word,tag,_,_ in sen]
            std_result=[x for _,_,x,_ in sen]
            #print(raw)
            rst_actions=stats.decode(raw)
            rst_result=stats.actions_to_result(rst_actions)
            std_actions=stats.result_to_actions(std_result)
            #print(std_result)
            #print(rst_result)
            #print(std_actions)
            #print(rst_actions)
            std+=len(std_result)
            cor+=sum(1 if s==r else 0 for s,r in zip(std_result,rst_result))
            if std_result!=rst_result:
                stats.update(rst_actions,step,-1)
                stats.update(std_actions,step,1)
        print(cor/std)
    model.average(step)

def test(model,test):
    stats=model
    std,cor=0,0
    for ln,line in enumerate(open(test)):
        line=line.strip()
        sen=codec.decode(line)
        raw=[(word,tag) for word,tag,_,_ in sen]
        std_result=[x for _,_,x,_ in sen]
        #print(raw)
        rst_actions=stats.decode(raw)
        rst_result=stats.actions_to_result(rst_actions)
        std_actions=stats.result_to_actions(std_result)
        std+=len(std_result)
        cor+=sum(1 if s==r else 0 for s,r in zip(std_result,rst_result))
    print(cor/std)

if __name__=="__main__":
    pass

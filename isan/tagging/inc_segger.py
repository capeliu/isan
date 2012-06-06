#!/usr/bin/python3
import collections
import pickle
import sys
import isan.tagging.codec as tagging_codec
import isan.tagging.eval as tagging_eval
import isan.common.perceptrons as perceptrons
"""
一个增量搜索模式的中文分词模块
"""

class Defalt_Atom_Action:
    def __init__(self):
        self.features=perceptrons.Features()#特征
    def set_raw(self,raw):
        """
        对需要处理的句子做必要的预处理（如缓存特征）
        """
        self.raw=raw
        self.uni_chars=list('###'+raw+'##')
        self.bi_chars=[(self.uni_chars[i],self.uni_chars[i+1]) for i in range(len(self.uni_chars)-1)]
    def _key_gen(self,span):
        raw=self.raw
        uni_chars=self.uni_chars
        bi_chars=self.bi_chars
        c_ind=span[0]+2
        ws_current=span[1]
        ws_left=span[2]
        fv=[
                ("ws",ws_left,ws_current),
                ("c",uni_chars[c_ind],ws_current),
                ("r",uni_chars[c_ind+1],ws_current),
                ('l',uni_chars[c_ind-1],ws_current),
                ("cr",bi_chars[c_ind],ws_current),
                ("lc",bi_chars[c_ind-1],ws_current),
                ("rr2",bi_chars[c_ind+1],ws_current),
                ("l2l",bi_chars[c_ind-2],ws_current),
            ]
        if len(span)>=4:
            w_current=raw[span[0]+1-span[3]:span[0]+1]
            fv.append(("w",w_current))
        return fv
        
    def __call__(self,stat):
        """
        返回一个动作的分数
        """
        return sum(self.features.get(cur,0) for cur in self._key_gen(stat))

    def update(self,stat,delta,step=0):
        """
        更新权重
        """
        self.features.updates(self._key_gen(stat),delta,step)

class Searcher:
    def __init__(self):
        self.sequence=[]
        self.beam_width=2
    def forward(self,model):
        """
        线性搜索
        value = [alphas,betas]
        alpha = [score, delta, action, link]
        """
        sequence=self.sequence
        del sequence[:]
        sequence.append({model.init():([(0,None,None,None)],[])})
        while True :
            beam={}
            for stat,alpha_beta in sequence[-1].items():
                for action,next_stat,value in model.gen_next(stat):
                    is_termed=model.is_termed(next_stat)
                    if next_stat not in beam:
                        beam[next_stat]=([],[])
                    beam[next_stat][0].append((alpha_beta[0][0][0]+value,value,action,stat))
            #sort alphas
            for k,v in beam.items():
                v[0].sort(reverse=True)
            #thrink beam
            beam=sorted(list(beam.items()),key=lambda x:x[1][0][0][0],reverse=True)
            beam=beam[:min(len(beam),self.beam_width)]
            sequence.append(dict(beam))
            if is_termed : break
        result=[]
        item=beam[0][1][0][0]
        self.best_score=item[0]
        ind=len(sequence)-2
        while True :
            if item[3]==None: break
            result.append(item[2])
            item=sequence[ind][item[3]][0][0]
            ind-=1
        result.reverse()
        return result
    def backward(self):
        """
        使用beta算法计算后向分数
        """
        sequence=self.sequence
        ind=len(sequence)-1
        for stat,alpha_beta in sequence[ind].items():#初始化最后一项的分数
            alpha_beta[1].append((0,None,None,None))
        while ind>0:
            for stat,alpha_beta in sequence[ind].items():
                alphas=alpha_beta[0]
                if not alpha_beta[1]: continue
                beta=alpha_beta[1][0][0]
                for score,delta,action,pre_stat in alphas:
                    sequence[ind-1][pre_stat][1].append((beta+delta,delta,action,stat))
            #排序
            for _,alpha_beta in sequence[ind-1].items():
                alpha_beta[1].sort(reverse=True)
            ind-=1
        
        #for i,d in enumerate(sequence):
        #    print(i,"===")
        #    for stat,alpha_beta in d.items():
        #        if alpha_beta[1]:
        #            print(alpha_beta[0][0][0]+alpha_beta[1][0][0])
        #input()

class Defalt_Actions:
    @staticmethod
    def actions_to_result(actions,raw):
        sen=[]
        cache=''
        for c,a in zip(raw,actions[1:]):
            cache+=c
            if a=='s':
                sen.append(cache)
                cache=''
        if cache:
            sen.append(cache)
        return sen
    @staticmethod
    def result_to_actions(y):
        actions=['s']
        for w in y:
            for i in range(len(w)-1):
                actions.append('c')
            actions.append('s')
        return actions

    
    def __init__(self,
                atom_action=Defalt_Atom_Action):
        self.sep_action=atom_action()
        self.com_action=atom_action()
        self.max_pos_size=1
        self.searcher=Searcher()
    def init(self):
        return (0,'|','|',0)
    def is_termed(self,stat):
        return stat[0]-1==len(self.raw)
    def gen_next(self,stat):
        ind,last,last2,wordl=stat
        yield 's',(ind+1,'s',last,wordl+1),self.sep_action(stat)
        yield 'c',(ind+1,'c',last,1),self.com_action(stat)
    def search(self,raw,std_actions=None):
        self.raw=raw
        self.sep_action.set_raw(raw)
        self.com_action.set_raw(raw)
        res=self.searcher.forward(self)
        self.searcher.backward()
        return res
    def update(self,x,std_actions,rst_actions,step):
        std_stat=self.init()
        rst_stat=self.init()
        for a,b in zip(rst_actions,std_actions):
            if a=='s':
                std_stat=self._separate_update(std_stat,-1,step=step)
            if a=='c':
                std_stat=self._combine_update(std_stat,-1,step=step)
            if b=='s':
                rst_stat=self._separate_update(rst_stat,1,step=step)
            if b=='c':
                rst_stat=self._combine_update(rst_stat,1,step=step)
    def average(self,step):
        self.sep_action.features.average(step)
        self.com_action.features.average(step)
    ### 私有函数 
    def _separate_update(self,stat,delta,step=0):
        ind,last,last2,wordl=stat
        self.sep_action.update(stat,delta,step)
        return (ind+1,'s',last,wordl+1)
    def _combine_update(self,stat,delta,step=0):
        ind,last,last2,wordl=stat
        self.com_action.update(stat,delta,step)
        return (ind+1,'c',last,1)

class Model:
    """
    模型
    """
    def __init__(self,model_file,actions=None):
        """
        初始化
        actions： 如果不设置，则读取已有模型。如果设置，就是学习新模型
        """
        if actions==None:
            file=open(model_file,"rb")
            self.actions=pickle.load(file)
            file.close()
        else:
            self.model_file=model_file
            self.actions=actions
            self.step=0
            
    def __call__(self,raw):
        """
        解码，读入生句子，返回词的数组
        """
        rst_actions=self.actions.search(raw)
        hat_y=self.actions.actions_to_result(rst_actions,raw)
        return hat_y
    def _learn_sentence(self,raw,y):
        """
        学习，根据生句子和标准分词结果
        """
        self.step+=1#学习步数加一
        std_actions=self.actions.result_to_actions(y)#得到标准动作
        rst_actions=self.actions.search(raw)#得到解码后动作
        hat_y=self.actions.actions_to_result(rst_actions,raw)#得到解码后结果
        if not (sum(len(x)for x in y)==sum(len(x)for x in hat_y)):
            print(y)
            print(hat_y)
        if y!=hat_y:#如果动作不一致，则更新
            self.actions.update(raw,std_actions,rst_actions,self.step)
        return hat_y
    def save(self):
        """
        保存模型
        """
        self.actions.average(self.step)
        file=open(self.model_file,'wb')
        pickle.dump(self.actions,file)
        file.close()
    def train(self,training_file,iteration=5):
        """
        训练
        """
        for it in range(iteration):#迭代整个语料库
            eval=tagging_eval.TaggingEval()#测试用的对象
            for line in open(training_file):#迭代每个句子
                y=tagging_codec.decode(line.strip())
                raw=''.join(y)
                hat_y=self._learn_sentence(raw,y)
                eval(y,hat_y)#学习它
            eval.print_result()#打印评测结果
    def test(self,test_file):
        """
        测试
        """
        eval=tagging_eval.TaggingEval()
        for line in open(test_file):
            y=tagging_codec.decode(line.strip())
            raw=''.join(y)
            hat_y=self(raw)
            eval(y,hat_y)
            #print(raw,self.actions.delta)
            #if not y==hat_y:
            #    input()
        eval.print_result()
if __name__=="__main__":
    train()
    test()

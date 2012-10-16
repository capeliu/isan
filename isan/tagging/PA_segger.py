from struct import Struct
import isan.tagging.eval as tagging_eval
import isan.tagging.cwstask as cwstask
import json
import random


"""
You do the best, we do the rest!

来看看如何建造一个中文分词模型
只需要编写最核心的代码，其它代码我都已经编好了
"""
class Segger:
    xa,xb=3,3
    """告诉isan，这是个什么task"""
    name='中文分词'
    
    """任务的输入和输出是什么，如何从数据文件中获得"""
    class codec:
        """编码、解码"""
        @staticmethod
        def decode(line):
            """从一行文本中，得到输入（raw）和输出（y）"""
            line=line.strip()
            if not line: return []
            if line[0]=='{':
                #data=json.loads(line)
                #if data['Y_b'][1]!=None : return None
                return json.loads(line)
            seq=[word for word in line.split()]
            raw=''.join(seq)
            
            #Y_b=sum((['c']*(len(w)-1)+['s'] for w in seq),['s'])

            return {'raw':raw,
                    'y':seq,
                    'Y_a' : None,
                    'Y_b' : None,
                    }
        def encode():
            pass

    """下面不妨给动作（一个unsigned char类型）定义一下名字
    分词中有两个动作：断与连"""
    sep=11
    com=22

    """告诉isan，有了输入和动作序列，输出该是什么"""
    def actions_to_result(self,actions,raw):
        last_sep=0
        sen=[]
        for i,a in enumerate(actions[1:]):
            if a==self.sep or i==len(actions)-2:
                sen.append(raw[last_sep:i+1])
                last_sep=i+1
        return sen
    
    """有了输出，需要怎样的动作序列才能得到"""
    def result_to_actions(self,y):
        return sum(([self.com]*(len(w)-1)+[self.sep] for w in y),[self.sep])

    """在isan中，状态是一个bytes对象，但Python中tuple好处理一些，
    在此规定一种从tuple到bytes对象的转换规则"""
    stat_fmt=Struct('hcchh')
    """分词搜索时的初始状态"""
    init_stat=stat_fmt.pack(*(0,b'0',b'0',0,0))


    def is_belong(self,y,Y):
        seq,intervals=Y

        if intervals :
            offset=0
            for w in y:
                r=intervals[offset][1]
                if r!=-1 and offset+len(w)>r : 
                    #print(y)
                    return False
                l=intervals[offset+len(w)][0]
                if l!=-1 and l>offset : return False
                offset+=len(w)
            return True
        if seq:
            
            actions=self.result_to_actions(y)
            #print(actions)
            #print(seq)
            for a,s in zip(actions,seq):
                if s and ((s=='s' and a!=self.sep) or (s=='c' and a!=self.com)) : 
                    #print("f")
                    return False
            #print("t")
            return True

    """根据当前状态，能产生什么动作，并且后续的状态是什么，就由这个函数决定了"""
    def gen_actions_and_stats(self,stat):
        ind,last,_,wordl,lwordl=self.stat_fmt.unpack(stat)
        if self.actions and self.actions[ind]:
            if self.actions[ind]=='s':
                return [(self.sep,self.stat_fmt.pack(ind+1,b'1',last,1,wordl))]
            else :
                return [(self.com,self.stat_fmt.pack(ind+1,b'2',last,wordl+1,lwordl))]
        if self.intervals :
            rtn=[]
            ll,lr=self.intervals[ind-wordl]
            rl,rr=self.intervals[ind]
            if lr!=-1 and lr<=ind :
                return [(self.sep,self.stat_fmt.pack(ind+1,b'1',last,1,wordl))]
            if rl!=-1 and ind-wordl<rl :
                return [(self.com,self.stat_fmt.pack(ind+1,b'2',last,wordl+1,lwordl))]
        return [(self.sep,self.stat_fmt.pack(ind+1,b'1',last,1,wordl)),
                (self.com,self.stat_fmt.pack(ind+1,b'2',last,wordl+1,lwordl))]

    """分词搜索时的初始状态"""
    def init(self):
        #self.init_stat,self.gen_actions_and_stats,self.gen_features=cwstask.new()
        _,_,self.gen_features=cwstask.new()
        pass
 


    """维特比解码中，状态根据动作而转移，
    有了动作序列，就能确定一个状态序列"""
    def actions_to_stats(self,actions):
        stat=self.init_stat
        for action in actions:
            yield stat
            for a,s in self._gen_actions_and_stats(stat):
                if action==a:
                    stat=s
        yield stat

    """根据当前状态，能产生什么动作，并且后续的状态是什么，就由这个函数决定了"""
    def _gen_actions_and_stats(self,stat):
        ind,last,_,wordl,lwordl=self.stat_fmt.unpack(stat)
        return [(self.sep,self.stat_fmt.pack(ind+1,b'1',last,1,wordl)),
                (self.com,self.stat_fmt.pack(ind+1,b'2',last,wordl+1,lwordl))]
    """这个函数用来在每次新到一个输入的时候，做一些预处理，一般为了加快特征向量生成的速度"""
    def set_raw(self,raw,Y=None):
        if Y:
            self.actions,self.intervals=Y
        else:
            self.actions,self.intervals=None,None
        self.raw=raw
        uni_chars=list(x.encode() for x in '###'+raw+'##')
        bi_chars=[uni_chars[i]+uni_chars[i+1]
                for i in range(len(uni_chars)-1)]
        self.uni_chars=uni_chars
        self.uni_fv=[]
        for ind in range(len(raw)+1):
            c_ind=ind+2
            self.uni_fv.append([])
            for ws_current in [b'0',b'1',b'2']:
                self.uni_fv[-1].append([
                    b"1"+uni_chars[c_ind]+ws_current,
                    b"2"+uni_chars[c_ind+1]+ws_current,
                    b'3'+uni_chars[c_ind-1]+ws_current,
                    b"a"+bi_chars[c_ind]+ws_current,
                    b"b"+bi_chars[c_ind-1]+ws_current,
                    b"c"+bi_chars[c_ind+1]+ws_current,
                    b"d"+bi_chars[c_ind-2]+ws_current,
                ])
        return


    """暂时忽略它"""
    def set_Y(self,Y):
        pass

    """告诉isan，一个状态能生成哪些特征向量，每个特征也是一个bytes类型，且其中不能有0"""
    def gen_features(self,span):
        span=self.stat_fmt.unpack(span)
        ind,ws_current,ws_left,sep_ind,sep_ind2=span

        w_current=self.raw[ind-sep_ind:ind]
        w_last=self.raw[ind-sep_ind-sep_ind2:ind-sep_ind]
        w_c_len=chr(len(w_current)+1).encode()
        w_l_len=chr(len(w_last)+1).encode()
        w_l=b' '
        w_r=b' '
        w2_l=b' '
        w2_r=b' '
        if(len(w_current)>0):
            w_l=w_current[0].encode()
            w_r=w_current[-1].encode()
        if(len(w_last)>0):
            w2_l=w_last[0].encode()
            w2_r=w_last[-1].encode()

        #bind=0
        #if ws_current==b'2':bind+=2
        #if ws_left==b'2':bind+=1
        fv=(self.uni_fv[ind][ws_current[0]-48]+
                #self.bi_fv[span[0]][(ws_current[0]-48)*3+ws_left[0]-48]+
                [ 
                #b"i"+self.identical[ind+2],
                b"0"+ws_current+ws_left,
                b"w"+w_current.encode(),
                b"l"+w_c_len,

                b"lw0"+w_l+w_c_len,
                b"lw-1"+w_r+w_c_len,

                b"w_0w_-1"+w_l+w_r,
                b"w2_-1w_-1"+w2_r+w_r,
                b"w_0c"+w_l+self.uni_chars[ind+3],
                b"w_-1c"+w_r+self.uni_chars[ind+3],

                b"wl2"+w_current.encode()+w_l_len,
                b"w2l"+w_last.encode()+w_c_len,
                #b"w2w"+w_last.encode()+b" "+w_current.encode(),
                #b'w2_-1cl'+w2_r+w_l_len+self.uni_chars[ind+3],


                #b"w_0cl"+w_l+self.uni_chars[ind+3]+w_c_len,
                #b"w_-1cl"+w_r+self.uni_chars[ind+3]+w_c_len,
                #b"w2_0l"+w2_l+w_c_len,
                #b"w2_-1l"+w2_r+w_c_len,
                #b"cl"+self.uni_chars[ind+3]+w_c_len,
                #b"l'l"+chr(len(w_current)+1).encode()+chr(len(w_last)+1).encode(),
                ]
                )
        #print(w_r,self.uni_chars[ind+2])
        return fv
    """最后告诉isan，如何评价模型的输出和标准答案的输出的好坏。具体可以看这个class"""
    Eval=tagging_eval.TaggingEval

#!/usr/bin/python3
"""
用于分词词性标注的评测和比较
"""

import time
import sys



class DiffToHTML:
    """
    用于生成HTML的diff文件的插件
    """
    def __init__(self,filename):
        self.html=open(filename,'w')
        self.line_no=0
    def __del__(self):
        self.html.close()
    def __call__(self,std,rst):
        self.line_no+=1
        #for b,w,t in std:
        print(std)
        cor=std&rst
        tag_std=set(std)
        seg_std={(b,w)for b,w,t in std}
        seg_rst={(b,w)for b,w,t in rst}
        if len(cor)==len(std):return
        html=[]
        for b,w,t in sorted(rst):
            if (b,w,t) in tag_std:
                html.append(w+"_"+t)
                continue
            if (b,w) in seg_std:
                html.append(w+"_<font color=red>"+t+"</font>")
                continue
            html.append("<font color=red>"+w+"_"+t+"</font>")
        print(' '.join(html),"<br/>",file=self.html)
        html=[]
        for b,w,t in sorted(std):
            if (b,w,t) in rst:
                continue
            if (b,w) in seg_rst:
                html.append(w+"_<font color=blue>"+t+"</font>")
                continue
            html.append("<font color=blue>"+w+"_"+t+"</font>")
        print(' '.join(html),"<br/><br/>",file=self.html)
        
"""
tagging_eval std rst
"""

def str_to_list_old(string):
    offset=0
    li=[]
    #print(string)
    for word, tag in [x.split('_') for x in string.split()]:
        li.append((offset,offset+len(word),tag))
        offset+=len(word)
    return li

def str_to_list(string):
    offset=0
    li=[]
    #print(string)
    for word, tag in [x.split('_') for x in string.split()]:
        li.append((offset,(word),tag))
        offset+=len(word)
    return li

class CrossBoundaryErrors(object):
    def __init__(self):
        self.value=0
    def __call__(self,std,rst):
        max_ind=max(e for b,e,t in std)
        boundaries=[0 for i in range(max_ind+1)]
        for b,e,t in std:
            boundaries[b]=1
            boundaries[e]=1
        for b,e,t in rst:
            if boundaries[b]==1 and boundaries[e]==1:
                continue
            if any(boundaries[i]==1 for i in range(b+1,e)):
                self.value+=1


class TaggingEval:
    """
    分词词性标注评测类
    """
    def get_prf(self,seg=False):
        """
        得到评测的结果，准确度、精确度和F1
        """
        cor=self.cor if seg==False else self.seg_cor
        p=cor/self.rst if self.rst else 0
        r=cor/self.std if self.std else 0
        f=2*p*r/(r+p) if (r+p) else 0
        return p,r,f
    def __init__(self,plugins=[],sep='_'):
        """
        初始化
        """
        self.otime=time.time()
        self.plugins=plugins
        self.std,self.rst=0,0
        self.cor,self.seg_cor=0,0
        self.sep=sep
        self.characters=0
        self.overlaps=0
        self.with_tags=False
    def print_result(self):
        """
        打印结果
        """
        time_used=time.time()-self.otime
        speed=self.characters/time_used

        cor=self.cor
        p=cor/self.rst if self.rst else 0
        r=cor/self.std if self.std else 0
        f=2*p*r/(r+p) if (r+p) else 0

        if self.with_tags :
            seg_cor=self.seg_cor
            p=seg_cor/self.rst if self.rst else 0
            r=seg_cor/self.std if self.std else 0
            seg_f=2*p*r/(r+p) if (r+p) else 0

        if self.with_tags :
            line=("标准: %d 输出: %d seg正确: %d 正确: %d seg_f1: \033[32;01m%.4f\033[1;m tag_f1: \033[32;01m%.4f\033[1;m ol: %d 时间: %.4f (%.0f字/秒)"
                        %(self.std,self.rst,self.seg_cor,self.cor,seg_f,f,self.overlaps,time_used,speed))
        else :
            line=("标准: %d 输出: %d 正确: %d f1: \033[32;01m%.4f\033[1;m ol: %d 时间: %.4f (%.0f字/秒)"
                        %(self.std,self.rst,self.cor,f,self.overlaps,time_used,speed))
        print(line,file=sys.stderr)
        sys.stderr.flush()
        
    def _set_based(self,std,rst):
        self.std+=len(std)
        self.rst+=len(rst)
        self.cor+=len(std&rst)
        self.characters+=sum(len(w)for _,w,_ in std)
        self.seg_cor+=len({(b,e) for b,e,t in std}&{(b,e) for b,e,t in rst})


        std=sorted(list(std))
        rst=sorted(list(rst))
        std_ind=0
        for b,w,*_ in rst :
            e=b+len(w)
            while std_ind < len(std) and std[std_ind][0]<b :
                std_ind += 1
            while std_ind < len(std) and std[std_ind][0]<e :
                bb=std[std_ind][0]
                ee=bb+len(std[std_ind][1])
                if bb>b and e>bb and ee>e :
                    self.overlaps+=1
                std_ind += 1

        #print(std,rst)
    
    def _to_set(self,seq):
        s=set()
        if type(seq[0])!=str:#word with tag
            self.with_tags=True
            offset=0
            for word,tag in seq:
                s.add((offset,word,tag))
                offset+=len(word)
        else:#only word
            offset=0
            for word in seq:
                s.add((offset,word,''))
                offset+=len(word)
        return s
    def __call__(self,std,rst,raw=None):
        if not std:return
        if not rst:return
        self._set_based(self._to_set(std),self._to_set(rst))
        for plugin in self.plugins:
            plugin(std,rst)

    def eval_files(self,std_file,rst_file):
        for g,r in zip(open(std_file),open(rst_file)):
            gl=sum(len(x.partition(self.sep)[0])for x in g.split())
            rl=sum(len(x.partition(self.sep)[0])for x in r.split())
            if(gl!=rl):
                print("---")
                print(g.strip())
                print(r.strip())
            assert(gl==rl)
            g=g.strip()
            r=r.strip()
            #print(g)
            #print(r)
            self(g.split(),r.split())
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="用于分词词性标注的评测和比较")
    parser.add_argument('std',help='被比较的标注结果')
    parser.add_argument('rst',help='用以比较的标注结果',nargs='?',default='-')
    parser.add_argument('-s','--separator',help='词和词性间的分隔符',dest='sep',default='_')
    parser.add_argument('-d','--diff',help='指定以html格式输出的显示差异的文件的名字',dest='diff_file')
    args=parser.parse_args()
    
    plugins=[]
    if args.diff_file!=None:
        plugins.append(DiffToHTML(args.diff_file))
    eval=TaggingEval(plugins,sep=args.sep)
    eval.eval_files(args.std,args.rst)
    p,r,f=eval.get_prf()
    sp,sr,sf=eval.get_prf(True)
    print(eval.std,eval.rst,eval.cor,"%.4f|%.4f|%.4f"%(p,r,f),"%.4f|%.4f|%.4f"%(sp,sr,sf))
    

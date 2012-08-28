#include <vector>
#include <map>
//#include <unordered_map>
//#include <ext/hash_map>
#include <algorithm>




template<class KEY,class ACTION,class SCORE>
struct Triple{
    KEY key;
    ACTION action;
    SCORE score;
};

template<class KEY,class ACTION,class SCORE>
class DFA_Beam_Searcher_Data{
public:
    virtual void gen_next(KEY&,std::vector<Triple<KEY,ACTION,SCORE> >&){std::cout<<"oh no\n";};
};



template<class KEY,class ACTION,class SCORE>
class DFA_Beam_Searcher{
public:
    
    
    struct Alpha{
        SCORE score;
        SCORE inc;
        ACTION last_action;
        KEY last_key;
        
    };
    
    struct State_Info{
        std::vector<Alpha> alphas;
        //betas
        
        
        void max_top(){
            if(alphas.size()==0){
                return;
            };
            int max_ind=0;
            for(int ind=1;ind<alphas.size();ind++){
                if (alphas[max_ind].score< alphas[ind].score){
                    max_ind=ind;
                }
            }
            Alpha tmp;
            if(max_ind){
                tmp=alphas[max_ind];
                alphas[max_ind]=alphas[0];
                alphas[0]=tmp;
            }
        };
    };
    typedef std::map<KEY,State_Info> my_map;
    //typedef __gnu_cxx::hash_map<KEY,State_Info,typename KEY::HASH> my_map;
    //bool state_comp_less(const std::pair<KEY,State_Info>& first, const std::pair<KEY,State_Info>& second) const{
    //    return first.second.alphas[0].score < second.second.alphas[0].score;
    //};
    class CompareFoo{
    public:
        bool operator()(const std::pair<KEY,SCORE>& first, const std::pair<KEY,SCORE>& second) const{
            return first.second > second.second;
        }
    } state_comp_greater;
    
    class CompareFoo2{
    public:
        bool operator()(const std::pair<KEY,SCORE>& first, const std::pair<KEY,SCORE>& second) const{
            return first.second < second.second;
        }
    } state_comp_less;
    
    int beam_width;
    DFA_Beam_Searcher_Data<KEY,ACTION,SCORE>* data;
    std::vector< my_map > sequence;
    
    
    
    DFA_Beam_Searcher(DFA_Beam_Searcher_Data<KEY,ACTION,SCORE>* data,int beam_width){
        this->beam_width=beam_width;
        this->data=data;
    };
    ~DFA_Beam_Searcher(){
        
    };
    
    void print_beam(std::vector<std::pair<KEY,State_Info> >& beam){
        for(int j=0;j<beam.size();j++){
            for(int i=0;i<beam[j].second.alphas.size();i++){
                std::cout<<j<<" "<<i<<" "<<(char)beam[j].second.alphas[i].last_action<<" "<<beam[j].second.alphas[i].score<<"\n";
            };
        }
        std::cout<<"\n";
    };
    
    void thrink(int step,std::vector<std::pair<KEY,SCORE> >& top_n){
        top_n.clear();
        
        my_map* map=&(this->sequence[step]);
        typename my_map::iterator it;
        for (it=map->begin() ; it != map->end(); ++it ){
            it->second.max_top();
            //std::cout<<"in thrink "<<it->second.alphas.size()<<"\n";
            if (top_n.size()<this->beam_width){//if top_n is not full
                top_n.push_back(std::pair<KEY,SCORE>((*it).first,(*it).second.alphas[0].score));

                if(top_n.size()==this->beam_width){//full, make this a (min)heap
                    make_heap(top_n.begin(),top_n.end(),state_comp_greater);
                }
            }else{
                
                if(top_n.front().second<(*it).second.alphas[0].score){//greater than the top of the heap
                    pop_heap(top_n.begin(),top_n.end(),state_comp_greater);
                    top_n.pop_back();
                    top_n.push_back(std::pair<KEY,SCORE>((*it).first,(*it).second.alphas[0].score));
                    push_heap(top_n.begin(),top_n.end(),state_comp_greater);
                }
            }
        };
    };
    std::vector<ACTION> call(KEY& init_key,int steps){
        std::vector<std::pair<KEY,SCORE> > beam;
        std::vector<Triple<KEY,ACTION,SCORE> > nexts;
        
        this->sequence.clear();
        this->sequence.push_back(my_map());
        
        this->sequence.back()[init_key]=State_Info();
        this->sequence.back()[init_key].alphas.push_back(Alpha());
        this->sequence.back()[init_key].alphas[0].score=0;
        
        for(int step=0;step<steps;step++){
            thrink(step,beam);//thrink, get beam
            //print_beam(beam);
            this->sequence.push_back(my_map());
            //gen_next
            for(int i=0;i<beam.size();i++){
                KEY last_key=beam[i].first;
                SCORE last_score=beam[i].second;
                //std::cout<<last_state_info.alphas.size()<<"\n";

                this->data->gen_next(last_key,nexts);
                
                for(int j=0;j<nexts.size();j++){
                    KEY key=nexts[j].key;
                    if (!this->sequence.back().count(key)){
                        this->sequence.back()[key]=State_Info();
                    }
                    this->sequence.back()[key].alphas.push_back(Alpha());
                    
                    Alpha& alpha=this->sequence.back()[key].alphas.back();
                    
                    alpha.last_action=nexts[j].action;
                    alpha.inc=nexts[j].score;
                    alpha.score=last_score+nexts[j].score;
                    alpha.last_key=last_key;
                };
            };
        };
        
        
        //make result
        thrink(steps,beam);
        sort(beam.begin(),beam.end(),state_comp_less);
        Alpha item=sequence[steps][beam.back().first].alphas[0];

        std::vector<ACTION> result;
        result.resize(steps);
        int ind=steps-1;
        while(ind>=0){
            //std::cout<<ind<<" "<<item.last_action<<"\n";
            result[ind]=item.last_action;
            item=sequence[ind][item.last_key].alphas[0];
            ind--;
        };
        return result;
    };
    
};

int main(){
    return 0;
};

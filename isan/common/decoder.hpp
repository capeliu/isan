#pragma once

#include "isan/common/common.hpp"
#include "isan/common/weights.hpp"
#include "isan/common/searcher.hpp"

namespace isan{



class General_Searcher_Data : 
        public Searcher_Data<Alpha_Type>{
public:

    Feature_Generator * feature_generator;
    State_Generator * shifted_state_generator;
    Reduced_State_Generator * reduced_state_generator;
    Early_Stop_Checker * early_stop_checker;

    std::map<Action_Type, Default_Weights* > actions;

    //cache for FV
    State_Type cached_state;
    std::map<Action_Type, Score_Type> cached_scores;
    Feature_Vector fv;

    General_Searcher_Data(
            Early_Stop_Checker * early_stop_checker,
            State_Generator *shifted_state_generator,
            Feature_Generator * feature_generator){
        this->early_stop_checker=early_stop_checker;
        this->feature_generator=feature_generator;
        this->shifted_state_generator=shifted_state_generator;
        this->reduced_state_generator=NULL;
        this->use_early_stop=false;
        if(this->early_stop_checker)this->use_early_stop=true;
        cached_state=State_Type();
    };
    General_Searcher_Data(
            Early_Stop_Checker * early_stop_checker,
            State_Generator *shifted_state_generator,
            Reduced_State_Generator *reduced_state_generator,
            Feature_Generator* feature_generator){
        this->use_early_stop=true;
        this->early_stop_checker=early_stop_checker;
        this->shifted_state_generator=shifted_state_generator;
        this->reduced_state_generator=reduced_state_generator;
        this->feature_generator=feature_generator;
        cached_state=State_Type();
    };
    ~General_Searcher_Data(){
        for(auto iter=actions.begin();
            iter!=actions.end();
            ++iter){
            delete iter->second;
        }
    };

    virtual bool early_stop(
            int step,
            const std::vector<Alpha_Type*>& last_alphas,
            const std::vector<State_Type>& states
            ){
        return (*early_stop_checker)(
                step,
                last_alphas,
                states);
    };

    inline void shift(
            const int& ind,
            State_Type& state, 
            std::vector<Action_Type>& next_actions,
            std::vector<int>& next_inds,
            std::vector<State_Type>& next_states,
            std::vector<Score_Type>& scores
            ){

        next_inds.clear();
        if(!(cached_state==state)){
            (*feature_generator)(state,fv);
            //std::cout<<fv.size()<<"\n";
            cached_state=state;
            cached_scores.clear();
        }
        (*shifted_state_generator)(ind,state,next_actions,next_inds,next_states);
        scores.resize(next_actions.size());
        for(int i=0;i<next_actions.size();i++){
            auto action=next_actions[i];
            auto got=actions.find(action);
            if(got==actions.end()){
                actions[action]=new Default_Weights();
            };
            scores[i]=(*actions[action])(fv);
        };

        if (next_states.size()==next_inds.size()) return;
        std::cout<<"oh no!"<<"\n";
        
        next_inds.resize(actions.size());
        for(int i=0;i<actions.size();++i){
            if ( ind+1 ==max_step){
                next_inds[i]=-1;
            }else{
                next_inds[i]=ind+1;
            }
        }
    };
    void reduce(
            const State_Type& state, 
            const State_Type& predictor,
            std::vector<Action_Type>& next_actions,
            std::vector<State_Type>& next_states,
            std::vector<Score_Type>& scores
            ){
        if(!(cached_state==state)){
            (*feature_generator)(state,fv);
            cached_state=state;
            cached_scores.clear();
        };
        (*reduced_state_generator)(state,predictor,next_actions,next_states);
        scores.resize(next_actions.size());
        for(int i=0;i<next_actions.size();i++){
            auto action=next_actions[i];
            auto got=actions.find(action);
            if(got==actions.end()){
                actions[action]=new Default_Weights();
            };
            auto got2=cached_scores.find(action);
            if(got2!=cached_scores.end()){
                scores[i]=got2->second;
            }else{
                cached_scores[action]=scores[i]=(*actions[action])(fv);
            }
        };
    };
};

class Interface{
    typedef Searcher<State_Info_Type > My_Searcher;
public:
    State_Type init_state;
    int beam_width;
    General_Searcher_Data * data;

    My_Searcher * push_down;
    
    State_Generator * shifted_state_generator;
    Reduced_State_Generator * reduced_state_generator;
    Feature_Generator * feature_generator;
    Early_Stop_Checker * early_stop_checker;
    
    Chinese* raw;
    
    Interface(State_Type init_state,int beam_width,
            PyObject * py_early_stop_callback,
            PyObject * py_shift_callback,
            PyObject * py_reduce_callback,
            PyObject * py_feature_cb
            ){
        shifted_state_generator=new Python_State_Generator(py_shift_callback);
        reduced_state_generator=new Python_Reduced_State_Generator(py_reduce_callback);
        feature_generator=new Python_Feature_Generator(py_feature_cb);
        early_stop_checker=new Python_Early_Stop_Checker(py_early_stop_callback);

        this->init_state=init_state;
        this->beam_width=beam_width;
        this->data=new General_Searcher_Data(
                early_stop_checker,
                shifted_state_generator,
                reduced_state_generator,
                feature_generator);
        this->push_down=new My_Searcher(this->data,beam_width);

    };
    Interface(int beam_width,
            PyObject * py_early_stop_callback,
            PyObject * py_shift_callback,
            PyObject * py_feature_cb
            ){
        if(PyLong_Check(py_shift_callback)){
            shifted_state_generator=(State_Generator *) PyLong_AsUnsignedLong(py_shift_callback);
        }else{
            shifted_state_generator=new Python_State_Generator(py_shift_callback);
        };
        if(PyLong_Check( py_feature_cb)){
            feature_generator=(Feature_Generator*) PyLong_AsUnsignedLong( py_feature_cb);
        }else{
            feature_generator=new Python_Feature_Generator( py_feature_cb);
        };
        

        early_stop_checker=NULL;
        if(py_early_stop_callback!=Py_None){
            early_stop_checker=new Python_Early_Stop_Checker(py_early_stop_callback);
        }
        reduced_state_generator=NULL;
        raw=NULL;
        this->data=new General_Searcher_Data(
                early_stop_checker,
                shifted_state_generator,
                feature_generator);

        this->beam_width=beam_width;
        this->push_down=new My_Searcher(this->data,beam_width);

    };
    
    void set_raw(Chinese& raw){
        if(this->raw)delete this->raw;
        this->raw=new Chinese(raw);
        this->shifted_state_generator->raw=this->raw;
        this->feature_generator->set_raw(this->raw);
    }

    ~Interface(){
        delete this->data;
        delete this->push_down;
        delete feature_generator;
        delete shifted_state_generator;
        delete early_stop_checker;
        if(reduced_state_generator)
            delete reduced_state_generator;
    };
};

};//isan

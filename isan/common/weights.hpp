#pragma once
#include <vector>
#include <ext/hash_map>
#include <map>
#include "isan/common/common.hpp"


namespace isan{

template<class KEY,class VALUE>
class Weights{
public:
    typedef __gnu_cxx::hash_map<KEY,VALUE,typename KEY::HASH> Map;
    //typedef std::map<KEY,VALUE> Map;
    Map* map;
    Map* acc_map;
    Map* backup;

    Weights(){
        map=new Map();
        acc_map=new Map();
        backup=NULL;

    };
    ~Weights(){
        delete map;map=NULL;
        delete acc_map;acc_map=NULL;
        delete backup;backup=NULL;

    };
    
    void update(const std::vector<KEY>& fv,
            VALUE delta,
            int step){
        typename Map::iterator got;
        VALUE sd=step*delta;
        for(int i=0;i<fv.size();i++){
            const KEY& key=fv[i];
            got=map->find(key);
            if(got==map->end()){
                (*map)[key]=delta;
                if(acc_map)(*acc_map)[key]=sd;
            }else{
                got->second+=delta;
                if(acc_map)(*acc_map)[key]+=sd;
            };
        };
    };
    VALUE operator()(const std::vector<KEY>& fv){
        typename Map::const_iterator got;
        VALUE value=0;
        for(int i=0;i<fv.size();i++){
            got = map->find(fv[i]);
            if(got!=map->end()){
                value+=got->second;
            }else{
            }
        };
        return value;
    };
    void average(int step){
        if(backup)delete backup;
        this->backup=this->map;
        this->map=new Map();
        typename Map::iterator it;
        for(it=acc_map->begin();it!=acc_map->end();++it){
            const KEY& key=(*it).first;
            VALUE value=(*it).second;
            (*map)[key]=(VALUE)
                    (
                        ((double)((*backup)[key]-value/step))*1000
                        +0.5
                    );
        };
    };
    void un_average(){
        delete map;
        map=backup;
        backup=NULL;
    };
};
class Default_Weights : public Weights<Feature_String ,Score_Type>{
public:
    PyObject * to_py_dict(){
        PyObject * dict=PyDict_New();
        //
        for(auto it=map->begin();it!=map->end();++it){
            PyObject * key=PyBytes_FromStringAndSize(it->first.pt,it->first.length);
            PyObject * value=PyLong_FromLong(it->second);
            PyDict_SetItem(dict,key,value);
            Py_DECREF(key);
            Py_DECREF(value);
        };
        
        return dict;
    };
    Default_Weights(){
    }
    Default_Weights(PyObject * dict){
        PyObject *key, *value;
        Py_ssize_t pos = 0;
        
        char* buffer;
        size_t length;
        while (PyDict_Next(dict, &pos, &key, &value)) {
            PyBytes_AsStringAndSize(key,&buffer,(Py_ssize_t*)&(length));
            (*map)[Feature_String(buffer,length)]=PyLong_AsLong(value);
        };
    };
};

};//isan

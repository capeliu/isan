#include <Python.h>
#include "isan/common/common.hpp"
#include "isan/common/decoder.hpp"

#define __INIT_FUNC(a,b) a##b
#define INIT_FUNC(a,b) __INIT_FUNC(a,b)
#define PYINIT PyInit_
#define STR(x) #x


namespace isan{

static PyObject *
interface_delete(PyObject *self, PyObject *arg){
    delete (Interface*)PyLong_AsLong(arg);
    Py_INCREF(Py_None);
    return Py_None;
};

static PyObject *
set_raw(PyObject *self, PyObject *arg)
{
    Interface* interface;
    PyObject *new_raw;
    PyArg_ParseTuple(arg, "LO", &interface,&new_raw);
    if(!PyUnicode_Check(new_raw)){
        Py_INCREF(Py_None);
        return Py_None;
        
    };
    long raw_size=PySequence_Size(new_raw);
    
    Chinese raw(raw_size);
    for(int i=0;i<raw_size;i++){
        PyObject *tmp=PySequence_GetItem(new_raw,i);
        raw.pt[i]=(Chinese_Character)*PyUnicode_AS_UNICODE(tmp);
        Py_DECREF(tmp);
    }
    interface->set_raw(raw);
    Py_INCREF(Py_None);
    
    return Py_None;
};
static PyObject *
set_step(PyObject *self, PyObject *arg)
{
    Interface* interface;
    PyObject *new_raw;
    long step=0;
    
    PyArg_ParseTuple(arg, "LL", &interface,&step);
    
    interface->data->learning_step=step;
    Py_INCREF(Py_None);
    
    return Py_None;
};
static PyObject *
do_nothing(PyObject *self, PyObject *arg)
{
    Py_INCREF(Py_None);
    return Py_None;
};



static PyObject *
search(PyObject *self, PyObject *arg)
{

    Interface* interface;
    PyObject *py_init_states;
    PyArg_ParseTuple(arg, "LO", &interface,&py_init_states);

    std::vector<State_Type> init_states;
    for(int i=0;i<PyList_GET_SIZE(py_init_states);i++){
        init_states.push_back(State_Type(PyList_GET_ITEM(py_init_states,i)));
    };

    std::vector<Alpha_Type* > result_alphas;

    (*interface->push_down)(
            init_states,
            result_alphas);
    PyObject * rtn_list=PyList_New(result_alphas.size());
    for(int i=0;i<result_alphas.size();i++){
        PyList_SetItem(rtn_list,i,pack_alpha(result_alphas[i]));
    }
    return rtn_list;
};

static PyObject *
get_states(PyObject *self, PyObject *arg)
{
    Interface* interface;
    PyArg_ParseTuple(arg, "L", &interface);
    interface->push_down->cal_betas();

    std::vector<State_Type > states;
    std::vector<Score_Type> scores;

    interface->push_down->get_states(states,scores);

    PyObject * list=PyList_New(states.size());
    for(int i=0;i<states.size();i++){
        PyObject * py_state=states[i].pack();
        PyObject * py_score=PyLong_FromLong(scores[i]);
        PyList_SetItem(list,i,
                    PyTuple_Pack(2,py_state,py_score)
                );
        Py_DECREF(py_state);
        Py_DECREF(py_score);
    };
    return list;
};
static PyObject *
module_new(PyObject *self, PyObject *arg)
{
    PyObject * py_early_stop_callback;
    PyObject * py_shift_callback;
    PyObject * py_reduce_callback;
    PyObject * py_feature_cb;
    int beam_width;
    PyArg_ParseTuple(arg, "iOOOO", &beam_width,
            &py_early_stop_callback,
            &py_shift_callback,
            &py_reduce_callback,
            &py_feature_cb);

    Interface* interface=new Interface(beam_width,
            py_early_stop_callback,
            py_shift_callback,
            py_reduce_callback,
            py_feature_cb);
    return PyLong_FromLong((long)interface);
};

/** stuffs about the module def */
static PyMethodDef interfaceMethods[] = {
    {"new",  module_new, METH_VARARGS,""},
    {"delete",  interface_delete, METH_O,""},
    {"set_raw",  set_raw, METH_VARARGS,""},
    {"set_step",  set_step, METH_VARARGS,""},
    {"search",  search, METH_VARARGS,""},
    {"get_states",  get_states, METH_VARARGS,""},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef module_struct = {
   PyModuleDef_HEAD_INIT,
   STR(__MODULE_NAME),   /* name of module */
   NULL, /* module documentation, may be NULL */
   -1,       /* size of per-interpreter state of the module,
                or -1 if the module keeps state in global variables. */
   interfaceMethods
};

PyMODINIT_FUNC
INIT_FUNC(PYINIT,__MODULE_NAME) (void)
{
    return PyModule_Create(&module_struct);
}

};//end of isan

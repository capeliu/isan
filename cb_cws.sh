#!/bin/sh

./isan.py \
    --model isan.common.perceptrons.Model \
    --decoder isan.common.decoder.DFA \
    --task isan.tagging.cb_cws.Task \
    $*

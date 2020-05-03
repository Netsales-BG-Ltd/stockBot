#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author : Romain Graux
@date : Thursday, 19 March 2020
"""

import os
import logging
import fnmatch
import datetime
from typing import Text
import tensorflow as tf
import numpy as np
from abc import ABC, ABCMeta, abstractmethod
from tensorboard.plugins.hparams import api as hp

from stockBot.reward_strategies import Reward_Strategy
from stockBot import MODELPATH, TENSORBOARDPATH, DEFAULT_TENSORBOARDPATH

# DECORATORS

def flush(function):
    def wrapper(*args, **kwargs):
        self = args[0]
        ret = function(*args, **kwargs)
        self.writer.flush()
        return ret
    return wrapper

def neural_network_graph(function):
    def wrapper(*args, **kwargs):
        self = args[0]
        with self.neural_network.writer.as_default():
            return function(*args, **kwargs)
    return wrapper

# CLASSES

class Neural_Network(ABC):
    """
        The skeleton of all neural networks with basics functions.
    """

    def __init__(self, input_shape=None, load_name=False, save_model_path:Text=None, save_tensorboard_path:Text=None, Name=None):
        self._save_model_path = save_model_path or MODELPATH
        self._save_tensorboard_path = save_tensorboard_path or TENSORBOARDPATH
        self.input_shape = input_shape
        self.model = None
        self.initial_episode = 0
        if load_name:
            self.load_model(load_name)
        else:
            self.build_model()
        self.model_name = Name or self._get_simple_name_model()
        self.tensorboard_log =  self._save_tensorboard_path%self.model_name + "/{}".format(datetime.datetime.now().strftime("%Y.%m.%d-%H:%M:%S"))
        self._launch_tensorboard()

    def fit(self, *args, **kwargs):
        """
            Same as tf.keras.models.Sequential.fit but force callbacks to the tensorboard.
        """
        if not self.model:
            raise NotImplementedError("Model not implemented")
        return self.model.fit(*args, **kwargs, verbose=1)

    def predict(self, *args, **kwargs):
        """
            Same as tf.keras.models.Sequential.predict but force callbacks to the tensorboard.
        """
        if not self.model:
            raise NotImplementedError("Model not implemented")
        return self.model.predict(*args, **kwargs)

    def save_model(self, episode=None):
        """
            Save the model to .h5 format in ./res/models/
        """
        if not self.model_name:
            raise NotImplementedError('Model not implemented')
        extension = ".h5" if not episode else "_%d.h5"%episode
        self.model.save(self._save_model_path%(self.model_name+extension))
        return None

    def load_model(self, name=None):
        """
            Load the model from .h5 format in ./res/models/
        """
        split_under = name.split('_')
        extension = split_under[-1]
        number = extension.split('.')[0]
        try:
            number = int(number)
            self.initial_episode = number
        except:
            pass
        self.model = tf.keras.models.load_model(self._save_model_path%name)
        return None

    @abstractmethod
    def build_model(self):
        raise NotImplementedError('build_model not implemented')

    def _get_name_model(self):
        """
            Compute the template name of the model
        """
        if not self.model:
            raise NotImplementedError('Model not implemented')
        string = "%s-"%(self.__class__.__name__.upper())
        for layer in self.model.layers:
            string += '(%s)'%','.join(map(str, layer.input_shape))
            string += '%s->'%(layer.name.upper())
        string += '(%s)'%','.join(map(str,self.model.layers[-1].output_shape))
        return string

    def _get_simple_name_model(self):
        """
            Compute the template name of the model
        """
        if not self.model:
            raise NotImplementedError('Model not implemented')
        string = "%s"%(self.__class__.__name__)
        for layer in self.model.layers:
            # self.model_name += '(%s)'%','.join(map(str, layer.input_shape))
            string += '->%s'%(layer.name)
        return string
        # self.model_name += '(%s)'%','.join(map(str,self.model.layers[-1].output_shape))

    def _launch_tensorboard(self):
        """
            Declare the TensorBoard
        """
        if not self.model_name:
            raise NotImplementedError('Model not implemented')
        # os.system("rm -r \"%s\""%(TENSORBOARDPATH%self.model_name))
        self.writer = tf.summary.create_file_writer(self.tensorboard_log+'/train')
        self.tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir = self.tensorboard_log, histogram_freq=1, profile_batch=0)
        input_shape = [*self.model.input_shape]
        input_shape[0] = 1
        self.model.predict(np.zeros(input_shape), callbacks=[self.tensorboard_callback]) # Used to display the graph in tensorboard

    @flush
    def summary_scalar(self, name, tensor, step, tag=None):
        def fun(name, tensor, step, tag=None):
            with self.writer.as_default():
                tf.summary.scalar(name, tensor, step=step, description=None)
        if not isinstance(tensor, tf.Tensor):
            tensor = tf.convert_to_tensor(tensor)
        fun(name, tensor, step, tag=None)

    @flush
    def summary_histogram(self, name, tensor, step, tag=None):
        def fun(name, tensor, step, tag=None):
            with self.writer.as_default():
                tf.summary.histogram(name, tensor, step=step, description=None)
        if not isinstance(tensor, tf.Tensor):
            tensor = tf.convert_to_tensor(tensor)
        fun(name, tensor, step, tag=None)

    @flush
    def summary_hparams(self, hparams):
        with self.writer.as_default():
            hp.hparams(hparams)
    @flush
    def summary_weights_biases_histogram(self, step):
        with self.writer.as_default():
            for i, layer in enumerate(self.model.layers):
                for j, weight in enumerate(layer.weights):
                    tf.summary.histogram(weight.name, weight.value(), step=step)
    # @_flush
    # def summary_scalar(self, name, tensor, step, tag=None):
    #     @tf.function
    #     def fun(name, tensor, step, tag=None):
    #         with self.writer.as_default():
    #             tf.summary.scalar(name, tensor, step=step, description=None)
    #     if not isinstance(tensor, tf.Tensor):
    #         tensor = tf.convert_to_tensor(tensor)
    #     fun(name, tensor, step, tag=None)

    # @_flush
    # def summary_histogram(self, name, tensor, step, tag=None):
    #     @tf.function
    #     def fun(name, tensor, step, tag=None):
    #         with self.writer.as_default():
    #             tf.summary.histogram(name, tensor, step=step, description=None)
    #     if not isinstance(tensor, tf.Tensor):
    #         tensor = tf.convert_to_tensor(tensor)
    #     fun(name, tensor, step, tag=None)


    def __str__(self):
        """
            The string representation of the model
        """
        if not self.model:
            raise NotImplementedError("Model not implemented")
        stringlist = []
        self.model.summary(print_fn=lambda x: stringlist.append(x))
        return "\n".join(stringlist)


class Reinforcement_Network(Neural_Network):

    def __init__(self, *args, layer_size=None, **kwargs):
        self.layer_size = layer_size
        super().__init__(*args, **kwargs)

    @abstractmethod
    def act(self, state, epsilon, **kwargs):
        raise NotImplementedError('act not implemented')

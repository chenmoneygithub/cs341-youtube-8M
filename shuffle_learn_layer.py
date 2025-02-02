#---------------------------------------------------------------------------------------------------------
#                   This file implements the shuffle and learn layer
#                   input: video with frame representations
#                   output: the mapped representation
#---------------------------------------------------------------------------------------------------------


import tensorflow as tf
import numpy as np
from utils import random_pick_3

class Config:
    """Holds model hyperparams and data information.

    The config class is used to store various hyperparameters and dataset
    information parameters. Model objects are passed a Config() object at
    instantiation.
    """

    hidden_size1 = 864
    hidden_size2 = 720
    batch_size = 64
    max_grad_norm = 10.0 # max gradients norm for clipping
    lr = 0.001 # learning rate

    # parameters for the first layer
    filter1_size = 5
    conv1_output_channel = 16
    pool1_length = 5

    # parameters for the second layer
    filter2_size = 3
    conv2_output_channel = 6
    pool2_length = 3

    feature_size = 1024
    input_length = 300

    input_num_once = 3

    num_shuffle_sample = 1

    def __init__(self):
        self.batch_size = 64

class shuffleLearnModel():
    def add_placeholders(self, input_features):
        self.input_placeholder  = input_features * 1
        #self.dropout_placeholder = tf.placeholder(tf.float32)
        #self.num_frames = tf.placeholder(tf.int32, [None])

    #def create_feed_dict(self, inputs_batch):
    #    feed_dict = {}
    #    feed_dict[self.input_placeholder] = inputs_batch
    #    #feed_dict[self.num_frames] = num_frames
    #    return feed_dict

    def add_extract_op(self):

        output_list_for_shuffle = []
	output_list_for_lstm = []

        for i in range(Config.input_length):
            with tf.variable_scope("conv1", reuse = None if i == 0 else True):
                # the first convolutional layer
                filter1 = tf.get_variable("f1", [Config.filter1_size, 1, Config.conv1_output_channel])
                conv1_input = tf.reshape(self.input_placeholder[:,i,:], [-1, Config.feature_size, 1 ])
		#conv1_input = self.input_placeholder[:,i,:]
                conv1 = tf.nn.conv1d(conv1_input, filter1, stride = 2, padding= "SAME")

                # pooling
                pool1 = tf.nn.pool(conv1, [Config.pool1_length], "MAX", "SAME")

                # activate
                activ1 = tf.nn.relu(conv1)

            with tf.variable_scope("conv2", reuse = None if i == 0 else True):
                # the first convolutional layer
                filter2 = tf.get_variable("f2", [Config.filter2_size, Config.conv1_output_channel, Config.conv2_output_channel])
                conv2 = tf.nn.conv1d(activ1, filter2, stride = 2, padding= "SAME")

                # pooling
                pool2 = tf.nn.pool(conv2, [Config.pool2_length], "MAX", "SAME")

                # activate
                activ2 = tf.nn.relu(conv2)

            with tf.variable_scope("fc1", reuse = None if i == 0 else True):
		activ2 = tf.transpose(activ2, [0, 2, 1])
                activ2_shape = activ2.get_shape().as_list()
                fc1_input = tf.reshape(activ2, [ -1, Config.conv2_output_channel * activ2_shape[2] ])
		#fc1_input1 = self.input_placeholder[:,i,:]
		fc1_W = tf.get_variable("fc1_W", 
					[Config.conv2_output_channel * activ2_shape[2], 1024],
					initializer = tf.contrib.layers.xavier_initializer())
		fc1_b = tf.get_variable("fc1_b", [1024], initializer = tf.contrib.layers.xavier_initializer())
		fc1_output1 = tf.nn.relu(tf.matmul(fc1_input, fc1_W) + fc1_b) 
                #fc1_output1 = tf.layers.dense(inputs=fc1_input1, units=1024,kernel_initializer=tf.contrib.layers.xavier_initializer(), activation=tf.nn.sigmoid)
	    with tf.variable_scope("fc2", reuse = None if i == 0 else True):
                fc2_W = tf.get_variable("fc2_W",
                                        [1024, 16],
                                        initializer = tf.contrib.layers.xavier_initializer())
                fc2_b = tf.get_variable("fc2_b", [16], initializer = tf.contrib.layers.xavier_initializer())
		fc2_output1 = tf.nn.relu(tf.matmul(fc1_output1, fc2_W) + fc2_b)
		#fc2_output1 = tf.layers.dense(inputs=fc1_output1, units=16,kernel_initializer=tf.contrib.layers.xavier_initializer(), activation=tf.nn.sigmoid)
            output_list_for_shuffle.append(fc2_output1)
	    output_list_for_lstm.append(fc1_output1)

        # return the output of the fully connected layer
        output_tensor_for_shuffle = tf.stack(output_list_for_shuffle, axis = 1)
        #output_tensor_for_shuffle = tf.reshape(output_tensor_for_shuffle, [-1, Config.input_length, 16])
        output_tensor_for_lstm = tf.stack(output_list_for_lstm, axis = 1)
       # output_tensor_for_lstm = tf.reshape(output_tensor_for_lstm, [-1, Config.input_length, Config.feature_size])
	return output_tensor_for_shuffle, output_tensor_for_lstm


    def add_random_combination(self, input_features, num_frames):
        """
        input features: a list (length: input_length) of element with shape [batch_size, feature_size]
        Returns:

        """
        shuffle_list, label_list = random_pick_3(num_frames, Config.num_shuffle_sample, 1) # 3-D np array [batch_size, num_samples, 3]
       # input_embedding_list = tf.unstack(input_features, axis = 0)
        input_embedding_list = input_features
        sample_list = []
        #label_list = tf.convert_to_tensor(label_list)
        video_num = 1
        label_list = tf.constant(label_list, dtype = tf.float32, shape = [video_num ,Config.num_shuffle_sample * 2])
        for i in range(video_num):
            # loop over the batch_size
            #shuffle_index = tf.convert_to_tensor(shuffle_list[i])
	    shuffle_index = tf.constant(shuffle_list[i], dtype = tf.int32, name = 'shuf_index')
            shuffle_value = tf.nn.embedding_lookup(input_embedding_list[i], shuffle_index)
            shuffle_concat_list = []
            for j in range(shuffle_value.shape[0]):
                shuffle_concat_list.append(tf.concat([shuffle_value[j][0], shuffle_value[j][1], shuffle_value[j][2]],
                                                     axis = 0))
	    shuffle_concat = tf.stack(shuffle_concat_list, axis = 0)
            sample_list.append(shuffle_concat)
	sample_list = tf.stack(sample_list, axis = 0)
        return sample_list, label_list

    #def add_random_pick(self, input_features):

	
    def add_shuffle_loss(self, sample_list, label_list):
        #!!!!!!!!! Need Discussion!!!!!!!!
        '''

        This function computes the shuffle loss
        Now, we use a simple softmax classifier to do this job
        It needs further discussion

        '''
	shuffle_loss_list = []
	for i in range(sample_list.shape[1]):
	    with tf.variable_scope("fc3", reuse = None  if i == 0 else True):
                fc3_W = tf.get_variable("fc3_W",
                                        [48, 16],
                                        initializer = tf.contrib.layers.xavier_initializer())
                fc3_b = tf.get_variable("fc3_b", [16], initializer = tf.contrib.layers.xavier_initializer())
                fc3_output1 = tf.nn.relu(tf.matmul(sample_list[:,i,:], fc3_W) + fc3_b)
	    with tf.variable_scope("shuffle_loss", reuse = None  if i == 0 else True):
                shuffle_loss_W = tf.get_variable("shuffle_loss_W",
                                        [16, 1],
                                        initializer = tf.contrib.layers.xavier_initializer())
                shuffle_loss_b = tf.get_variable("shuffle_loss_b", [1], initializer = tf.contrib.layers.xavier_initializer())
                shuffle_loss_output = tf.nn.sigmoid(tf.matmul(fc3_output1, shuffle_loss_W) + shuffle_loss_b)
	    label_current = tf.reshape(label_list[:,i], [-1, 1])
	    shuffle_loss_temp = tf.nn.sigmoid_cross_entropy_with_logits(logits=shuffle_loss_output, labels=label_current)
	    shuffle_loss_temp = tf.reduce_mean(shuffle_loss_temp)
	    shuffle_loss_list.append(shuffle_loss_temp)
	self.shuffle_loss = tf.reduce_mean(tf.stack(shuffle_loss_list, axis = 0))
	return shuffle_loss_output, self.shuffle_loss


    def __init__(self, num_frames, input_features):
        self.config = Config()
        self.input_placeholder = None
       # self.dropout_placeholder = None
        self.add_placeholders(input_features)
        self.output_feat_for_shuffle, self.output_feat_for_lstm = self.add_extract_op()
        sample_list, label_list = self.add_random_combination(self.output_feat_for_shuffle, num_frames)
        self.shuffle_pred, self.loss = self.add_shuffle_loss(sample_list, label_list)
        # self.loss = self.add_shuffle_loss(NONE,sample_list, label_list,-1,NONE)










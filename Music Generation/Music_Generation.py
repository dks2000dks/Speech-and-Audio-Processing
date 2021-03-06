# Generation of Music Automatically using LSTMs.
# Implementation of WaveNet

# Importing Libraries
import numpy as np
from music21 import *
import os
#%tensorflow_version 2.x
import scipy
import keras
import random
import tensorflow as tf
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Flatten
from keras.utils.vis_utils import plot_model
from tensorflow.keras.models import Model
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Activation
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dense,Conv1D,LSTM
from tensorflow.keras.layers import concatenate,Activation

print ("----------------------------Imported Libraries-------------------------")


# The following lines should be added and batch_size during traing must be reduced if the following error occurs
"""
Failed to get convolution algorithm. This is probably because cuDNN failed to initialize, so try looking to see if a warning log message was printed above.
"""
physical_devices = tf.config.experimental.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(physical_devices[0], True)


def Read_MIDI(file):
	""" Process of Reading a Music MIDI File """
	# Returns Notes and Chords of a Music
	notes=[]
	data_to_parse = None

	# Parsing or Resoving a MIDI file
	midi = converter.parse(file)
	
	# Classifying Music based on Instruments
	Data = instrument.partitionByInstrument(midi)

	# Iterating over all Instrumnets of MIDI File
	for ins in Data:
		# Select Instrument as Piano
		if 'Piano' in str(ins):
			data_to_parse = ins.recurse()
			
			# Classifying whether a particular element is Note or a Chord
			for element in data_to_parse:
				if isinstance(element, note.Note):
					notes.append(str(element.pitch))
				elif isinstance(element, chord.Chord):
					notes.append('.'.join(str(n) for n in element.normalOrder))
	
	return notes

# Navigating to Dataset Directory
DatasetDirectory = os.getcwd() + '/classical-music-midi/mendelssohn'# Returns Current Directory and adds additional path to it
os.chdir(DatasetDirectory)												# Changes Directory

Notes_Data = []
MIDI_Data = [i for i in os.listdir() if i.endswith(".mid")]

for i in MIDI_Data:
	Notes_Data.append(Read_MIDI(i))

# Data contains all Notes and Chords of all Music Notes
Data = [element for notes in Notes_Data for element in notes]


""" Preparing Data """
# Defining no.of Time Steps
no_of_timesteps = 128

# Unique Notes in Data
Notes_Vocab = len(set(Data))
print ("No.of Elements in Notes Vocabulary = ",Notes_Vocab)

pitch = sorted(set(item for item in Data))

# Indexing Notes
Notes_Index = dict((note, number) for number, note in enumerate(pitch))


# Creating Input and Output Sequences
X = []
y = []

for notes in Notes_Data:
	for i in range(0,len(notes)-no_of_timesteps,1):
		input_notes = notes[i:i + no_of_timesteps]
		output_notes = notes[i + no_of_timesteps]
		X.append([Notes_Index[note] for note in input_notes])
		y.append(Notes_Index[output_notes])
		
X = np.reshape(X, (len(X), no_of_timesteps, 1))
# Normalising Inputs
X = X/Notes_Vocab


# Creating WaveNet Model
def Simple_WaveNet_Model():
	no_of_kernels = 64
	num_of_blocks= int(np.sqrt(no_of_timesteps)) - 1   					#Stacked Conv1D Layers
	
	# Creating a Model
	model = Sequential()
	for i in range(num_of_blocks):
		model.add(Conv1D(no_of_kernels,3,dilation_rate=(2**i),padding='causal',activation='relu'))
	model.add(Conv1D(1, 1, activation='relu', padding='causal'))
	model.add(Flatten())
	model.add(Dense(128, activation='relu'))
	model.add(Dense(Notes_Vocab, activation='softmax'))
	
	return model
	
WaveNet = Simple_WaveNet_Model()
WaveNet.compile(loss='sparse_categorical_crossentropy', optimizer='adam')

tf.keras.backend.clear_session()

# Creating LSTM Model
def Simple_LSTM_Model():
	model = Sequential()
	model.add(LSTM(128,return_sequences=True))
	model.add(LSTM(128,return_sequences=True))
	model.add(LSTM(256))
	model.add(Activation('relu'))
	model.add(Dense(Notes_Vocab))
	model.add(Activation('softmax'))
	
	return model

LSTM_Model = Simple_LSTM_Model()
LSTM_Model.compile(loss='sparse_categorical_crossentropy', optimizer='adam')


WaveNet.fit(X,np.array(y), epochs=50, batch_size=128)
plot_model(WaveNet, to_file='WaveNet.png', show_shapes=True)

LSTM_Model.fit(X,np.array(y), epochs=50, batch_size=128)
plot_model(LSTM_Model, to_file='LSTM_Model.png', show_shapes=True)


def Generate_Music(model,pitch,no_of_timesteps,pattern):
	Prediction = []
	Map = dict((number, note) for number, note in enumerate(pitch))
	# Generating 100 elements
	for i in range(100):
		input_data = np.reshape(pattern,(1,len(pattern),1))
		p = model.predict(input_data, verbose=0)
		index = np.argmax(p)
		pred = Map[index]
		Prediction.append(pred)
		
		# For generating next element first element of pattern is ignored. This is inorder to generate unique data
		pattern = list(pattern)
		pattern.append(random.random())
		pattern = np.array(pattern[1:len(pattern)])
		
	return Prediction
	
	
def Convert_to_MIDI(prediction_output,name):
	offset = 0
	output_notes = []

	# Create Note and Chord objects based on the values generated by the model
	for pattern in prediction_output:
		# pattern is a chord
		if ('.' in pattern) or pattern.isdigit():
			notes_in_chord = pattern.split('.')
			notes = []
			for current_note in notes_in_chord:
				new_note = note.Note(int(current_note))
				new_note.storedInstrument = instrument.Piano()
				notes.append(new_note)
			new_chord = chord.Chord(notes)
			new_chord.offset = offset
			output_notes.append(new_chord)
		# Pattern is a note
		else:
			new_note = note.Note(pattern)
			new_note.offset = offset
			new_note.storedInstrument = instrument.Piano()
			output_notes.append(new_note)

		# Specify duration between 2 notes
		offset += 0.5
		# offset += random.uniform(0.5,0.9)

	midi_stream = stream.Stream(output_notes)
	midi_stream.write('midi', fp=name + '.mid')
	
# Testing
Input_Data = np.random.rand(128)
Music_WaveNet = np.array(Generate_Music(WaveNet,pitch,no_of_timesteps,Input_Data))
Music_LSTM = np.array(Generate_Music(LSTM_Model,pitch,no_of_timesteps,Input_Data))
rate = 22050
Convert_to_MIDI(Music_LSTM,'Music_LSTM')
Convert_to_MIDI(Music_WaveNet,'Music_WaveNet')

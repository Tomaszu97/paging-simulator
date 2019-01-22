import kivy
kivy.require('1.10.1')
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView, FileChooserIconView
from kivy.uix.button import Button
from kivy.config import Config
from kivy.clock import Clock
from kivy.graphics import *
from random import randint
from kivy.graphics import Color, Ellipse
from kivy.core.text import Label as CoreLabel
from queue import Queue
from operator import itemgetter
from random import uniform
from math import ceil, floor
from kivy.config import Config
from time import sleep
from functools import partial
import os
from pygame import mixer
from kivy.core.window import Window

#window size, no antialiasing
Config.set('graphics','multisamples',0)
Config.set('graphics', 'width', '1900')
Config.set('graphics', 'height', '950')
Config.write()


class GreenLabel(Label):
	pass


class BlueLabel(Label):
	pass


class LightBlueLabel(Label):
	pass


class PrecisionSlider(BoxLayout):
	def increase_value(self):
		if (self.ids.slider.value + self.ids.slider.step) <= self.max:
			self.ids.slider.value += self.ids.slider.step

	def decrease_value(self):
		if (self.ids.slider.value - self.ids.slider.step) >= self.min:
			self.ids.slider.value -= self.ids.slider.step


class AnalogValue(BoxLayout):
	def update_from_reg(self):
		self.ids.slider.ids.slider.value = round(self.reg_value * self.step, 1)


class LoadDialog(FloatLayout):
	load = ObjectProperty(None)
	cancel = ObjectProperty(None)


class SaveDialog(FloatLayout):
	save = ObjectProperty(None)
	text_input = ObjectProperty(None)
	cancel = ObjectProperty(None)


class MainLayout(BoxLayout):
	def __init__(self):
		BoxLayout.__init__(self)
		self.pagelist = []
		self.algorithm_used = 'None'
		mixer.init()
		x = randint(0,2)
		if  x == 0:
			mixer.music.load('res/unreal superhero.mp3')
		elif x == 1:
			mixer.music.load('res/most awesome song.mp3')
		else:
			mixer.music.load('res/digital insanity.mp3')
		mixer.music.play()


	def update_gui_from_pagelist(self):
		if len(self.pagelist) == 0:
			return

		request_count = len(self.pagelist)

		#depending on chosen algorithm show or dont show buffer usage section
		#TODO - edit
		if True:
		#if self.ids['algorithm_picker'].text == 'LFU':
			pagelist_width = len(self.pagelist[0])
		else:
			pagelist_width = int(((len(self.pagelist[0])-1)/2)+1)

		self.ids['paging_table'].clear_widgets()
		self.ids['paging_table'].width = request_count*100

		#put data in scrollable table LIGHT BLUE - REQUESTED, BLUE - SWAP and READ, GREEN - READ
		for i in range(request_count):
			templayout = BoxLayout(orientation = 'vertical', size_hint_x = None)
			for j in range(pagelist_width):
				#empty label if None
				if self.pagelist[i][j] == None:
					templayout.add_widget(Label(text = '', font_size='20sp'))
					continue

				#request row color
				if j == self.request_index:
					templayout.add_widget(LightBlueLabel(markup = True, text = '[color=000000]'+str(self.pagelist[i][j])+'[/color]', font_size='20sp'))
					continue
				
				#buffer section
				if j in range(self.slot_index_range[0], self.slot_index_range[1]):
					#blue if swapped/loaded
					if self.pagelist[i][j] != self.pagelist[i-1][j] or i == 0:
						templayout.add_widget(BlueLabel(markup = True, text = '[color=00FF00]'+str(self.pagelist[i][j])+'[/color]', font_size='20sp'))
						continue
					#green if only used
					if self.pagelist[i][j] == self.pagelist[i][self.request_index]:
						templayout.add_widget(GreenLabel(markup = True, text = '[color=0000FF]'+str(self.pagelist[i][j])+'[/color]', font_size='20sp'))
						continue

				#every other label is normal
				templayout.add_widget(Label(text = str(self.pagelist[i][j]), font_size='20sp'))

			self.ids['paging_table'].add_widget(templayout)

		
		self.ids['requested_page_label'].size_hint_y = 1.0
		self.ids['buffer_label'].size_hint_y = (len(self.pagelist[0])-1)/2
		self.ids['buffer_usage_label'].size_hint_y = (len(self.pagelist[0])-1)/2

		if self.ids['algorithm_picker'].text == 'FIFO':
			self.ids['buffer_usage_label'].text = 'Buffer Slot Age (Arrived)'

		if self.ids['algorithm_picker'].text == 'LRU':
			self.ids['buffer_usage_label'].text = 'Buffer Slot Age (Last Used)'

		if self.ids['algorithm_picker'].text == 'OPT':
			self.ids['buffer_usage_label'].text = 'Buffer Slot Future Usage Distance'

		if self.ids['algorithm_picker'].text == 'LFU':
			self.ids['buffer_usage_label'].text = 'Buffer Slot Usage Count'
		
			# self.ids['requested_page_label'].size_hint_y = 1.0
			# self.ids['buffer_label'].size_hint_y = (len(self.pagelist[0])-1)
			# self.ids['buffer_usage_label'].size_hint_y = None
			# self.ids['buffer_usage_label'].height = 0
			# self.ids['buffer_usage_label'].text = ''


	def generate_data(self):
		request_count = int(self.ids['request_count_slider'].value)
		buffer_size = int(self.ids['buffer_size_slider'].value)
		page_count = int(self.ids['page_count_slider'].value)
		self.pagelist.clear()
		self.algorithm_used = 'None'
		
		#generate table, double buffer section (useful for LFU)
		for i in range(request_count):
			temp = [randint(0, page_count-1)]
			for n in range(buffer_size*2):
				temp.append(None)
			self.pagelist.append(temp[:])

		#calculate useful stuff
		self.request_index = 0
		self.slot_index_range = (1, int( (len(self.pagelist[0])-1)/2 )+1)
		self.age_index_range = (self.slot_index_range[1], int(len(self.pagelist[0])))
		self.buffer_size = int( (len(self.pagelist[0])-1)/2 )

		self.update_gui_from_pagelist()


	def fifo(self):
		self.algorithm_used = 'FIFO'
		self.loadswap_count = 0
		#for every request record
		for i in range(len(self.pagelist)):
			step_done = False

			if i > 0:
				#copy slots and ages from previous step
				for n in range(self.slot_index_range[0], self.age_index_range[1]):
					self.pagelist[i][n] = self.pagelist[i-1][n]

				#increment slot ages depending on old values
				for n in range(self.age_index_range[0], self.age_index_range[1]):
					if self.pagelist[i][n] != None:
						self.pagelist[i][n] += 1
			
			#look for requested value in a buffer - return if its there
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == self.pagelist[i][self.request_index]:
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for empty slots and put requested page there + zero its age
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == None:
					self.loadswap_count += 1
					self.pagelist[i][x] = self.pagelist[i][self.request_index]
					self.pagelist[i][x+self.buffer_size] = 0
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for oldest slot and replace it with needed page
			self.loadswap_count += 1
			temp = self.pagelist[i][self.age_index_range[0] : self.age_index_range[1]]
			oldestval = max(temp)
			oldestindex = temp.index(oldestval) + 1
			self.pagelist[i][oldestindex] = self.pagelist[i][self.request_index]
			self.pagelist[i][oldestindex+self.buffer_size] = 0


	def lru(self):
		self.algorithm_used = 'LRU'
		self.loadswap_count = 0
		#for every request record
		for i in range(len(self.pagelist)):
			step_done = False

			if i > 0:
				#copy slots and ages from previous step
				for n in range(self.slot_index_range[0], self.age_index_range[1]):
					self.pagelist[i][n] = self.pagelist[i-1][n]

				#increment slot ages depending on old values
				for n in range(self.age_index_range[0], self.age_index_range[1]):
					if self.pagelist[i][n] != None:
						self.pagelist[i][n] += 1
			
			#look for requested value in a buffer - return if its there AND zero its age
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == self.pagelist[i][self.request_index]:
					self.pagelist[i][x+self.buffer_size] = 0
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for empty slots and put requested page there + zero its age
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == None:
					self.loadswap_count += 1
					self.pagelist[i][x] = self.pagelist[i][self.request_index]
					self.pagelist[i][x+self.buffer_size] = 0
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for oldest slot and replace it with needed page
			self.loadswap_count += 1
			temp = self.pagelist[i][self.age_index_range[0] : self.age_index_range[1]]
			oldestval = max(temp)
			oldestindex = temp.index(oldestval) + 1
			self.pagelist[i][oldestindex] = self.pagelist[i][self.request_index]
			self.pagelist[i][oldestindex+self.buffer_size] = 0
			
	
	def opt(self):
		self.algorithm_used = 'OPT'
		self.loadswap_count = 0
		#for every request record
		for i in range(len(self.pagelist)):
			step_done = False
			if i > 0:
				#copy slots and ages from previous step
				for n in range(self.slot_index_range[0], self.age_index_range[1]):
					self.pagelist[i][n] = self.pagelist[i-1][n]

				#decrement slot distances depending on old values
				for n in range(self.age_index_range[0], self.age_index_range[1]):
					if self.pagelist[i][n] != None:
						self.pagelist[i][n] -= 1
			
			#look for requested value in a buffer - return if its there
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == self.pagelist[i][self.request_index]:
					#calculate distance
					distance = None
					if i < len(self.pagelist) - 1 :
						for j in range(i+1, len(self.pagelist)):
							if self.pagelist[i][x] == self.pagelist[j][self.request_index]:
								distance = j-i
								break
					self.pagelist[i][x+self.buffer_size] = distance
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for empty slot and put requested page there + calculate its distance
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == None:
					self.loadswap_count += 1
					#swap requested page with this slot
					self.pagelist[i][x] = self.pagelist[i][self.request_index]
					#calculate distance
					distance = None
					if i < len(self.pagelist) - 1 :
						for j in range(i+1, len(self.pagelist)):
							if self.pagelist[i][x] == self.pagelist[j][self.request_index]:
								distance = j-i
								break
					self.pagelist[i][x+self.buffer_size] = distance
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for never used again slot and put requested page there + calculate its distance
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x+self.buffer_size] == None:
					self.loadswap_count += 1
					#swap requested page with this slot
					self.pagelist[i][x] = self.pagelist[i][self.request_index]
					#calculate distance
					distance = None
					if i < len(self.pagelist) - 1 :
						for j in range(i+1, len(self.pagelist)):
							if self.pagelist[i][x] == self.pagelist[j][self.request_index]:
								distance = j-i
								break
					self.pagelist[i][x+self.buffer_size] = distance
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for slot with furthest distance and replace it with needed page
			self.loadswap_count += 1
			temp = self.pagelist[i][self.age_index_range[0] : self.age_index_range[1]]
			oldestval = max(temp)
			oldestindex = temp.index(oldestval) + 1
			self.pagelist[i][oldestindex] = self.pagelist[i][self.request_index]
			#calculate distance
			distance = None
			for j in range(i+1, len(self.pagelist)):
				if self.pagelist[i][oldestindex] == self.pagelist[j][self.request_index]:
						distance = j-i
						break
			self.pagelist[i][oldestindex+self.buffer_size] = distance

#TODO - secondary choose by age
	def lfu(self):
		self.algorithm_used = 'LFU'
		self.loadswap_count = 0
		#for every request record
		for i in range(len(self.pagelist)):
			step_done = False

			if i > 0:
				#copy slots and ages from previous step
				for n in range(self.slot_index_range[0], self.age_index_range[1]):
					self.pagelist[i][n] = self.pagelist[i-1][n]
			
			#look for requested value in a buffer - return if its there AND add +1 to 'age' (here it means usage frequency)
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == self.pagelist[i][self.request_index]:
					self.pagelist[i][x+self.buffer_size] += 1
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for empty slots and put requested page there + age=1
			for x in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][x] == None:
					self.loadswap_count += 1
					self.pagelist[i][x] = self.pagelist[i][self.request_index]
					self.pagelist[i][x+self.buffer_size] = 1
					step_done = True
					break
			if step_done:
				continue

			#otherwise look for least used and then oldest slot and replace it with needed page
			self.loadswap_count += 1
			temp = self.pagelist[i][self.age_index_range[0] : self.age_index_range[1]]
			leastusages = min(temp)
			tempagebuffer = []
			for q in range(self.slot_index_range[0], self.slot_index_range[1]):
				if self.pagelist[i][q+self.buffer_size] == leastusages:
					
					tempage = 0
					for n in reversed(range(0,i-1)):
						if self.pagelist[i][q] != self.pagelist[n][q]:
							break
						else:
							tempage += 1

					tempagebuffer.append(tempage)
				else:
					tempagebuffer.append(-1)
			swapindex = tempagebuffer.index(max(tempagebuffer)) + 1


			self.pagelist[i][swapindex] = self.pagelist[i][self.request_index]
			self.pagelist[i][swapindex+self.buffer_size] = 1


	def calculate(self):
		if len(self.pagelist) == 0:
			return

		#clear previously calculated data
		for i in range(0, len(self.pagelist)):
			for j in range(self.request_index+1, self.age_index_range[1]):
				self.pagelist[i][j] =  None

		if self.ids['algorithm_picker'].text == 'FIFO':
			self.fifo()

		if self.ids['algorithm_picker'].text == 'LRU':
			self.lru()

		if self.ids['algorithm_picker'].text == 'OPT':
			self.opt()

		if self.ids['algorithm_picker'].text == 'LFU':
			self.lfu()

		self.update_gui_from_pagelist()


	def dismiss_popup(self):
		self._popup.dismiss()

		
	def show_load(self):
		content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
		content.ids['filechooser'].path = str(os.getcwd()) + '\\savefiles'
		self._popup = Popup(title="Load file", content=content, size_hint=(0.5, 0.5))
		self._popup.open()


	def show_save(self):
		content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
		content.ids['filechooser'].path = str(os.getcwd()) + '\\savefiles'
		self._popup = Popup(title="Save file", content=content, size_hint=(0.5, 0.5))
		self._popup.open()


	def load(self, path, filename):
		self.pagelist.clear()
		self.algorithm_used = 'None'
		with open(os.path.join(path, filename[0])) as stream:
			
			buffer_size = None
			for line in stream:
				#skip commented lines
				if line[0] == '#':
					continue
				#set buffer size according to first non-commented line
				if buffer_size == None:
					buffer_size = int(line)
					continue
				#add Requested Page number
				record = [int(line.split(',')[0])]
				for i in range(buffer_size*2):
					record.append(None)
				self.pagelist.append(record)
			self.request_index = 0
			self.slot_index_range = (1, int( (len(self.pagelist[0])-1)/2 )+1)
			self.age_index_range = (self.slot_index_range[1], int(len(self.pagelist[0])))
			self.buffer_size = int( (len(self.pagelist[0])-1)/2 )

			self.update_gui_from_pagelist()
		
		self.dismiss_popup()


	def save(self, path, filename):
		if len(self.pagelist) == 0:
			return

		with open(os.path.join(path, filename), 'w') as stream:
			stream.write('#Buffer Length\n')
			stream.write(str( int( (len(self.pagelist[0])-1)/2 ) ) + '\n')
			stream.write('#Requested Page [,Slot1,Slot2,...,SlotUsage1,SlotUsage2,...]\n')

			#if no algorithm used then just save requested pages
			for record in self.pagelist:
				for n in range(len(self.pagelist[0])):
					stream.write(str(record[n]))
					if self.algorithm_used == 'None':
						break
					if n < len(self.pagelist[0])-1:
						stream.write(',')
				stream.write('\n')

			if self.algorithm_used != 'None':
				stream.write('#Used Algorithm: ' + str(self.algorithm_used) + '\n')
				stream.write('#Swap/Request Ratio: ' + str(self.loadswap_count) + '/' + str(len(self.pagelist)) + ' [' +  str(self.loadswap_count/len(self.pagelist)) + ']' + '\n')

		self.dismiss_popup()



Builder.load_file('kv/layout.kv')



class MyApp(App):
	def build(self):
		self.icon = 'res/icon.ico'
		m = MainLayout()
		return m



if __name__ == '__main__':
	MyApp().run()
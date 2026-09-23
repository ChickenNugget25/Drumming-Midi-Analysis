import pygame
import pygame.midi
import pygame.gfxdraw
import pygame.transform
import time
import numpy as np
import pydub
import pydub.generators
import pydub.playback
import sounddevice as sd
from threading import Thread
from enum import Enum

from math import pi, sin, cos, fmod, dist, floor, sqrt, tanh, log2, log10

# pygame.init()

class Notes(Enum):
	C = 261.63
	Cs= 277.18
	D = 293.66
	Ds= 311.13
	E = 329.63
	F = 349.23
	Fs= 369.99
	G = 392
	Gs= 415.30
	A = 440
	As= 466.16
	B = 493.88

note_array = [Notes.C, Notes.Cs, Notes.D, Notes.Ds, Notes.E, Notes.F, Notes.Fs, Notes.G, Notes.Gs, Notes.A, Notes.As, Notes.B]

def distance(x, y):
	return abs(x - y)

def ratioize(x, y, a):

	if type(x) != type(y):
		return 0

	if type(x) == pygame.Vector2:
		return pygame.Vector2((x.x / y.x) * a.x, (x.y / y.y) * a.y)

	return (x / y) * a

def lerp(x, y, t):
	return x + (abs(y - x) * t)

def gradientize(x, gradient : dict):

	keys = list(gradient.keys())
	for i in range(len(keys)):

		if x > keys[i]:
			continue

		# floating point error catcher thing
		elif distance(x, keys[i]) <= 0.0001:
			return gradient[keys[i]]

		# t = (x - keys[i - 1]) / (keys[i] - keys[i - 1])
		# print(t)
		return lerp(gradient[keys[i - 1]], gradient[keys[i]], 0)

	return gradient[keys[-1]]

# draws from top left
def gfxdraw_box(surface, x, y, sizex, sizey, color):
	# pygame.gfxdraw.line(surface, x - sizex, y - sizey, x - sizex, y + sizey, color)
	# pygame.gfxdraw.line(surface, x - sizex, y + sizey, x + sizex, y + sizey, color)
	# pygame.gfxdraw.line(surface, x + sizex, y + sizey, x + sizex, y - sizey, color)
	# pygame.gfxdraw.line(surface, x + sizex, y - sizey, x - sizex, y - sizey, color)

	x = round(x)
	y = round(y)
	sizex = round(sizex)
	sizey = round(sizey)

	pygame.gfxdraw.line(surface, x, y, x, y + sizey, color)
	pygame.gfxdraw.line(surface, x, y + sizey, x + sizex, y + sizey, color)
	pygame.gfxdraw.line(surface, x + sizex, y + sizey, x + sizex, y, color)
	pygame.gfxdraw.line(surface, x + sizex, y, x, y, color)

def gfxdraw_line(surface, x, y, x1, y1, color):
	pygame.gfxdraw.line(surface, round(x), round(y), round(x1), round(y1), color)

# I don't really need this, but it's cleaner imo.
class Time:

	elapsed_time : float = 0

	def get_time_seconds(self):
		return self.elapsed_time

class Instrument:

	NUMBER_OF_HARMONICS = 16

	# a list of harmonics for specific notes
	harmonic_sets = {
		Notes.C: [1.0]
	}

	class SynthType(Enum):
		Sin = 1

	class NoteInformation:
		start_time : float = 0
		phase : float = 0
		held : bool = True
		released_at : float = 0
		should_be_deleted : bool = False

	synth_type : SynthType = SynthType.Sin
	sustain : bool = False

	# all of these values are in miliseconds
	# attack_pos : pygame.Vector2 = pygame.Vector2(1000, 1.0)
	# decay_pos : pygame.Vector2 = pygame.Vector2(1500, 0.8)
	# release_pos : pygame.Vector2 = pygame.Vector2(5000, 0.0)

	attack_pos : pygame.Vector2 = pygame.Vector2(0, 1.0)
	decay_pos : pygame.Vector2 = pygame.Vector2(500, 0.5)
	release_pos : pygame.Vector2 = pygame.Vector2(2000, 0.0)
	
	# elapsed time this note on this instrument has been played for
	el_time : float = 0

	is_playing_audio : bool = False

	frequencies_to_phases = {}

	def __init__(self, time : Time, ssynth_type : SynthType = SynthType.Sin) -> None:
		self.time = time
		self.synth_type = ssynth_type

		for i in self.harmonic_sets.keys():
			while len(self.harmonic_sets[i]) < self.NUMBER_OF_HARMONICS:
				self.harmonic_sets[i].append(0)

	def start_playing(self, frequency):
		# self.frequencies_to_phases[frequency] = 0
		self.frequencies_to_phases[frequency] = self.NoteInformation()
		# self.frequencies_to_phases[frequency].start_time = self.time.elapsed_time
		self.frequencies_to_phases[frequency].start_time = time.time_ns() * (10 ** -9)
		self.is_playing_audio = True

	def stop_playing(self, frequency):

		if not (frequency in self.frequencies_to_phases):
			return

		# self.frequencies_to_phases.pop(frequency)
		self.frequencies_to_phases[frequency].held = False
		# self.frequencies_to_phases[frequency].released_at = self.time.get_time_seconds()
		self.frequencies_to_phases[frequency].released_at = time.time_ns() * (10 ** -9)

		# if not self.frequencies_to_phases:
		# 	self.is_playing_audio = False

	def evalute_envelope(self, elapsed_time) -> float:

		# Attack
		if elapsed_time < self.attack_pos.x:
			return ratioize(elapsed_time, self.attack_pos.x, self.attack_pos.y)

		# Decay
		elif elapsed_time < self.decay_pos.x:
			return min(ratioize(elapsed_time - self.attack_pos.x, self.decay_pos.x, self.decay_pos.y), self.decay_pos.y)

		# Sustain (if enabled)
		elif self.sustain:
			return self.decay_pos.y

		# Release
		elif elapsed_time < self.release_pos.x:
			return ratioize(elapsed_time - self.decay_pos.x, self.release_pos.x, self.release_pos.y)

		return 0

	def generate_frames(self, outdata, frames) -> int:

		# is this a bad fix?
		frequencies = self.frequencies_to_phases.copy()

		loops = 0
		for frequency in frequencies.keys():

			note_info = frequencies[frequency]

			# amplitude = 1
			elapsed_time = (self.time.get_time_seconds() - note_info.start_time) * 1000
			amplitude : float

			elapsed_time = ((time.time_ns() * (10 ** -9)) - note_info.start_time) * 1000
			if note_info.held:
				amplitude = self.evalute_envelope(elapsed_time)
			else:
				amplitude = self.evalute_envelope(note_info.released_at * 1000)

			# if note_info.held:
				# if elapsed_time < self.attack_pos.x:
				# 	amplitude_modifier = ratioize(elapsed_time, self.attack_pos.x, self.attack_pos.y)
				# elif elapsed_time < self.decay_pos.x or (self.sustain):
				# 	amplitude_modifier = min(ratioize(elapsed_time - self.attack_pos.x, self.decay_pos.x, self.decay_pos.y), self.decay_pos.y)
				# elif elapsed_time < self.release_pos.x:
				# 	amplitude_modifier = ratioize(elapsed_time - self.decay_pos.x, self.release_pos.x, self.release_pos.y)
				# else:
				# 	amplitude_modifier = 0
			# else:
			if not note_info.held:
				# so it was released,

				t = 1.0 - ((elapsed_time - ((note_info.released_at - note_info.start_time) * 1000)) / (self.release_pos.x - self.decay_pos.x))

				amplitude *= t

				if amplitude <= 0.0:
					# frequencies.pop(frequency)
					frequencies[frequency].should_be_deleted = True

			t = (np.arange(frames) + note_info.phase) / DAW.SAMPLE_RATE

			if self.synth_type == Instrument.SynthType.Sin:
				outdata[:] += np.sin(2 * np.pi * frequency * t).reshape(-1, 1) * amplitude

			# if frequency in frequencies:
			frequencies[frequency].phase = fmod(note_info.phase + frames, DAW.SAMPLE_RATE / frequency)

			loops += 1

		for frequency in list(frequencies.keys()):
			if frequency in self.frequencies_to_phases:
				self.frequencies_to_phases[frequency].phase = frequencies[frequency].phase

			if frequencies[frequency].should_be_deleted:
				self.frequencies_to_phases.pop(frequency)

		return loops

class DAW:

	NONE = -1

	FPS = 30
	SAMPLE_RATE = 44100
	BLACK = (0, 0, 0)
	GREY = (100, 100, 100)
	WHITE = (255, 255, 255)

	BLACK_HEX = 0x00_00_00
	WHITE_HEX = 0xFF_FF_FF

	START_WIDTH, START_HEIGHT = (1200, 800)
	width, height = START_WIDTH, START_HEIGHT

	elapsed_time : float = 0
	draw_elapsed_time : float = 0
	draw_frame_index : int = 0

	# phase : float = 0

	# is_playing : bool = False
	is_running : bool = True
	# thread_just_started : Thread
	# current_threads : list[Thread] = []

	KEYS_TO_NOTE_MAP = {
		"q": Notes.C,
		"2": Notes.Cs,
		"w": Notes.D,
		"3": Notes.Ds,
		"e": Notes.E,
		"r": Notes.F,
		"5": Notes.Fs,
		"t": Notes.G,
		"6": Notes.Gs,
		"y": Notes.A,
		"7": Notes.As,
		"u": Notes.B
	}

	NOTE_TO_INTEGER_MAP = {
		Notes.C: 0,
		Notes.Cs: 1,
		Notes.D: 2,
		Notes.Ds: 3,
		Notes.E: 4,
		Notes.F: 5,
		Notes.Fs: 6,
		Notes.G: 7,
		Notes.Gs: 8,
		Notes.A: 9,
		Notes.As: 10,
		Notes.B: 11
	}

	class DrawType(Enum):
		DRAW_MODULATION = 1
		DRAW_FFT = 2

	draw_state : DrawType = DrawType.DRAW_FFT

	spectograph_gradient = {
		0: 0x00_00_00,
		0.25: 0x6c_24_c9,
		0.5: 0xe0_2a_0d,
		0.75: 0xf0_e6_62,
		1.0: 0xff_ff_ff
	}

	# frequency : float = NONE
	octave : int = 4

	time = Time()

	# instrument view:
	note_playing : int = NONE
	using_midi : bool = False
	instruments : list[Instrument] = [Instrument(time)]
	current_instrument_index : int = 0

	def __init__(self, bpm=90, uusing_midi : bool = False):

		pygame.init()
		self.surface = pygame.display.set_mode((self.width, self.height))
		pygame.display.set_caption("Parker's DAW")
		self.small_font = pygame.font.Font(None, 26)

		self.using_midi = uusing_midi

		if uusing_midi:
			pygame.midi.init()

			if pygame.midi.get_default_input_id() == -1:
				print("Couldn't find midi device. Continuing.")
				self.using_midi = False
			else:
				self.midi_device = pygame.midi.Input(pygame.midi.get_default_input_id())

		self.drawn_curve = pydub.generators.Sine(440)
		self.bpm = bpm

		self.output_stream = sd.OutputStream(samplerate=DAW.SAMPLE_RATE, channels=1, callback=self._play_callback, blocksize=1024)

	def _play_callback(self, outdata, frames, atime, status):

		# if self.frequency == DAW.NONE:
		outdata[:] = np.array([0 for i in range(frames)]).reshape(-1, 1)
		if not self.instruments[self.current_instrument_index].is_playing_audio:
			return

		if status:
			print(status)

		n_voices = self.instruments[self.current_instrument_index].generate_frames(outdata, frames)

		outdata = np.array([tanh(sample[0]) for sample in outdata])

		# for i in range(len(outdata)):

		# 	if outdata[i] >= 1.0:
		# 		outdata[i] *= 0.8

	def draw_box(self, bg_scaledown_amount):

		inverse_bg_scale_down_amount = 1.0 / bg_scaledown_amount

		box_margin = inverse_bg_scale_down_amount

		middle = (pygame.Vector2(self.width, self.height) / 2.0)
		bottom_right = pygame.Vector2(self.width, self.height)

		box_size = middle - pygame.Vector2(1, 1) * box_margin * 2 - pygame.Vector2(1, 1) * (inverse_bg_scale_down_amount * 0.5)
		box_pos = bottom_right - (box_size + pygame.Vector2(1, 1) * box_margin)

		# make it 1/8 the size
		# scale_down_amount = 0.125
		scale_down_amount = 0.125
		inverse_scale_down_amount = 1.0 / scale_down_amount
		draw_surface = pygame.Surface(box_size * scale_down_amount + pygame.Vector2(1, 1) * inverse_scale_down_amount)
		pixels = pygame.surfarray.pixels2d(draw_surface)

		effective_box_size = box_size * scale_down_amount
		# amplitude = effective_box_size.y * 0.125
		amplitude = 2

		# time it takes for the sin wave to go all the way through? (s)
		time_per_box = 2

		# time for the thing to slowly 'tween' back to zero so it doesn't hurt your eyes
		grace_period = 0.5
		relative_elapsed_time = fmod(self.time.get_time_seconds(), time_per_box + grace_period)

		# n_samples = sample_rate * duration
		# n_samples / sample_rate = duration
		# audio_segment = self.drawn_curve.to_audio_segment((effective_box_size.x / self.drawn_curve.sample_rate) * 10 ** -3)

		audio_segment = self.drawn_curve.to_audio_segment()

		frames = audio_segment.get_array_of_samples()

		for x, y in np.ndindex(pixels.shape):

			if (x + y) % 2 == 0:
				pixels[x, y] = 0x742c9e
			else:
				pixels[x, y] = 0x69288f

			time_to_use = relative_elapsed_time
			if relative_elapsed_time > time_per_box:
				time_to_use = (1.0 - ((relative_elapsed_time - time_per_box) / grace_period)) * time_per_box
			
			# if (x / effective_box_size.x) > (time_to_use / time_per_box):
			# 	continue


			# index_low = floor((x / effective_box_size.x) * len(audio_segment))
			# index_high = floor(min(((x + 1) / effective_box_size.x), 1.0) * len(audio_segment))

			# sum_samples = 0

			# for i in range(index_low, index_high):
			# 	sum_samples += int.from_bytes(audio_segment.get_frame(i), signed=True)

			# half_box_size_y = effective_box_size.y * 0.5

			# # print(index_high - index_low)

			# sum_samples /= (index_high - index_low)
			# value = round(((sum_samples / 32767) * half_box_size_y) + half_box_size_y)

			# if y == value:
			# 	pixels[x, y] = DAW.BLACK_HEX


			index = round((x / effective_box_size.x) * len(audio_segment))
			# index = x
			# divide by the max 16 signed amount (2^15 - 1 = 32767)

			# value = round(((int.from_bytes(audio_segment.get_frame(index), signed=True) / 32767) * effective_box_size.y * 0.5) + effective_box_size.y * 0.5)
			value = (int.from_bytes(audio_segment.get_frame(index), signed=True) / 32767) * effective_box_size.y * 0.5

			offset_y = y - (effective_box_size.y * 0.5)

			# if ((offset_y < 0) == (value < 0)) and (abs(offset_y) <= abs(value)):
			# 	pixels[x, y] = DAW.BLACK_HEX

			# r = round(amplitude * sin((x)) + (effective_box_size.y * 0.5))

			# if y > r - (amplitude * 0.6) and y < r + (amplitude * 0.6):
			# 	pixels[x, y] = DAW.BLACK_HEX

		del pixels

		# scale it back up
		scaled_surface = pygame.transform.scale(draw_surface, box_size + pygame.Vector2(1, 1) * inverse_scale_down_amount)
		self.surface.blit(scaled_surface, box_pos, pygame.Rect(pygame.Vector2(0, 0), box_size))
		
		gfxdraw_box(self.surface, box_pos.x, box_pos.y, box_size.x, box_size.y, DAW.BLACK)

	def draw_piano(self, bg_scaledown_amount):

		pixel_size = 1.0 / bg_scaledown_amount

		piano_box_pos = pygame.Vector2(0, self.height) + pygame.Vector2(pixel_size, -pixel_size)
		piano_box_size = pygame.Vector2(8, 4) * pixel_size

		N_Notes = 12

		note_padding : float = 2.0
		white_key_size = floor((piano_box_size.x - (note_padding * N_Notes)) / N_Notes)

		n_white_keys = 0

		black_key_indecies = []

		for i in range(N_Notes):

			relative_key = i % 12

			if relative_key > 4:
				if relative_key % 2 == 0:
					black_key_indecies.append(i)
					continue				
			elif relative_key % 2 != 0:
				black_key_indecies.append(i)
				continue

			x_offset = (white_key_size + note_padding) * n_white_keys

			color = DAW.WHITE

			if i == self.note_playing:
				color = DAW.GREY

			pygame.draw.rect(self.surface, color, pygame.Rect(piano_box_pos + pygame.Vector2(x_offset, -piano_box_size.y), pygame.Vector2(white_key_size, piano_box_size.y)), width=10000)
			n_white_keys += 1

		n_black_keys = 0
		# these numbers are kinda random, ngl
		for i in range((N_Notes // 8) + 1):
			for j in range(2 if (i % 2 == 0) else 3):

				x_offset = (n_black_keys + 1) * (white_key_size + note_padding)

				r = pygame.Rect(piano_box_pos - pygame.Vector2(white_key_size * 0.5 - x_offset, piano_box_size.y), pygame.Vector2(white_key_size, piano_box_size.y * 0.75))

				color = DAW.BLACK

				if black_key_indecies[n_black_keys - i] == self.note_playing:
					color = DAW.GREY

				pygame.draw.rect(self.surface, color, r, width=1000)

				n_black_keys += 1

			n_black_keys += 1

	def draw_envelope(self, bg_scaledown_amount):

		pixel_size = 1.0 / bg_scaledown_amount

		envelope_pos = pygame.Vector2(pixel_size, pixel_size)
		envelope_box_size = pygame.Vector2(8, 6) * pixel_size

		scale_down_amount = 1 / 4
		draw_surface = pygame.Surface(envelope_box_size * scale_down_amount)# + pygame.Vector2(pixel_size, pixel_size))
		pixels = pygame.surfarray.pixels2d(draw_surface)

		effective_size = envelope_box_size * scale_down_amount
		instrument = self.instruments[0]

		for x, y in np.ndindex(pixels.shape):

			if (x + y) % 2 == 0:
				pixels[x, y] = 0x742c9e
			else:
				pixels[x, y] = 0x59288f

		del pixels

		Xmax = max(instrument.attack_pos.x, instrument.decay_pos.x, instrument.release_pos.x)
		Ymax = max(instrument.attack_pos.y, instrument.decay_pos.y, instrument.release_pos.y)
		Dmax = pygame.Vector2(Xmax, Ymax) * 2 # + pygame.Vector2(Xmax, Ymax) / 2

		attack_pos_scaled : pygame.Vector2 = ratioize(instrument.attack_pos, Dmax, effective_size)
		decay_pos_scaled : pygame.Vector2 = ratioize(instrument.decay_pos, Dmax, effective_size)
		release_pos_scaled : pygame.Vector2 = ratioize(instrument.release_pos, Dmax, effective_size)

		# for i in [attack_pos_scaled, decay_pos_scaled, release_pos_scaled]:
		# 	pygame.draw.circle(draw_surface, DAW.BLACK, i, 2)

		pygame.draw.line(draw_surface, DAW.BLACK, pygame.Vector2(0, effective_size.y), attack_pos_scaled)
		pygame.draw.line(draw_surface, DAW.BLACK, attack_pos_scaled, decay_pos_scaled)
		pygame.draw.line(draw_surface, DAW.BLACK, decay_pos_scaled, release_pos_scaled)
		pygame.draw.line(draw_surface, DAW.BLACK, release_pos_scaled, effective_size)

		scaled_surface = pygame.transform.scale(draw_surface, envelope_box_size)# + pygame.Vector2(pixel_size, pixel_size))
		self.surface.blit(scaled_surface, envelope_pos, pygame.Rect(pygame.Vector2(0, 0), envelope_box_size))

		gfxdraw_box(self.surface, envelope_pos.x, envelope_pos.y, envelope_box_size.x, envelope_box_size.y, DAW.BLACK)

	def draw_harmonics(self, bg_scaledown_amount):

		pixel_size = 1.0 / bg_scaledown_amount
		harmonics_size = pygame.Vector2(12, 4) * 32
		position = pygame.Vector2(self.width, 0) + pygame.Vector2(-pixel_size - harmonics_size.x, pixel_size)
		scale_down_amount = 1 / 8

		draw_surface = pygame.Surface(harmonics_size * scale_down_amount)
		pixels = pygame.surfarray.array2d(draw_surface)

		for x, y in np.ndindex(pixels.shape):

			if (x + y) % 2 == 0:
				pixels[x, y] = 0x742c9e
			else:
				pixels[x, y] = 0x59288f

			# pixels[x, y] = 0x00ff00

		del pixels

		scaled = pygame.transform.scale(draw_surface, harmonics_size)
		self.surface.blit(scaled, position)

	def draw_modulation_view(self, bg_scaledown_amount):
		self.draw_box(bg_scaledown_amount)
		self.draw_piano(bg_scaledown_amount)
		self.draw_envelope(bg_scaledown_amount)
		self.draw_harmonics(bg_scaledown_amount)

	def draw_fft(self, bg_pixel_size):

		time_chunks = 128
		draw_size = pygame.Vector2(16, 16) * (1.0 / bg_pixel_size)
		# extremely slow
		audio_segment : pydub.AudioSegment = pydub.AudioSegment.from_file("sounds/HelloEveryone.wav")
		audio_nparr = np.array(audio_segment.get_array_of_samples())

		segments_per_chunk = floor(len(audio_nparr) / time_chunks)
		del audio_segment

		# scale_down_amount = pygame.Vector2(time_chunks, ) / draw_size.x
		# print(scale_down_amount * draw_size)

		# draw_surface = pygame.Surface(draw_size * scale_down_amount)
		# time_chunks x frequencies
		draw_surface = pygame.Surface(pygame.Vector2(time_chunks, (segments_per_chunk // 2) + 1))
		draw_pixels = pygame.surfarray.pixels2d(draw_surface)

		cmax = -1000

		for x in range(draw_pixels.shape[0]):

			if len(audio_nparr[segments_per_chunk * x:segments_per_chunk * (x + 1)]) == 0:
				continue

			sfft = np.abs(np.fft.fft(audio_nparr[segments_per_chunk * x:segments_per_chunk * (x + 1)]))
			sfft = np.log10(sfft / 32768)

			# the maximum / minimum value might need to be an external variable.
			dbfs_max = np.max(sfft)
			# sfft_max = np.max(sfft)
			N = len(sfft)
			# frequencies = (np.arange(N)) / (N / sampling_rate)

			for y in range(draw_pixels.shape[1]):

				# yy = (N // 2) - (y + 1)

				# dbfs = log10(sfft[y] / 32768) / (6.541883715362519)
				dbfs = sfft[y] / dbfs_max
				cmax = max(cmax, dbfs)
				# dbfs = log10(sfft[y] / sfft_max)

				# frequencies[y]
				# draw_pixels[x, yy] = round(0xff_ff_ff * max(min(1.0 - (sfft[y] / (N * 4)), 1.0), 0.0))
				# gcolor = round(dbfs * 255)
				# draw_pixels[x, y] = (gcolor) + (gcolor * pow(2, 8)) + (gcolor * pow(2, 16))
				# draw_pixels[x, y] = gcolor + (gcolor << 8) + (gcolor << 16)
				# draw_pixels[x, y] = 0xff0000

				draw_pixels[x, draw_pixels.shape[1] - (y + 1)] = gradientize(dbfs, DAW.spectograph_gradient)

		del draw_pixels

		if cmax != 1.0:
			print("Cmax was: ", cmax)

		scaled_surface = pygame.transform.scale(draw_surface, draw_size)

		# self.surface.blit(scaled_surface, pygame.Vector2(0, 0), pygame.Rect(pygame.Vector2(0, 0), draw_size))
		self.surface.blit(scaled_surface, pygame.Vector2(0, 0))

	def draw(self):

		bg_scaledown_amount = 1.0 / 32.0
		inverse_scale = 1.0 / bg_scaledown_amount

		# bg_surface = pygame.Surface((round(surface_size.x), round(surface_size.y)))
		bg_surface = pygame.Surface(pygame.Vector2(self.width, self.height) * bg_scaledown_amount)

		bg_pixels = pygame.surfarray.pixels2d(bg_surface)

		bg_surface.fill((164, 90, 156))

		for col, row in np.ndindex(bg_pixels.shape):

			if (col + row) % 2 == 0:
				bg_pixels[col, row] = 0x965490

		del bg_pixels

		scaled_surface = pygame.transform.scale(bg_surface, pygame.Vector2(self.width, self.height))

		self.surface.blit(scaled_surface, (0, 0), pygame.Rect(pygame.Vector2(0, 0), pygame.Vector2(self.width, self.height)))

		# if self.draw_state == DAW.DrawType.DRAW_MODULATION:
		# 	self.draw_modulation_view(bg_scaledown_amount)
		match self.draw_state:
			case DAW.DrawType.DRAW_MODULATION:
				self.draw_modulation_view(bg_scaledown_amount)
			case DAW.DrawType.DRAW_FFT:
				self.draw_fft(bg_scaledown_amount)

		pygame.display.flip()

	def process(self, delta_time : float):

		# self.start_async_play(self.drawn_curve.to_audio_segment())
		# print(self.drawn_curve.to_audio_segment().get_frame(0))

		self.draw_elapsed_time += delta_time
		self.time.elapsed_time += delta_time

		if self.draw_elapsed_time >= (1.0 / DAW.FPS):

			self.draw_elapsed_time = fmod(self.draw_elapsed_time, 1.0 / DAW.FPS)
			self.draw()

			self.draw_frame_index += 1

	def _on_key_pressed(self, key : int):

		character = chr(key).lower()

		if not(character in DAW.KEYS_TO_NOTE_MAP):
			return

		note = DAW.KEYS_TO_NOTE_MAP[character]
		self.note_playing = DAW.NOTE_TO_INTEGER_MAP[note]

		frequency = (note.value) * pow(2, self.octave - 4)

		self.instruments[self.current_instrument_index].start_playing(frequency)

	def _on_key_unpressed(self, key):

		character = chr(key).lower()

		if not(character in DAW.KEYS_TO_NOTE_MAP):
			return

		note = DAW.KEYS_TO_NOTE_MAP[character]

		frequency = (note.value) * pow(2, self.octave - 4)

		self.instruments[self.current_instrument_index].stop_playing(frequency)

		self.note_playing = DAW.NONE

	def _on_midi_input(self, raw_midi_data):

		data, timestamp = raw_midi_data
		status, raw_note, velocity, data3 = data

		note = raw_note % 12
		octave = (raw_note // 12) - 4
		frequency = note_array[note].value * pow(2, octave)

		if status == 144:
			self.instruments[self.current_instrument_index].start_playing(frequency)
			self.note_playing = note

		elif status == 128:
			self.instruments[self.current_instrument_index].stop_playing(frequency)

if __name__ == "__main__":

	daw = DAW(uusing_midi=True)
	last_time = time.time_ns()

	running = True

	with daw.output_stream:

		while running:

			delta_time = (time.time_ns() - last_time) * (10**-9)
			last_time = time.time_ns()

			daw.process(delta_time)

			if daw.using_midi:
				for event in daw.midi_device.read(10):
					daw._on_midi_input(event)

			for event in pygame.event.get():

				if event.type == pygame.QUIT:
					running = False
					daw.is_running = False

				if event.type == pygame.KEYDOWN:

					if event.key == pygame.K_ESCAPE:
						running = False
						daw.is_running = False

					daw._on_key_pressed(event.key)
				
				if event.type == pygame.KEYUP:
					daw._on_key_unpressed(event.key)
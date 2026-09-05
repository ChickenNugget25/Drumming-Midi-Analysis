import pygame
import pygame.gfxdraw
import time
import copy
import os
from math import pi, sin, cos, atan, log2, fmod, isclose
from pydub import AudioSegment
from pydub.effects import speedup
from abstract import *
from songsterr_translate import translate_songsterr_data

# notes --
#	I was originally going to have the program play music so you can drum with the music, but
#	that was nowhere near as easy as I thought it would be because the drummers of course aren't
#	always playing musicially perfect, and so little errors accumulate over time. I'm not really
#	sure how Songsterr gets around this, there are these weird 'points' that it keeps track of but
#	I'm not sure how that fixes the issue.

class SheetMusic:

	FPS = 30

	BLACK = (0, 0, 0)
	GREY = (100, 100, 100)
	WHITE = (255, 255, 255)
	GREEN = (0, 255, 0)

	WIDTH, HEIGHT = (1200, 800)

	playing : bool = True

	elapsed_draw_time : float = 0
	elapsed_time : float = 0

	# this just helps us play the midi sounds at the right time, and not play one beat more than once.
	midi_beats_played : int = 0

	# this is for buttons that alter the way the program works:
	BPM_LABEL_MARGIN = (20, 20)
	BPM_SELECTION_TIMEOUT = 5
	bpm_selected : bool = False
	bpm_selected_elapsed_time : float = 0
	displayed_bpm : int
	_paused : bool = False

	# related to key echoes
	key_to_time_pressed = {}
	TIME_UNTIL_ECHO = 0.5
	TIME_PER_ECHO = 0.05

	# you need a getter to have a setter (not really true, but true if you want readability)
	@property
	def paused(self):
		return self._paused

	@paused.setter
	def paused(self, new : bool):
		self._paused = new

		time_per_bar = self.time_signature.numerator * (1.0 / self.bpm) * 60

		self.elapsed_time = (self.played_index - self.start_index) * time_per_bar
		self.midi_beats_played = 0

		if self.play_music:

			if new:
				# going into a pause
				pygame.mixer.music.pause()
			else:
				# stopping a pause
				self.change_speed()
				pygame.mixer.music.play(start= self.played_index * time_per_bar)

	# I can't really think of great way to make this not abhorrently unreadable sooooo
	midi_key_to_bar_pos = {
		DrumType.OpenHiHat: -0.5,
		DrumType.HalfHiHat: -0.5,
		DrumType.ClosedHiHat: -0.5,
		DrumType.HighCrash: -1,
		DrumType.MediumCrash: -0.5,
		DrumType.Ride: 0,
		DrumType.RideBell: 0,
		DrumType.Snare: 1.5,
		DrumType.ElectricSnare: 1.5,
		DrumType.SideStickSnare: 1.5,
		DrumType.HighTom: 0.5,
		DrumType.HiMidTom: 1,
		DrumType.LowMidTom: 1,
		DrumType.LowTom: 2.5,
		DrumType.HighFloorTom: 2.5,
		DrumType.LowFloorTom: 3,
		DrumType.FloorTom: 2.5,
		DrumType.Kick: 3.5,
		DrumType.HiHatControl: 4.5,
		DrumType.Rest: 1.5
	}

	# kinda same here..
	# btw omitting file extension and folder:
	MIDI_FILE_EXTENSION = ".wav"
	MIDI_FOLDER = "midi_samples"
	drum_type_to_midi_file = {
		DrumType.OpenHiHat: "open_hihat",
		DrumType.HalfHiHat: "closed_hihat",
		DrumType.ClosedHiHat: "closed_hihat",
		DrumType.HighCrash: "high_crash",
		DrumType.MediumCrash: "medium_crash",
		DrumType.Ride: "ride",
		DrumType.RideBell: "ride_bell",
		DrumType.Snare: "snare",
		DrumType.ElectricSnare: "snare",
		DrumType.SideStickSnare: "side_stick",
		DrumType.HighTom: "high_tom",
		DrumType.HiMidTom: "mid_tom",
		DrumType.LowMidTom: "mid_tom",
		DrumType.LowTom: "mid_tom",
		DrumType.HighFloorTom: "low_tom",
		DrumType.LowFloorTom: "low_tom",
		DrumType.FloorTom: "low_tom",
		DrumType.Kick: "kick",
		DrumType.HiHatControl: "closed_hihat"
	}

	def __init__(self, data : list[list[dict]], music_name : str = "", bar_index : int = 0, bpm : int = 110, time_signature : Fraction = Fraction(4, 4), play_midi : bool = True, play_music : bool = False):
		self.bar_data = data

		self.start_index = bar_index
		self.drawn_index = bar_index
		self.played_index = bar_index

		self.original_bpm = bpm
		self.bpm = bpm
		self.displayed_bpm = bpm

		self.time_signature = time_signature

		self.play_midi = play_midi and not play_music
		self.play_music = play_music
		self.music_name = music_name

		pygame.init()
		pygame.mixer.init()

		self.drum_type_to_sfx = {}
		for i in self.drum_type_to_midi_file.keys():
			self.drum_type_to_sfx[i] = pygame.mixer.Sound(os.path.join(SheetMusic.MIDI_FOLDER, self.drum_type_to_midi_file[i]) + SheetMusic.MIDI_FILE_EXTENSION)

		self.small_font = pygame.font.Font(None, 26)
		self.surface = pygame.display.set_mode((SheetMusic.WIDTH, SheetMusic.HEIGHT))

		if play_music and music_name:
			# pygame.mixer.music.load(os.path.join(MUSIC_FOLDER, music_name + ".mp3"))
			self.change_speed()

			time_per_bar = self.time_signature.numerator * (1.0 / self.bpm) * 60
			
			pygame.mixer.music.play(start=self.start_index * time_per_bar)
		
		elif self.play_midi:
			pygame.mixer.set_num_channels(128)

	# changes the speed of the song playing in the background (for when you change the bpm)
	def change_speed(self):

		if self.bpm == self.original_bpm:
			pygame.mixer.music.load(os.path.join(MUSIC_FOLDER, self.music_name + ".mp3"))
			return

		# this is gonna be really rough.
		# pygame has no way to change the speed of music, and I did a very tiny amount of research and I'm pretty sure the only way to get around this is by loading the mp3 into pydub, changing it's speed, saving it, and then reloading it into pygame
		# so that's gonna be super super heavy, but because I don't know of a better solution, that's what I'm gonna go with!

		path = os.path.join(MUSIC_FOLDER, self.music_name + ".mp3")

		audio : AudioSegment = AudioSegment.from_file(path)

		# I think the best solution is to create a folder, put all of the copies of the original in there, and then delete the old copies whenever we make a new one.

		folder_path = os.path.join(MUSIC_FOLDER, self.music_name)

		if not os.path.exists(folder_path):
			os.mkdir(folder_path)

		else:
			for i in os.listdir(folder_path):
				os.remove(os.path.join(folder_path, i))

		bpm_difference = self.bpm / self.original_bpm 

		audio = speedup(audio, bpm_difference)

		file = os.path.join(folder_path, "%d.mp3" % self.bpm)

		audio.export(file)

		pygame.mixer.music.load(file)

	def draw_bar(self, bar_data : list[dict], x : int = 0, y : int = 0, bar_width : int = 500, bar_height : int = 100, p : float = 0, is_next : bool = False):

		line_separation = bar_height / 6.0

		bar_left = x
		bar_right = x + bar_width
		bar_top = round(y + line_separation)
		bar_bottom = round(y + bar_height - line_separation)

		note_offset = int((35.0 / 300.0) * bar_width)

		min_size = Fraction(1, 16)
		max_duration = Fraction()
		for beat in bar_data:
			if beat["duration"].number() < min_size.number():
				max_duration += min_size
			else:
				max_duration += beat["duration"]
		
		down_size_amount = 1.0 / max_duration.number()

		if not is_next:
			p = min(max(p, 0), 1)
			if p != 0:

				if p >= 1:
					pygame.gfxdraw.filled_polygon(self.surface, [(bar_left, bar_top), (bar_right, bar_top), (bar_right, bar_bottom), (bar_left, bar_bottom)], SheetMusic.GREEN)
				else:
					x_right = bar_left + note_offset + ((bar_width - note_offset) * (p))

					pygame.gfxdraw.filled_polygon(self.surface, [(bar_left, bar_top), (x_right, bar_top), (x_right, bar_bottom), (bar_left, bar_bottom)], SheetMusic.GREEN)
		else:

			x_right = bar_left + (note_offset * (1 + p))
			pygame.gfxdraw.filled_polygon(self.surface, [(bar_left, bar_top), (x_right, bar_top), (x_right, bar_bottom), (bar_left, bar_bottom)], SheetMusic.GREEN)

		for i in range(5):

			line_y = round(y + ((i + 1) * line_separation))

			pygame.gfxdraw.line(self.surface, bar_left, line_y, bar_right, line_y, SheetMusic.GREY)

		pygame.gfxdraw.line(self.surface, bar_left, bar_top, bar_left, bar_bottom, SheetMusic.GREY)
		pygame.gfxdraw.line(self.surface, bar_right, bar_top, bar_right, bar_bottom, SheetMusic.GREY)


		# for i in range(13):

		# 	c = i / 2.0

		# 	pygame.gfxdraw.circle(self.surface, bar_right + 20, y + int(line_separation * c), 2, SheetMusic.BLACK)


		percent_done = Fraction()

		note_radius_x = int((4.0 / 300.0) * bar_width)
		note_radius_y = int(line_separation * 0.2)

		circle_radius = 10
		cymbal_line_angle = pi / 4.0
		cymbal_coords = pygame.Vector2(circle_radius * cos(cymbal_line_angle), circle_radius * sin(cymbal_line_angle))

		rest_offset = 4

		beam_bottom = y + bar_height

		# dict of start : Fraction, end : Fraction, type : int = (denominator), is_dead : bool, is_weird
		# the 'is_weird' tells us if, when this beam was created, it was given 'beamStart', which we'll say means it can connect with anything??
		beams = []
		# current_beam = {}

		for beat in bar_data:

			is_part_of_beam : bool = False
			for current_beam in beams:
				if current_beam["is_dead"]:
					continue

				smaller = beat["duration"].denominator < current_beam["type"]

				if "beamStop" in beat or (smaller and current_beam["is_weird"]):
					is_part_of_beam = True
					current_beam["end"] = copy.copy(percent_done)
					current_beam["is_dead"] = True
					continue
					
				if smaller:
					current_beam["is_dead"] = True
					continue

				# beam type = duration and beam !dead

				is_part_of_beam = current_beam["type"] == beat["duration"].denominator
				current_beam["end"] = copy.copy(percent_done)
				difference = percent_done - current_beam["start"]

				beat_frac = Fraction(3, current_beam["type"])

				# this probably won't be effected by floating-point errors.
				if difference.number() >= beat_frac.number():
					current_beam["is_dead"] = True

			if not is_part_of_beam and beat["duration"].denominator >= 8:
				beams.append({"start": copy.copy(percent_done), "end": copy.copy(percent_done), "type": beat["duration"].denominator, "is_dead": False, "is_weird": "beamStart" in beat})

			for note in beat["notes"]:

				pos = SheetMusic.midi_key_to_bar_pos[note] + 1

				note_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (percent_done.number() * down_size_amount))
				note_y = y + int(line_separation * pos)

				cymbal_x = note_x + int(circle_radius * cos(cymbal_line_angle))

				# should we draw the cymbal 'X' ?
				# also Crash isn't in here because it draws it's own 'X'.
				if note == DrumType.Ride or note == DrumType.OpenHiHat or note == DrumType.ClosedHiHat or note == DrumType.HiHatControl or note == DrumType.HalfHiHat or note == DrumType.SideStickSnare:
					# pygame.gfxdraw.circle(self.surface, note_x + circle_radius, note_y, circle_radius, SheetMusic.BLACK)

					# on the half hi-hat we only draw the '/' part of the 'X' (not the '\')
					if note != DrumType.HalfHiHat:
						pygame.gfxdraw.line(self.surface, cymbal_x - int(cymbal_coords.x), note_y - int(cymbal_coords.y), cymbal_x + int(cymbal_coords.x), note_y + int(cymbal_coords.y), SheetMusic.BLACK)

					if note == DrumType.OpenHiHat:
						pygame.gfxdraw.circle(self.surface, cymbal_x, note_y, circle_radius, SheetMusic.BLACK)

					pygame.gfxdraw.line(self.surface, cymbal_x - int(cymbal_coords.x), note_y + int(cymbal_coords.y), cymbal_x + int(cymbal_coords.x), note_y - int(cymbal_coords.y), SheetMusic.BLACK)
					pygame.gfxdraw.line(self.surface, note_x, note_y + int(circle_radius * sin(cymbal_line_angle)), note_x, beam_bottom, SheetMusic.GREY)
					continue
					
				elif note == DrumType.HighCrash or note == DrumType.MediumCrash:

					if note == DrumType.HighCrash:
						pygame.gfxdraw.line(self.surface, cymbal_x - circle_radius, note_y, cymbal_x + circle_radius, note_y, SheetMusic.GREY)

					pygame.draw.line(self.surface, SheetMusic.BLACK, (cymbal_x - cymbal_coords.x, note_y - cymbal_coords.y), (cymbal_x + cymbal_coords.x, note_y + cymbal_coords.y), 5)
					pygame.draw.line(self.surface, SheetMusic.BLACK, (cymbal_x - cymbal_coords.x, note_y + cymbal_coords.y), (cymbal_x + cymbal_coords.x, note_y - cymbal_coords.y), 5)

					pygame.gfxdraw.line(self.surface, note_x, note_y + int(circle_radius * sin(cymbal_line_angle)), note_x, beam_bottom, SheetMusic.GREY)
					continue

				elif note == DrumType.Rest:

					denominator = beat["duration"].denominator

					half_rest_thickness = note_radius_x * 3

					match denominator:
						# this works even if the time signature is 3rds or something, right?

						case 1:
							# 1 / 1 (whole note)

							# I'm just setting it to always draw in the middle of the bar.
							pygame.draw.rect(self.surface, SheetMusic.BLACK, pygame.Rect(x + (bar_width * 0.5) - half_rest_thickness, y + 2.5 * line_separation, half_rest_thickness * 2, 0.5 * line_separation), width=100)

						case 2:
							# 1 / 2 (half note)
							
							pygame.draw.rect(self.surface, SheetMusic.BLACK, pygame.Rect(note_x - half_rest_thickness, y + 3 * line_separation, half_rest_thickness * 2, 0.5 * line_separation), width=100)

						case 4:
							# 1 / 4 (quarter note)

							pygame.gfxdraw.circle(self.surface, note_x, note_y, circle_radius, SheetMusic.BLACK)

						case _:

							line_top = 0
							line_bottom = 0
							n_circles = 0

							# this is kinda grossly hard-coded, can't lie.

							if denominator >= 8:
								n_circles = 1
								line_top = 1
								line_bottom = 3

							if denominator >= 16:
								line_bottom = 4
								n_circles = 2

							if denominator >= 32:
								line_top = 0
								n_circles = 3

							if denominator >= 64:
								line_bottom = 5
								n_circles = 4

							pygame.gfxdraw.line(self.surface, note_x - note_radius_x, y + int(line_bottom * line_separation), note_x + note_radius_x, y + int(line_top * line_separation), SheetMusic.BLACK)
							a = atan((note_radius_x * 2) / ((line_bottom - line_top) * line_separation))

							orientation = [1, 2, 0, 3]

							for i in range(n_circles):
								pygame.gfxdraw.filled_circle(self.surface, note_x, y + int(orientation[i] * line_separation), int(line_separation * 0.25), SheetMusic.BLACK)
							
					continue

				pygame.gfxdraw.line(self.surface, note_x, note_y, note_x, beam_bottom, SheetMusic.GREY)
				pygame.gfxdraw.filled_ellipse(self.surface, note_x + note_radius_x, note_y, note_radius_x, note_radius_y, SheetMusic.BLACK)

			if beat["duration"].number() < min_size.number():
				percent_done += min_size
			else:
				percent_done += beat["duration"]

		for i in beams:

			start_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (i["start"].number() * down_size_amount))
			end_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (i["end"].number() * down_size_amount))

			for j in range(int(log2(i["type"])) - 2):

				y_offset = j * 7

				pygame.draw.line(self.surface, SheetMusic.GREY, (start_x, beam_bottom - y_offset), (end_x, beam_bottom - y_offset), width=5)

	# this is just used for playing the midi sounds.
	def non_draw_process(self):

		time_per_bar = self.time_signature.numerator * (1.0 / self.bpm) * 60
		if self.elapsed_time > ((self.played_index - self.start_index) + 1) * time_per_bar:
			self.midi_beats_played = 0
			self.played_index += 1
		
		if not self.play_midi:
			return

		# this feels like it might allow for some notes not playing if they're at the end of the bar, or if a frame takes too long.
		elapsed_time = fmod(self.elapsed_time, time_per_bar)

		time = Fraction()

		for i in range(len(self.bar_data[self.played_index])):

			bar = self.bar_data[self.played_index][i]

			if i != 0:
				time += self.bar_data[self.played_index][i - 1]["duration"]

			if self.midi_beats_played > i:
				continue

			if elapsed_time >= time.number() * time_per_bar:

				for note in bar["notes"]:

					if note == DrumType.Rest:
						continue

					self.drum_type_to_sfx[note].play()

				self.midi_beats_played += 1

		if self.played_index >= len(self.bar_data):
			self.playing = False

	def draw(self):
		self.surface.fill(SheetMusic.WHITE)

		bar_width = int(SheetMusic.WIDTH * 0.5) - 100
		bar_height = 200

		margin_y = 100
		padding_y = 30

		time_per_bar = self.time_signature.numerator * (1.0 / self.bpm) * 60

		relative_elapsed_time = self.elapsed_time - ((self.drawn_index - self.start_index)) * time_per_bar
		relative_time_greater_than_2 = relative_elapsed_time > (time_per_bar * 2)

		for i in range(8):

			if self.drawn_index + i >= len(self.bar_data):
				break

			x = 50 + (i % 2) * bar_width
			y = (i // 2) * (bar_height + padding_y) + margin_y

			p = (relative_elapsed_time - (i * time_per_bar)) / time_per_bar

			if relative_time_greater_than_2:

				time = ((relative_elapsed_time - 2 * time_per_bar) / (2 * time_per_bar))

				y = y - int((bar_height + padding_y) * time)
			
			r = self.small_font.render("%d" % (i + self.drawn_index), True, SheetMusic.BLACK)
			self.surface.blit(r, (x + 10, y))

			self.draw_bar(self.bar_data[self.drawn_index + i], x=x, y=y, bar_width=bar_width, bar_height=bar_height, p=p, is_next = p >= -1 and p <= 0)

		if relative_elapsed_time > 4 * time_per_bar:
			self.drawn_index += 2

		if self.drawn_index >= len(self.bar_data):
			self.playing = False

		pygame.draw.rect(self.surface, SheetMusic.WHITE, pygame.Rect(0, 0, SheetMusic.WIDTH, margin_y // 2))

		bpm_render = self.small_font.render("BPM: %d" % self.displayed_bpm, True, SheetMusic.BLACK)
		self.surface.blit(bpm_render, SheetMusic.BPM_LABEL_MARGIN)

		if self.bpm_selected:

			# kind of annoying this doesn't return a point or vector2
			render_size = bpm_render.get_size()
			render_size = pygame.Vector2(render_size[0] + SheetMusic.BPM_LABEL_MARGIN[0], render_size[1] + SheetMusic.BPM_LABEL_MARGIN[1])

			pygame.gfxdraw.line(self.surface, int(render_size.x), int(render_size.y), int(render_size.x) + 10, int(render_size.y), SheetMusic.BLACK)

		pygame.display.flip()

	def on_mouse_clicked(self, pos : pygame.Vector2):

		size_x, size_y = self.small_font.size("BPM: %d" % self.bpm)

		if pygame.Rect((SheetMusic.BPM_LABEL_MARGIN[0] - (size_x * 0.5), SheetMusic.BPM_LABEL_MARGIN[1] - (size_y * 0.5)), (size_x * 2, size_y * 2)).collidepoint(pos):
			self.bpm_selected = True
			self.bpm_selected_elapsed_time = 0

	def handle_left_right_pressed(self, key):
		if key == pygame.K_RIGHT or key == pygame.K_d or key == pygame.K_LEFT or key == pygame.K_a:
		
			if key == pygame.K_RIGHT or key == pygame.K_d:
				self.start_index = min(self.played_index + 1, len(self.bar_data) - 1)

			elif key == pygame.K_LEFT or key == pygame.K_a:
				self.start_index = max(self.played_index - 1, 0)

			self.drawn_index = self.start_index
			self.played_index = self.start_index

			if not self.paused:
				self.paused = True

	def key_pressed(self, key : int):

		if self.bpm_selected:

			inputted = False

			if key == pygame.K_BACKSPACE:
				self.displayed_bpm //= 10
				inputted = True

			elif key >= pygame.K_0 and key <= pygame.K_9:
				self.displayed_bpm *= 10
				self.displayed_bpm += key - pygame.K_0
				inputted = True

			elif key == pygame.K_KP_ENTER or key == pygame.K_RETURN:
				self.bpm = max(self.displayed_bpm, 1)
				self.bpm_selected = False
				inputted = True

			if inputted:
				self.bpm_selected_elapsed_time = 0
				self.paused = True

		self.handle_left_right_pressed(key)

		if key == pygame.K_RIGHT or key == pygame.K_d or key == pygame.K_LEFT or key == pygame.K_a:
			self.key_to_time_pressed[key] = 0

		if key == pygame.K_UP or key == pygame.K_DOWN:

			if key == pygame.K_UP:
				self.start_index = 0

			elif key == pygame.K_DOWN:
				self.start_index = len(self.bar_data) - 1

			self.drawn_index = self.start_index
			self.played_index = self.start_index

			self.paused = True

		if key == pygame.K_SPACE:
			self.paused = not self.paused

	def key_unpressed(self, key):

		if key in self.key_to_time_pressed:
			self.key_to_time_pressed.pop(key)

	def process(self, delta_time : float):

		if not self.playing:
			return

		if not self.paused:
			self.elapsed_time += delta_time

			self.non_draw_process()

		self.elapsed_draw_time += delta_time

		for i in self.key_to_time_pressed.keys():

			self.key_to_time_pressed[i] += delta_time

			if self.key_to_time_pressed[i] >= SheetMusic.TIME_UNTIL_ECHO:

				n = int((self.key_to_time_pressed[i] - SheetMusic.TIME_UNTIL_ECHO) / SheetMusic.TIME_PER_ECHO)

				for j in range(n):
					self.handle_left_right_pressed(i)

				if n > 0:

					# this is a little weird but allows for less variables
					self.key_to_time_pressed[i] = SheetMusic.TIME_UNTIL_ECHO

		if self.bpm_selected:
			self.bpm_selected_elapsed_time += delta_time

			if self.bpm_selected_elapsed_time >= SheetMusic.BPM_SELECTION_TIMEOUT:
				self.bpm_selected = False
		
		if self.elapsed_draw_time >= (1.0 / SheetMusic.FPS):
			self.elapsed_draw_time = fmod(self.elapsed_time, 1.0 / SheetMusic.FPS)
			self.draw()

if __name__ == "__main__":

	sheet_music = SheetMusic(translate_songsterr_data("song_data/vampire empire.json"), bar_index=0, bpm=116)
	last_time = time.time_ns()

	running = True
	while running:

		delta_time = (time.time_ns() - last_time) * (10 ** -9)
		last_time = time.time_ns()

		sheet_music.process(delta_time)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			
			if event.type == pygame.KEYDOWN:
	
				if event.key == pygame.K_ESCAPE:
					running = False

				sheet_music.key_pressed(event.key)

			if event.type == pygame.KEYUP:
				sheet_music.key_unpressed(event.key)

			# I couldn't find the mouse type enum
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				sheet_music.on_mouse_clicked(event.pos)
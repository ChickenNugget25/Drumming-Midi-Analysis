import pygame
import pygame.gfxdraw
import time
import copy
from math import pi, sin, cos, atan, log2
from abstract import *
from songsterr_translate import translate_songsterr_data

BLACK = (0, 0, 0)
GREY = (100, 100, 100)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)

WIDTH, HEIGHT = (1200, 800)

pygame.init()

surface = pygame.display.set_mode((WIDTH, HEIGHT))

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

def draw_bar(bar_data : list[dict], x : int = 0, y : int = 0, bar_width : int = 500, bar_height : int = 100, p : float = 0):

	line_separation = bar_height / 6.0

	bar_left = x
	bar_right = x + bar_width
	bar_top = round(y + line_separation)
	bar_bottom = round(y + bar_height - line_separation)

	if p != 0:
		pygame.gfxdraw.filled_polygon(surface, [(bar_left, bar_top), (bar_right * p, bar_top), (bar_right * p, bar_bottom), (bar_left, bar_bottom)], GREEN)

	for i in range(5):

		line_y = round(y + ((i + 1) * line_separation))

		pygame.gfxdraw.line(surface, bar_left, line_y, bar_right, line_y, GREY)

	pygame.gfxdraw.line(surface, bar_left, bar_top, bar_left, bar_bottom, GREY)
	pygame.gfxdraw.line(surface, bar_right, bar_top, bar_right, bar_bottom, GREY)


	# for i in range(13):

	# 	c = i / 2.0

	# 	pygame.gfxdraw.circle(surface, bar_right + 20, y + int(line_separation * c), 2, BLACK)

	percent_done = Fraction()

	note_offset = int((35.0 / 300.0) * bar_width)
	down_size_amount = 0.9
	min_size = Fraction(1, 16)
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

			pos = midi_key_to_bar_pos[note] + 1

			note_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (percent_done.number() * down_size_amount))
			note_y = y + int(line_separation * pos)

			cymbal_x = note_x + int(circle_radius * cos(cymbal_line_angle))

			# should we draw the cymbal 'X' ?
			# also Crash isn't in here because it draws it's own 'X'.
			if note == DrumType.Ride or note == DrumType.OpenHiHat or note == DrumType.ClosedHiHat or note == DrumType.HiHatControl or note == DrumType.HalfHiHat or note == DrumType.SideStickSnare:
				# pygame.gfxdraw.circle(surface, note_x + circle_radius, note_y, circle_radius, BLACK)

				# on the half hi-hat we only draw the '/' part of the 'X' (not the '\')
				if note != DrumType.HalfHiHat:
					pygame.gfxdraw.line(surface, cymbal_x - int(cymbal_coords.x), note_y - int(cymbal_coords.y), cymbal_x + int(cymbal_coords.x), note_y + int(cymbal_coords.y), BLACK)

				pygame.gfxdraw.line(surface, cymbal_x - int(cymbal_coords.x), note_y + int(cymbal_coords.y), cymbal_x + int(cymbal_coords.x), note_y - int(cymbal_coords.y), BLACK)
				pygame.gfxdraw.line(surface, note_x, note_y + int(circle_radius * sin(cymbal_line_angle)), note_x, beam_bottom, GREY)
				continue
				
			elif note == DrumType.HighCrash or note == DrumType.MediumCrash:

				if note == DrumType.HighCrash:
					pygame.gfxdraw.line(surface, cymbal_x - circle_radius, note_y, cymbal_x + circle_radius, note_y, GREY)

				pygame.draw.line(surface, BLACK, (cymbal_x - cymbal_coords.x, note_y - cymbal_coords.y), (cymbal_x + cymbal_coords.x, note_y + cymbal_coords.y), 5)
				pygame.draw.line(surface, BLACK, (cymbal_x - cymbal_coords.x, note_y + cymbal_coords.y), (cymbal_x + cymbal_coords.x, note_y - cymbal_coords.y), 5)

				pygame.gfxdraw.line(surface, note_x, note_y + int(circle_radius * sin(cymbal_line_angle)), note_x, beam_bottom, GREY)
				continue

			elif note == DrumType.Rest:

				denominator = beat["duration"].denominator

				match denominator:
					# this works even if the time signature is 3rds or something, right?

					case 1:
						# 1 / 1 (whole note)

						# I'm just setting it to always draw in the middle of the bar.
						pygame.draw.rect(surface, BLACK, pygame.Rect(x + (bar_width * 0.5) - note_radius_x, y + 1.5 * line_separation, note_radius_x * 2, 0.5 * line_separation), width=-1)

					case 2:
						# 1 / 2 (half note)
						
						pygame.draw.rect(surface, BLACK, pygame.Rect(note_x - note_radius_x, y + 2 * line_separation, note_radius_x * 2, 0.5 * line_separation), width=-1)

					case _:

						line_top = 0
						line_bottom = 0
						n_circles = 0

						# this is kinda grossly hard-coded, can't lie.
						if denominator >= 4:
							line_top = 1
							line_bottom = 3

						if denominator >= 8:
							n_circles = 1

						if denominator >= 16:
							line_bottom = 4
							n_circles = 2

						if denominator >= 32:
							line_top = 0
							n_circles = 3

						if denominator >= 64:
							line_bottom = 5
							n_circles = 4
					
						pygame.gfxdraw.line(surface, note_x - note_radius_x, y + int(line_bottom * line_separation), note_x + note_radius_x, y + int(line_top * line_separation), BLACK)
						a = atan((note_radius_x * 2) / ((line_bottom - line_top) * line_separation))

						orientation = [1, 2, 0, 3]

						for i in range(n_circles):
							pygame.gfxdraw.filled_circle(surface, note_x, y + int(orientation[i] * line_separation), int(line_separation * 0.25), BLACK)

			pygame.gfxdraw.line(surface, note_x, note_y, note_x, beam_bottom, GREY)
			pygame.gfxdraw.filled_ellipse(surface, note_x + note_radius_x, note_y, note_radius_x, note_radius_y, BLACK)

		if beat["duration"].number() < min_size.number():
			percent_done += min_size
		else:
			percent_done += beat["duration"]

	for i in beams:

		start_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (i["start"].number() * down_size_amount))
		end_x = note_offset + int(bar_left + ((bar_right - note_offset) - bar_left) * (i["end"].number() * down_size_amount))

		for j in range(int(log2(i["type"])) - 2):

			y_offset = j * 7

			pygame.draw.line(surface, GREY, (start_x, beam_bottom - y_offset), (end_x, beam_bottom - y_offset), width=5)

def draw(data, index):
	surface.fill(WHITE)

	bar_width = int(WIDTH * 0.5) - 100
	bar_height = 200
	offset_y = 30

	for i in range(4):
		x = i % 2
		y = i // 2

		draw_bar(data[index + i], x=50 + (bar_width * x), y=100 + ((bar_height + offset_y) * y), bar_width=bar_width, bar_height=bar_height)

	pygame.display.flip()

if __name__ == "__main__":

	data = translate_songsterr_data("stuff/undone.json")

	index = 42

	last_time = time.time_ns()
	elapsed_draw_time = 0

	FPS = 30

	running = True
	while running:

		delta_time = (time.time_ns() - last_time) * (10 ** -9)
		last_time = time.time_ns()
		elapsed_draw_time += delta_time

		if elapsed_draw_time > (1.0 / FPS):
			elapsed_draw_time = 0
			draw(data, index)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			
			if event.type == pygame.KEYDOWN:
	
				if event.key == pygame.K_ESCAPE:
					running = False

				elif event.key == pygame.K_RIGHT:
					index += 1

				elif event.key == pygame.K_LEFT:
					index -= 1
import pygame
import pygame.gfxdraw
import pygame.transform
import time
import copy
import os
import numpy as np
from math import pi, sin, cos, fmod, dist

# pygame.init()

def distance(x, y):
	return abs(x - y)

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

class DAW:

	FPS = 30
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

	def __init__(self):

		pygame.init()
		pygame.mixer.init()

		self.surface = pygame.display.set_mode((self.width, self.height))

		self.small_font = pygame.font.Font(None, 26)

		pygame.mixer.set_num_channels(128)

	def draw_box(self, bg_scaledown_amount):

		inverse_bg_scale_down_amount = 1.0 / bg_scaledown_amount

		box_margin = inverse_bg_scale_down_amount

		middle = (pygame.Vector2(self.width, self.height) / 2.0)
		bottom_right = pygame.Vector2(self.width, self.height)

		box_size = middle - pygame.Vector2(1, 1) * box_margin * 2 - pygame.Vector2(1, 1) * (inverse_bg_scale_down_amount * 0.5)
		box_pos = bottom_right - (box_size + pygame.Vector2(1, 1) * box_margin)

		# make it 1/8 the size
		scale_down_amount = 0.125
		draw_surface = pygame.Surface(box_size * scale_down_amount)
		pixels = pygame.surfarray.pixels2d(draw_surface)

		effective_box_size = box_size * scale_down_amount
		inverse_scale_down_amount = 1.0 / scale_down_amount
		# amplitude = effective_box_size.y * 0.125
		amplitude = 2

		# time it takes for the sin wave to go all the way through? (s)
		time_per_box = 2

		# time for the thing to slowly 'tween' back to zero so it doesn't hurt your eyes
		grace_period = 0.5
		relative_elapsed_time = fmod(self.elapsed_time, time_per_box + grace_period)

		for col, row in np.ndindex(pixels.shape):

			if (col + row) % 2 == 0:
				pixels[col, row] = 0x742c9e
			else:
				pixels[col, row] = 0x69288f

			time_to_use = relative_elapsed_time
			if relative_elapsed_time > time_per_box:
				time_to_use = (1.0 - ((relative_elapsed_time - time_per_box) / grace_period)) * time_per_box
			
			if (col / effective_box_size.x) > (time_to_use / time_per_box):
				continue

			r = round(amplitude * sin((col + relative_elapsed_time * 15)) + (effective_box_size.y * 0.5))

			if row > r - (amplitude * 0.6) and row < r + (amplitude * 0.6):
				pixels[col, row] = DAW.BLACK_HEX				

		del pixels

		# scale it back up
		scaled_surface = pygame.transform.scale(draw_surface, box_size)
		self.surface.blit(scaled_surface, box_pos)
		
		gfxdraw_box(self.surface, box_pos.x, box_pos.y, box_size.x, box_size.y, DAW.BLACK)

	def draw(self):

		bg_scaledown_amount = 1.0 / 32.0

		surface_size = pygame.Vector2(self.width, self.height) * bg_scaledown_amount

		# bg_surface = pygame.Surface((round(surface_size.x), round(surface_size.y)))
		bg_surface = pygame.Surface(pygame.Vector2(self.width, self.height) * bg_scaledown_amount)

		bg_pixels = pygame.surfarray.pixels2d(bg_surface)

		bg_surface.fill((164, 90, 156))

		for col, row in np.ndindex(bg_pixels.shape):

			if (col + row) % 2 == 0:
				bg_pixels[col, row] = 0x965490

		del bg_pixels

		scaled_surface = pygame.transform.scale(bg_surface, pygame.Vector2(self.width, self.height))
		self.surface.blit(scaled_surface, (0, 0))

		self.draw_box(bg_scaledown_amount)

		# render = self.small_font.render("%d" % (self.draw_frame_index % 10), True, DAW.BLACK)
		# self.surface.blit(render, (10, 10))

		pygame.display.flip()

	def process(self, delta_time : float):

		self.draw_elapsed_time += delta_time
		self.elapsed_time += delta_time

		if self.draw_elapsed_time >= (1.0 / DAW.FPS):
			self.draw_elapsed_time = fmod(self.draw_elapsed_time, 1.0 / DAW.FPS)
			self.draw()

			self.draw_frame_index += 1

if __name__ == "__main__":

	daw = DAW()
	last_time = time.time_ns()

	running = True
	while running:

		delta_time = (time.time_ns() - last_time) * (10**-9)
		last_time = time.time_ns()

		daw.process(delta_time)

		for event in pygame.event.get():

			if event.type == pygame.QUIT:
				running = False

			if event.type == pygame.KEYDOWN:

				if event.key == pygame.K_ESCAPE:
					running = False

				# daw.key_pressed(event.key)
			
			if event.type == pygame.KEYUP:
				pass
				# daw.key_unpressed(event.key)
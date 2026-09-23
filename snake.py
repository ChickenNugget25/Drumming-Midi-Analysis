import pygame
import random
import numpy as np
import time

class Snake:

	ROWS = 10
	COLUMNS = 10

	FPS = 5

	BLACK = (0, 0, 0)
	BG = (0, 255, 0)

	elapsed_time : float = 0

	snake = [pygame.Vector2(1, COLUMNS // 2), pygame.Vector2(2, COLUMNS // 2), pygame.Vector2(3, COLUMNS // 2)]
	apple = pygame.Vector2(2 + (ROWS // 2), COLUMNS // 2)
	hsp = 1
	vsp = 0
	valid_inputs : bool = True

	running : bool = True

	def __init__(self):
		pygame.init()
		pygame.font.init()

		# self.width, self.height = pygame.display.get_desktop_sizes()[0]
		self.width, self.height = (500, 500)
		self.font = pygame.font.Font(None, size=24)

		self.surface = pygame.display.set_mode((self.width, self.height))
		pygame.display.set_caption("Snake")
		# pygame.display.toggle_fullscreen()

	def key_pressed(self, key):

		if not self.valid_inputs:
			return

		if self.hsp == 0:
			if (key == pygame.K_RIGHT or key == pygame.K_d):
				self.hsp = 1
				self.vsp = 0
				self.valid_inputs = False
			elif (key == pygame.K_LEFT or key == pygame.K_a):
				self.hsp = -1
				self.vsp = 0
				self.valid_inputs = False
		elif self.vsp == 0:
			if (key == pygame.K_UP or key == pygame.K_w):
				self.vsp = -1
				self.hsp = 0
				self.valid_inputs = False
			elif (key == pygame.K_DOWN or key == pygame.K_s):
				self.vsp = 1
				self.hsp = 0
				self.valid_inputs = False

	def draw(self):

		unusable_width = self.width - self.height
		# draw_surface = pygame.Surface(pygame.Vector2(Snake.ROWS, Snake.COLUMNS))
		# pixels = pygame.surfarray.array2d(draw_surface)

		# self.surface.fill((255, 255, 255))

		# for x, y in np.ndindex(pixels.shape):
		# 	if (x + y) % 2 == 0:
		# 		pixels[x, y] = 0x00ff00
		# 	else:
		# 		pixels[x, y] = 0x0000ff

		# # del pixels

		# # print(pygame.surfarray.array2d(draw_surface))

		# scaled = pygame.transform.scale(draw_surface, pygame.Vector2(Snake.ROWS, Snake.COLUMNS) * 2)
		# self.surface.blit(scaled, (0, 0))

		bg_surface = pygame.Surface(pygame.Vector2(Snake.ROWS, Snake.COLUMNS))
		bg_pixels = pygame.surfarray.pixels2d(bg_surface)

		bg_surface.fill((50, 125, 50))

		for x, y in np.ndindex(bg_pixels.shape):

			if (x + y) % 2 == 0:
				bg_pixels[x, y] = 0x519617
			
			for piece in self.snake:
				if piece.x == x and piece.y == y:
					bg_pixels[x, y] = 0xc23b15
					break

			if x == self.apple.x and y == self.apple.y:
				bg_pixels[x, y] = 0x00ff00

		del bg_pixels

		scaled_surface = pygame.transform.scale(bg_surface, pygame.Vector2(self.height, self.height))

		self.surface.blit(scaled_surface, (0, 0))

		score_label = self.font.render("Score: %d" % (len(self.snake) - 3), False, (255, 255, 255))
		self.surface.blit(score_label, (0, 0))

		pygame.display.flip()

	def do_process(self):

		self.valid_inputs = True

		next_pos = self.snake[-1] + pygame.Vector2(self.hsp, self.vsp)

		if next_pos.x >= Snake.ROWS or next_pos.x < 0:
			self.running = False
			return
		elif next_pos.y >= Snake.COLUMNS or next_pos.y < 0:
			self.running = False
			return

		for i in range(1, len(self.snake)):
			if next_pos == self.snake[i]:
				self.running = False
				return

		if next_pos == self.apple:
			self.snake.insert(0, pygame.Vector2(0, 0))

			valid_squares = []
			for x in range(Snake.ROWS):
				for y in range(Snake.COLUMNS):
					c = pygame.Vector2(x, y)
					valid_squares.append(c)

			for i in range(1, len(self.snake)):
				valid_squares.remove(self.snake[i])

			valid_squares.remove(next_pos)

			if len(valid_squares) == 0:
				self.running = False
				return

			self.apple = random.choice(valid_squares)

		for i in range(len(self.snake) - 1):
			self.snake[i] = self.snake[i + 1]
		
		self.snake[-1] = next_pos
	
	def process(self, delta_time : float):

		if not self.running:
			return

		self.elapsed_time += delta_time

		if self.elapsed_time > (1.0 / Snake.FPS):
			self.elapsed_time = 0
			self.do_process()
			self.draw()


running = True
snake = Snake()
last_time = time.time_ns()

while running:

	delta_time = (time.time_ns() - last_time) * 10 ** -9
	last_time = time.time_ns()

	snake.process(delta_time)

	for event in pygame.event.get():

		if event.type == pygame.QUIT:
			running = False

		if event.type == pygame.KEYDOWN:

			if event.key == pygame.K_ESCAPE:
				running = False

			snake.key_pressed(event.key)
			
			
		elif event.type == pygame.KEYUP:
			pass
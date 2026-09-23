import pygame
from pygame import Vector2
import time

pygame.init()
pygame.font.init()

width, height = (400, 400)
surface = pygame.display.set_mode((width, height))

font = pygame.font.Font(None, 24)

class UI:

	# like Godot
	class TextEdit:

		selected = False
		text = ""

		def __init__(self, position : Vector2, size : Vector2 = Vector2(100, 50)) -> None:
			self.position = position
			self.size = size

		def draw(self, surface : pygame.Surface) -> None:
			surface.blit()
	
	selected = None

	def __init__(self) -> None:
		pass

	def _on_mouse_click(self) -> None:
		pass






last_time = time.time_ns()

FPS = 30
draw_time : float = 0

running = True
while running:

	delta_time = (time.time_ns() - last_time) * 10 ** -9
	last_time = time.time_ns()

	draw_time += delta_time

	if draw_time > 1.0 / FPS:
		surface.fill((255, 255, 255))
		pygame.display.flip()

	for event in pygame.event.get():

		if event.type == pygame.QUIT:
			running = False

	
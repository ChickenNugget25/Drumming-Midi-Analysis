import pygame.midi
import pygame
import time

# in ms
MAX_DEVIANCE = 10

pygame.midi.init()
input_id = pygame.midi.get_default_input_id()

if input_id != -1:
    midi_input = pygame.midi.Input(input_id)
else:
    print("no midi device.")
    quit()

pygame.init()

# width = 400
# height = 400

# screen = pygame.display.set_mode((width, height))

def await_midi_input():

    if not midi_input:
        return []

    while True:
        if midi_input.poll():
            return midi_input.read(10)

elapsed_time = 0

BPM = 95

while True:

    last_time = time.time_ns()
    await_midi_input()

    # ms
    time_since_last = (time.time_ns() - last_time) * 10 ** -6

    # perfect_play_time_ns
    perfect_play = ((1.0 / BPM) * 60) * 10 ** 3

    if time_since_last < perfect_play - MAX_DEVIANCE:
        print("rushing")
    elif time_since_last > perfect_play + MAX_DEVIANCE:
        print("dragging")
    else:
        print("perfect!")
    
    print("difference from perfect: %s" % (time_since_last - perfect_play))

    # play = ((1.0 / BPM) * 60) * 10 ** 3
    # (play * 10 ** -3) / 60 = 1.0 / BPM
    # 60.0 / (play * 10 ** -3) = BPM

    print("played BPM: %s" % (60.0 / (time_since_last * 10 ** -3)))

    print(time_since_last)
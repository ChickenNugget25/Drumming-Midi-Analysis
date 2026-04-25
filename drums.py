import pygame.midi
import pygame
from enum import Enum
import time
from math import sqrt

BLACK = (0,0,0)
WHITE = (255,255,255)

BIG_NUMBER = 999999

replicube_ass_debug = [BLACK, (255,0,0), (0,255,0), (0,0,255)]

pygame.midi.init()
input_id = pygame.midi.get_default_input_id()

if input_id != -1:
    midi_input = pygame.midi.Input(input_id)

pygame.init()

# I haven't even seen 32th-notes yet in practice so I'm just not even coding them, lol. Maybe I'll change this once I encounter them.
class NoteType(Enum):
    QuarterNote = 0,
    QuarterNoteDotted = 1,
    EighthNote = 2,
    EighthNoteDotted = 3,
    SixteenthNote = 4,
    SixteenthNoteDotted = 5,
    QuarterRest = 6,
    EighthRest = 7,
    SixteenthRest = 8

    @staticmethod
    def note_to_note_no_dots(note_type):

        match (note_type):
            case NoteType.QuarterNoteDotted:
                return NoteType.QuarterNote
            case NoteType.EighthNoteDotted:
                return NoteType.EighthNote
            case NoteType.SixteenthNoteDotted:
                return NoteType.SixteenthNote
        
        return note_type

# using 32th instead of 16ths just makes the numbers integers which seems easier.
# NOTE_TYPE_TO_32TH_LENGTH = [8, 12, 4, 6, 2, 3, 8, 4, 2]

NOTE_TYPE_TO_32TH_LENGTH = {
    NoteType.QuarterNote: 8,
    NoteType.QuarterNoteDotted: 12,
    NoteType.EighthNote: 4,
    NoteType.EighthNoteDotted: 6,
    NoteType.SixteenthNote: 2,
    NoteType.SixteenthNoteDotted: 3,
    NoteType.QuarterNote: 8,
    NoteType.EighthRest: 4,
    NoteType.SixteenthRest: 2
}

class DrumType(Enum):
    HiHatOpen = 0,
    HiHatClosed = 1,
    Crash = 2,
    Ride = 3,
    Snare = 4,
    HighTom = 5,
    MidTom = 6,
    FloorTom = 7,
    Kick = 8,
    HiHatControl = 9

    @staticmethod
    def is_cymbol_hit(hit_type):

        if (hit_type == DrumType.HiHatOpen or hit_type == DrumType.HiHatClosed or hit_type == DrumType.Crash or hit_type == DrumType.Ride or hit_type == DrumType.HiHatControl):
            return True

        return False

# just going to be a integer, the top of the clef (the top f) will be 0
# HIT_TYPE_TO_POSITION_ON_CLEF = [-1, -1, -2, 0, 4, 1, 2, 5, 7, 9]

TOP_OF_CLEF_POSITION = 0
MIDDLE_OF_CLEF_POSITION = 4
BOTTOM_OF_CLEF_POSITION = 8


HIT_TYPE_TO_POSITION_ON_CLEF = {
    DrumType.HiHatOpen: -1,
    DrumType.HiHatClosed: -1,
    DrumType.Crash: -2,
    DrumType.Ride: 0,
    DrumType.Snare: 4,
    DrumType.HighTom: 1,
    DrumType.MidTom: 2,
    DrumType.FloorTom: 5,
    DrumType.Kick: 7,
    DrumType.HiHatControl: 9
}

sprite_sheet = pygame.image.load("Notes.png")

def get_note_type(frame):
    return sprite_sheet.subsurface(pygame.Rect(frame*32,0,32,32))

def await_midi_input():

    if not midi_input:
        return []

    while True:
        if midi_input.poll():
            return midi_input.read(10)


WIDTH = 800
HEIGHT = 600
BPM = 95

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
# screen = pygame.display.set_mode((WIDTH, HEIGHT))

# we're passing in a list for each subdivision of the beat which will contain each type of drum played. (and also the duration of that hit)
def draw_bar(data : list[list[tuple[DrumType, NoteType]]]):

    # draw bar (where notes will be placed)
    BAR_PADDING = 100
    CLEF_HEIGHT = 200

    half_screen_height = HEIGHT / 2.0
    half_clef_height = CLEF_HEIGHT / 2.0

    # pygame.draw.rect(screen, (255,255,255), pygame.Rect(0,0,WIDTH,HEIGHT))
    screen.fill(WHITE)

    pygame.draw.line(screen, BLACK, (BAR_PADDING, half_screen_height - half_clef_height), (BAR_PADDING, half_screen_height + half_clef_height), width=3)
    pygame.draw.line(screen, BLACK, (WIDTH - BAR_PADDING, half_screen_height - half_clef_height), (WIDTH - BAR_PADDING, half_screen_height + half_clef_height), width=3)

    for i in range(5):

        y_value = (half_screen_height - half_clef_height) + (CLEF_HEIGHT / 4.0) * i

        pygame.draw.line(screen, BLACK, (BAR_PADDING, y_value), (WIDTH - BAR_PADDING, y_value), width=2)

    # draw notes
    NOTE_PADDING = 50
    CYMBAL_SYMBOL_LENGTH = 10
    NOTE_ELLIPSE_WIDTH = 15
    NOTE_ELLIPSE_HEIGHT = 10
    NOTE_TAIL_HEIGHT = 30

    BAR_START_HEIGHT = half_screen_height - half_clef_height

    BEAM_OFFSET = 50
    BEAM_POSITION_BOTTOM = half_screen_height + half_clef_height + BEAM_OFFSET
    BEAM_POSITION_TOP = half_screen_height - (half_clef_height + BEAM_OFFSET)
    HALF_BEAM_Y_SIZE = 2

    # in quarter note durations
    MAX_BEAM_WIDTH = 2

    # loop until we find a not-the-same note length (ignore dotted notes..?) then include the one found in the search (if it has a same-length note and a not-same-length note)
    n_32ths = 0

    # [(beam_end, duration_32ths), (beam_end, duration_32ths), (beam_end, duration_32ths)]
    beam_until = [(0,0)]
    drawing_beam : bool = False
    beam_drawn_on_top = False

    for i in range(len(data)):

        shortest_duration = BIG_NUMBER

        for j in data[i]:
            drum_type = j[0]
            note_type = j[1]
            note_type_no_dots = NoteType.note_to_note_no_dots(note_type)

            x_pos = NOTE_PADDING + BAR_PADDING + (n_32ths / 28.0) * (WIDTH - (BAR_PADDING + NOTE_PADDING) * 2)
            y_pos = BAR_START_HEIGHT + (HIT_TYPE_TO_POSITION_ON_CLEF[drum_type] / 8.0) * CLEF_HEIGHT
            is_cymbol_hit = DrumType.is_cymbol_hit(drum_type)

            # if n_32ths > beam_until[-1][0] or beam_until[-1][0] == 0:
            if (not drawing_beam) or n_32ths > beam_until[0][0]:

                # the number of 32ths to draw beam to
                beam_length_32ths = 0
                beam_until = []
                # beam_index = 0
                search_index = i
                last_shortest_duration = 0
                all_time_shortest_duration = BIG_NUMBER
                search_note_length = NOTE_TYPE_TO_32TH_LENGTH[note_type_no_dots]

                beam_drawn_on_top = HIT_TYPE_TO_POSITION_ON_CLEF[drum_type] > MIDDLE_OF_CLEF_POSITION

                # 1 quarter note = 1/4, 1 32th note = 1/32, so there're 8 32th notes in a quarter note.
                while (beam_length_32ths < MAX_BEAM_WIDTH * 8) and (search_index < len(data)):
                    
                    i_shortest_duration = BIG_NUMBER
                    note_length_equal_or_less_than_found : bool = True
                    all_durations_are_equal : bool = True

                    for k in data[search_index]:
                        
                        # we'll only draw the beam on top if NONE of the notes are above the middle of the clef.
                        if beam_drawn_on_top:
                            beam_drawn_on_top = HIT_TYPE_TO_POSITION_ON_CLEF[k[0]] > MIDDLE_OF_CLEF_POSITION

                        i_note_type = NoteType.note_to_note_no_dots(k[1])

                        # kind of janky/gross solution to proritize grouping in quarters of the beat
                        if NOTE_TYPE_TO_32TH_LENGTH[i_note_type] > search_note_length and 2 >= beam_length_32ths % 8:
                            note_length_equal_or_less_than_found = False

                        if NOTE_TYPE_TO_32TH_LENGTH[i_note_type] < i_shortest_duration:

                            if i_shortest_duration != BIG_NUMBER:
                                all_durations_are_equal = False

                            i_shortest_duration = NOTE_TYPE_TO_32TH_LENGTH[i_note_type]

                        # i_shortest_duration = min(i_shortest_duration, NOTE_TYPE_TO_32TH_LENGTH[i_note_type])
                        search_note_length = min(search_note_length, i_shortest_duration)

                    last_shortest_duration = i_shortest_duration
                    if (not note_length_equal_or_less_than_found) or i_shortest_duration >= 8:
                        break
                    
                    if i_shortest_duration < all_time_shortest_duration:

                        drawing_beam = True

                        # print(f"{i_shortest_duration=}")

                        # if all_time_shortest_duration != BIG_NUMBER or not all_durations_are_equal:
                        beam_until.insert(0, (n_32ths + beam_length_32ths, i_shortest_duration))

                        all_time_shortest_duration = i_shortest_duration
                        # beam_index += 1

                        # if beam_index >= len(beam_until):
                        #     beam_until.append(0)

                    beam_length_32ths += i_shortest_duration
                    search_index += 1

                # beam_until.append((n_32ths + beam_length_32ths - last_shortest_duration, last_shortest_duration))

                if drawing_beam:
                    drawing_beam = True
                    beam_until.insert(0, (n_32ths + beam_length_32ths - last_shortest_duration, last_shortest_duration))
                    # print(f"{beam_until=}")
                    
                    biggest_beam_width = 0
                    for beam in beam_until:
                        biggest_beam_width = max(biggest_beam_width, beam[0])
                    
                    # print(f"{biggest_beam_width=}")

                    for beam_index_i in range(len(beam_until)):

                        # probably a bad solution:
                        # if beam_until[beam_index_i][0] == biggest_beam_width:
                        #     continue

                        beam_end_x = NOTE_PADDING + BAR_PADDING + (biggest_beam_width / 28.0) * (WIDTH - (BAR_PADDING + NOTE_PADDING) * 2) - CYMBAL_SYMBOL_LENGTH

                        # beam_start_x = x_pos
                        # if is_cymbol_hit:
                        #     beam_start_x -= CYMBAL_SYMBOL_LENGTH

                        beam_start_x = NOTE_PADDING + BAR_PADDING + (beam_until[beam_index_i][0] / 28.0) * (WIDTH - (BAR_PADDING + NOTE_PADDING) * 2) - CYMBAL_SYMBOL_LENGTH

                        beam_y_pos = BEAM_POSITION_BOTTOM - HALF_BEAM_Y_SIZE
                        if beam_drawn_on_top:
                            beam_y_pos = BEAM_POSITION_TOP - HALF_BEAM_Y_SIZE
                        
                        beam_y_pos -= (2-(beam_until[beam_index_i][1] / 2.0)) * 5
                        # print(f"{beam_index_i}, ({beam_start_x:.2f}:{beam_end_x:.2f}, {beam_y_pos}) a.k.a. {beam_until[beam_index_i][0]}:{biggest_beam_width}")

                        pygame.draw.line(screen, BLACK, (beam_start_x, beam_y_pos), (beam_end_x, beam_y_pos), width=HALF_BEAM_Y_SIZE*2)
                else:
                    beam_until = [(0,0)]
                    drawing_beam = False

            if is_cymbol_hit:
                # draw cymbol X
                pygame.draw.line(screen, BLACK, (x_pos + CYMBAL_SYMBOL_LENGTH, y_pos + CYMBAL_SYMBOL_LENGTH), (x_pos - CYMBAL_SYMBOL_LENGTH, y_pos - CYMBAL_SYMBOL_LENGTH), width=2)
                pygame.draw.line(screen, BLACK, (x_pos - CYMBAL_SYMBOL_LENGTH, y_pos + CYMBAL_SYMBOL_LENGTH), (x_pos + CYMBAL_SYMBOL_LENGTH, y_pos - CYMBAL_SYMBOL_LENGTH), width=2)
            else:
                # draw note

                # subtracting by cymbal length just ensures it's drawn on the same x as the cymbal symbols.
                x_pos -= CYMBAL_SYMBOL_LENGTH

                # and the plus 2 here is just for aesthetic reasons, I just think it looks better a bit offset.
                pygame.draw.ellipse(screen, BLACK, pygame.Rect(x_pos + 2, y_pos - (NOTE_ELLIPSE_HEIGHT / 2.0), NOTE_ELLIPSE_WIDTH, NOTE_ELLIPSE_HEIGHT))

            # draw beam
            if drawing_beam and n_32ths <= beam_until[0][0]:

                beam_y_pos = BEAM_POSITION_BOTTOM 
                if beam_drawn_on_top:
                    beam_y_pos = BEAM_POSITION_TOP

                if is_cymbol_hit:
                    pygame.draw.line(screen, BLACK, (x_pos - CYMBAL_SYMBOL_LENGTH, y_pos + CYMBAL_SYMBOL_LENGTH), (x_pos - CYMBAL_SYMBOL_LENGTH, beam_y_pos), width=2)
                else:
                    pygame.draw.line(screen, BLACK, (x_pos, y_pos), (x_pos, beam_y_pos), width=2)
            elif not is_cymbol_hit:
                pygame.draw.line(screen, BLACK, (x_pos, y_pos), (x_pos, y_pos + NOTE_TAIL_HEIGHT), width=2)

            # if it's a hihat open note, we'll also draw the circle around the X.
            if drum_type == DrumType.HiHatOpen:
                pygame.draw.circle(screen, BLACK, (x_pos, y_pos), sqrt(CYMBAL_SYMBOL_LENGTH ** 2 + CYMBAL_SYMBOL_LENGTH ** 2), width=2)

            shortest_duration = min(shortest_duration, NOTE_TYPE_TO_32TH_LENGTH[note_type])
        
        n_32ths += shortest_duration
    
    pygame.display.flip()

# draw_bar([[(DrumType.HiHatClosed, NoteType.EighthNote), (DrumType.Kick, NoteType.EighthNote)], [(DrumType.HiHatClosed, NoteType.EighthNote)], [(DrumType.HiHatClosed, NoteType.EighthNote), (DrumType.Snare, NoteType.EighthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote)],
#           [(DrumType.HiHatClosed, NoteType.EighthNote), (DrumType.Kick, NoteType.EighthNote)], [(DrumType.HiHatClosed, NoteType.EighthNote)], [(DrumType.HiHatClosed, NoteType.EighthNote), (DrumType.Snare, NoteType.EighthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote)]])

draw_bar([[(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Kick, NoteType.EighthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Kick, NoteType.SixteenthNote)], [(DrumType.Kick, NoteType.SixteenthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Snare, NoteType.SixteenthNote)], [(DrumType.Snare, NoteType.SixteenthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote)],
          [(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Kick, NoteType.EighthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Kick, NoteType.SixteenthNote)], [(DrumType.Kick, NoteType.SixteenthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote), (DrumType.Snare, NoteType.SixteenthNote)], [(DrumType.Snare, NoteType.SixteenthNote)], [(DrumType.HiHatOpen, NoteType.EighthNote)]])

# draw_bar([[(DrumType.Snare, NoteType.QuarterNote)], [(DrumType.Snare, NoteType.QuarterNote)], [(DrumType.Snare, NoteType.QuarterNote)], [(DrumType.Snare, NoteType.QuarterNote)]])

input()
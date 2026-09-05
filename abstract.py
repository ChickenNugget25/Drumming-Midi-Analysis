from enum import Enum

SONG_JSON_FOLDER = "song_data"
MUSIC_FOLDER = "music"

# I haven't even seen 32th-notes yet in practice so I'm just not even coding them, lol. Maybe I'll change this once I encounter them.
class NoteDuration(Enum):
	WholeNote = -2,
	HalfNote = -1,
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
			case NoteDuration.QuarterNoteDotted:
				return NoteDuration.QuarterNote
			case NoteDuration.EighthNoteDotted:
				return NoteDuration.EighthNote
			case NoteDuration.SixteenthNoteDotted:
				return NoteDuration.SixteenthNote
		
		return note_type

class DrumType(Enum):
	OpenHiHat = 46,
	HalfHiHat = 92,
	ClosedHiHat = 42,
	HighCrash = 49,
	MediumCrash = 57,
	Ride = 51,
	RideBell = 53,
	Snare = 38,
	ElectricSnare = 40,
	SideStickSnare = 37,
	HighTom = 50,
	HiMidTom = 48,
	MidTom = 48,
	LowMidTom = 47,
	LowTom = 45,
	HighFloorTom = 43,
	LowFloorTom = 41,
	FloorTom = 41,
	Kick = 36,
	HiHatControl = 93,
	Rest = -1

# idk if I really need this but it's fancy
class Fraction:

	def __init__(self, numerator : int = 0, denominator : int = 1):
		self.numerator : int = numerator
		self.denominator : int = denominator

	# this is ripped from the internet and converted to python.
	# btw this is an in-place addition override function
	def __iadd__(self, other):

		den = Fraction.gcd(self.denominator, other.denominator)

		num = self.numerator * (den / self.denominator) + other.numerator * (den / other.denominator)

		common_factor = Fraction.gcd(num, den)

		num //= common_factor
		den //= common_factor

		self.numerator = num
		self.denominator = den

		# not really sure why this needs to be here, but it does.
		return self

	def __sub__(self, other):

		den = Fraction.gcd(self.denominator, other.denominator)

		num = self.numerator * (den / self.denominator) - other.numerator * (den / other.denominator)

		common_factor = Fraction.gcd(num, den)

		num //= common_factor
		den //= common_factor

		return Fraction(num, den)

	# this is what's called to convert the object to a string when it's in a container like: {"key": Fraction} or [Fraction, Fraction]
	def __repr__(self):
		return self.__str__()

	# this just converts the object to a string.
	def __str__(self):
		return "%d / %d" % (self.numerator, self.denominator)

	# this is also ripped from the internet and converted to python.
	@staticmethod
	def gcd(n1 : int, n2 : int):
		if (n1 == 0):
			return n2
		return Fraction.gcd(n2%n1, n1)

	@staticmethod
	def from_float(x : float):

		d = len(str(x).split('.')[1])

		den = 10 ** d
		num = x * den

		factor = Fraction.gcd(num, den)

		den //= factor
		num //= factor

		return Fraction(num, den)

	def number(self) -> float:
		return self.numerator / self.denominator
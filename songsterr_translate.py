from abstract import *
from json import load

# just found out there's a standard for midi drum types
# I'm simplifying it a bit, also Songsterr's is a bit different than the standard.. maybe?
songster_to_me_map = {
	46: DrumType.OpenHiHat,
	92: DrumType.HalfHiHat,
	42: DrumType.ClosedHiHat,
	49: DrumType.HighCrash,
	57: DrumType.MediumCrash,
	51: DrumType.Ride,
	53: DrumType.RideBell,
	38: DrumType.Snare,
	40: DrumType.ElectricSnare,
	50: DrumType.HighTom,
	48: DrumType.MidTom,
	47: DrumType.LowMidTom,
	45: DrumType.LowTom,
	43: DrumType.HighFloorTom,
	41: DrumType.FloorTom,
	36: DrumType.Kick,
	37: DrumType.SideStickSnare
	# 38: DrumType.HiHatControl
}

# is this legal?
def translate_songsterr_data(filepath : str) -> list[list[dict]]:

	with open(filepath, "r") as f:
		data = load(f)

	translation = []

	for measure in data["measures"]:

		measure_translation = []

		for beat in measure["voices"][0]["beats"]:

			beat_translation = {
				"duration": Fraction(beat["duration"][0], beat["duration"][1]),
				"notes": []
			}

			if "beamStop" in beat:
				beat_translation["beamStop"] = True

			if "beamStart" in beat:
				beat_translation["beamStart"] = True

			for note in beat["notes"]:

				if "rest" in note:
					beat_translation["notes"].append(DrumType.Rest)
					continue

				beat_translation["notes"].append(songster_to_me_map[note["fret"]])

			measure_translation.append(beat_translation)

		translation.append(measure_translation)

	return translation
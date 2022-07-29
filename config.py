# General configuration for the Synthesizer

debug = False
prove = False
depth_for_observational_equivalence = 5


def set_debug(value):
    global debug
    debug = value


def set_prove(value):
    global prove
    prove = value


def set_depth_for_observational_equivalence(value):
    global depth_for_observational_equivalence
    depth_for_observational_equivalence = value

import obspython as obs
from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library

DEBUG = False
DEBUG_AUDIO = False


# Classes
class Source(Structure):
    pass

class Volmeter(Structure):
    pass

class PNGTuber:
    isIdle = True
    isTalking = False
    isYelling = False

    def __init__(self, source, talk_image, talk_threshold, yell_image, yell_threshold, hold_yell):
        self.source = source
        self.settings = obs.obs_source_get_settings(source)

        self.idle_image = obs.obs_data_get_string(self.settings, "file")
        self.talking_image = talk_image
        self.talking_threshold = talk_threshold
        self.yelling_image = yell_image
        self.yelling_threshold = yell_threshold
        self.hold_yell = hold_yell

    def idle(self):
        if self.isIdle:
            return
        
        if DEBUG: print("Idle")
        self.isIdle = True
        self.isTalking = False
        self.isYelling = False
        obs.obs_data_set_string(self.settings, "file", self.idle_image)
        obs.obs_source_update(self.source, self.settings);

    def talking(self):
        if self.hold_yell and self.isYelling:
            self.yelling()
            return 
        
        if self.isTalking:
            return
        
        if DEBUG: print("Talking")
        self.isIdle = False
        self.isTalking = True
        self.isYelling = False
        obs.obs_data_set_string(self.settings, "file", self.talking_image)
        obs.obs_source_update(self.source, self.settings);
    
    def yelling(self):
        if self.isYelling:
            return
        
        if DEBUG: print("Yelling")
        self.isIdle = False
        self.isTalking = False
        self.isYelling = True
        obs.obs_data_set_string(self.settings, "file", self.yelling_image)
        obs.obs_source_update(self.source, self.settings);


    def update(self, volume):
        if   (volume > self.yelling_threshold): self.yelling()
        elif (volume > self.talking_threshold): self.talking()
        else: self.idle()

    def release(self):
        self.idle()
        obs.obs_data_release(self.settings)
        obs.obs_source_release(self.source)


# Audio Device Wrapper
obsffi = CDLL("obs")
G = SimpleNamespace()

def wrap(funcname, restype, argtypes):
    """Simplify wrapping ctypes functions in obsffi"""
    func = getattr(obsffi, funcname)
    func.restype = restype
    func.argtypes = argtypes
    globals()["g_" + funcname] = func

volmeter_callback_t = CFUNCTYPE(None, c_void_p, POINTER(c_float), POINTER(c_float), POINTER(c_float))
wrap("obs_get_source_by_name", POINTER(Source), argtypes=[c_char_p])
wrap("obs_source_release", None, argtypes=[POINTER(Source)])
wrap("obs_volmeter_create", POINTER(Volmeter), argtypes=[c_int])
wrap("obs_volmeter_destroy", None, argtypes=[POINTER(Volmeter)])
wrap("obs_volmeter_add_callback", None, argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p])
wrap("obs_volmeter_remove_callback", None, argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p])
wrap("obs_volmeter_attach_source", c_bool, argtypes=[POINTER(Volmeter), POINTER(Source)])

@volmeter_callback_t
def volmeter_callback(data, mag, peak, input):
    G.noise = float(peak[0])

def remove_volmeter():
    g_obs_volmeter_remove_callback(G.volmeter, volmeter_callback, None)
    g_obs_volmeter_destroy(G.volmeter)
    G.lock = False

def write_volume(volume):
    global audio_volume
    if DEBUG_AUDIO: print(volume)
    audio_volume = volume

OBS_FADER_LOG = 2
G.lock = False
G.noise = 999
G.tick = 16
G.tick_mili = G.tick * 0.001
G.interval_sec = 0.05
G.tick_acc = 0
G.source_name = "Media Source"
G.volmeter = "not yet initialized volmeter instance"
G.callback = write_volume

def poll_audio():
    if not G.lock:
        source = g_obs_get_source_by_name(G.source_name.encode("utf-8"))
        G.volmeter = g_obs_volmeter_create(OBS_FADER_LOG)
        g_obs_volmeter_add_callback(G.volmeter, volmeter_callback, None)
        if g_obs_volmeter_attach_source(G.volmeter, source):
            g_obs_source_release(source)
            G.lock = True
            return
        
    G.tick_acc += G.tick_mili
    if G.tick_acc > G.interval_sec:
        G.callback(G.noise)
        G.tick_acc = 0


# Global Parameters
audio_volume = -999.999
audio_source = None
pngtuber = None

# Description displayed in the Scripts dialog window
def script_description():
  return \
"""
PNGTuber State Machine
    by @Acerola_t

Change your PNGTuber source based on up to two sound gates.
"""

# Set Default Values
def script_defaults(settings):
    obs.obs_data_set_default_double(settings, "poll rate", 0.03)


# UI
def script_properties():
    properties = obs.obs_properties_create()

    audio_sources_list = obs.obs_properties_add_list(
        properties,
        "audio source",
        "Audio Source:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id == "wasapi_input_capture":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(audio_sources_list, name, name)

    poll = obs.obs_properties_add_float(properties, "poll rate", "Poll Rate:", 0.01, 0.1, 0.01)
    obs.obs_property_set_long_description(poll, "How often to sample the audio level (in seconds). Lower number will mean more accurate audio data but potentially worse performance.")

    png_sources_list = obs.obs_properties_add_list(
        properties,
        "png source",
        "PNG Source:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)

            if source_id == "image_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(png_sources_list, name, name)
        
        obs.source_list_release(sources)

    obs.obs_properties_add_float_slider(properties, "talking threshold", "Talking Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "talking image path", "Talking Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    ygate = obs.obs_properties_add_bool(properties, "use yell gate", "Use Yell Gate?")
    obs.obs_property_set_long_description(ygate, "Use this gate to transition to a different sprite when input volume exceeds the following threshold")

    obs.obs_properties_add_float_slider(properties, "yelling threshold", "Yelling Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "yelling image path", "Yelling Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    hold_yell_b = obs.obs_properties_add_bool(properties, "hold yell", "Hold Yell?")
    obs.obs_property_set_long_description(hold_yell_b, "Usually you'll only be above the yell threshold for a brief period, enable this if you want to keep the yelling sprite regardless of future audio levels until you stop talking.")

    if DEBUG:
        obs.obs_properties_add_button(properties, "debug button", "Debug", debug)

    return properties


# Cache GUI Parameters
def script_update(settings):
    global pngtuber, audio_source

    if G.lock:
        remove_volmeter()

    if pngtuber is not None:
        pngtuber.release()

    G.source_name = obs.obs_data_get_string(settings, "audio source")

    if G.source_name is None:
        print("Please select an audio source to control your PNGTuber.")
        return

    G.interval_sec = obs.obs_data_get_double(settings, "poll rate")

    audio_source = obs.obs_get_source_by_name(G.source_name)

    pngtuber_source = obs.obs_data_get_string(settings, "png source")
    talking_image_path = obs.obs_data_get_string(settings, "talking image path")
    talking_threshold = obs.obs_data_get_double(settings, "talking threshold")
    use_yelling = obs.obs_data_get_bool(settings, "use yell gate")
    yelling_image_path = obs.obs_data_get_string(settings, "yelling image path") if use_yelling else talking_image_path
    yelling_threshold = obs.obs_data_get_double(settings, "yelling threshold")
    hold_yelling = obs.obs_data_get_bool(settings, "hold yell")

    if pngtuber_source is None:
        print("Please select your PNGTuber source.")
        return
    
    if talking_image_path == "":
        print("Please select an image for talking.")
        return
    
    if use_yelling and yelling_image_path == "":
        print("Please select an image for talking.")
        return
    
    pngtuber = PNGTuber(obs.obs_get_source_by_name(pngtuber_source), talking_image_path, talking_threshold, yelling_image_path, yelling_threshold, hold_yelling)


# Update (Called once per frame)
def script_tick(seconds):
    if audio_source is not None:
        if obs.obs_source_muted(audio_source):
            if pngtuber is not None: pngtuber.idle()
            return

    if G.source_name is not None:
        poll_audio()
    
    if pngtuber is not None:
        pngtuber.update(audio_volume)


# Release memory
def script_unload():
    if G.lock:
        remove_volmeter()
    
    if pngtuber is not None:
        pngtuber.release()

    if audio_source is not None:
        obs.obs_source_release(audio_source)


def debug(props, prop):
    print("Debug")
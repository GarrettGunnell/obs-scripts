import obspython as obs
from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library


# Classes
class Source(Structure):
    pass

class Volmeter(Structure):
    pass

class PNGTuber:
    isIdle = True
    isTalking = False

    def __init__(self, source, talk_image, talk_threshold):
        self.source = source
        self.settings = obs.obs_source_get_settings(source)

        self.idle_image = obs.obs_data_get_string(self.settings, "file")
        self.talking_image = talk_image
        self.talking_threshold = talk_threshold

    def idle(self):
        if self.isIdle:
            return
        
        self.isIdle = True
        self.isTalking = False
        obs.obs_data_set_string(self.settings, "file", self.idle_image)
        obs.obs_source_update(self.source, self.settings);

    def talking(self):
        if self.isTalking:
            return
        
        self.isIdle = False
        self.isTalking = True
        obs.obs_data_set_string(self.settings, "file", self.talking_image)
        obs.obs_source_update(self.source, self.settings);

    def update(self, volume):
        if (volume > self.talking_threshold):
            self.talking()
        else:
            self.idle()

    def release(self):
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
DEBUG = False

# Description displayed in the Scripts dialog window
def script_description():
  return \
"""
PNGTuber Animator
    by @Acerola_t

Change your PNGTuber source based on any number of sound gates.
"""

# Set Default Values
def script_defaults(settings):
    pass


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

    if DEBUG:
        obs.obs_properties_add_button(properties, "talking button", "Debug", debug)

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

    audio_source = obs.obs_get_source_by_name(G.source_name)

    pngtuber_source = obs.obs_data_get_string(settings, "png source")
    talking_image_path = obs.obs_data_get_string(settings, "talking image path")
    audio_threshold = obs.obs_data_get_double(settings, "talking threshold")

    if pngtuber_source is None:
        print("Please select your PNGTuber source.")
        return
    
    if talking_image_path == "":
        print("Please select an image for talking.")
        return
    
    pngtuber = PNGTuber(obs.obs_get_source_by_name(pngtuber_source),talking_image_path, audio_threshold)


# Update (Called once per frame)
def script_tick(seconds):
    if audio_source is not None:
        if obs.obs_source_muted(audio_source):
            return

    if G.source_name is not None:
        poll_audio()
    
    if pngtuber is not None:
        pngtuber.update(audio_volume)



def script_unload():
    if G.lock:
        remove_volmeter()
    
    if pngtuber is not None:
        pngtuber.release()

    if audio_source is not None:
        obs.obs_source_release(audio_source)
    


# Debug Button
def idle(props, prop):
    if not pngtuber_source:
        print("Select your PNGTuber source")

    source = obs.obs_get_source_by_name(pngtuber_source)
    settings = obs.obs_source_get_settings(source)
    obs.obs_data_set_string(settings, "file", idle_image_path)
    obs.obs_source_update(source, settings);

    obs.obs_data_release(settings)
    obs.obs_source_release(source)


def debug(props, prop):
    print("Debug")
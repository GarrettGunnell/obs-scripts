import math
import time
import obspython as obs
from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library

DEBUG = False
DEBUG_AUDIO = False

WINDOW_WIDTH = 0
WINDOW_HEIGHT = 0


# Classes
class Source(Structure):
    pass

class Volmeter(Structure):
    pass

class PNGTuber:
    origin = obs.vec2()
    sceneitem = None
    is_paused = False
    is_idle = False
    is_talking = False
    is_yelling = False
    tick_acc = 0.0

    def __init__(self, source, talk_image, talk_threshold, yell_image, yell_threshold, hold_yell, idle_delay, origin, sceneitem):
        self.source = source
        self.settings = obs.obs_source_get_settings(source)

        self.idle_image = obs.obs_data_get_string(self.settings, "file")
        self.talking_image = talk_image
        self.talking_threshold = talk_threshold
        self.yelling_image = yell_image
        self.yelling_threshold = yell_threshold
        self.hold_yell = hold_yell
        self.idle_delay = idle_delay
        self.origin = origin
        self.sceneitem = sceneitem

    def idle(self):
        if self.is_idle or self.is_paused:
            return
        
        if DEBUG: print("Idle")
        self.is_idle = True
        self.is_talking = False
        self.is_yelling = False
        obs.obs_data_set_string(self.settings, "file", self.idle_image)
        obs.obs_source_update(self.source, self.settings);

    def talking(self):
        if self.is_paused: return

        self.tick_acc = 0.0
        if self.hold_yell and self.is_yelling:
            self.yelling()
            return 
        
        if self.is_talking:
            return
        
        if DEBUG: print("Talking")
        self.is_idle = False
        self.is_talking = True
        self.is_yelling = False
        obs.obs_data_set_string(self.settings, "file", self.talking_image)
        obs.obs_source_update(self.source, self.settings);
    
    def yelling(self):
        if self.is_paused: return
        
        self.tick_acc = 0.0
        if self.is_yelling:
            return
        
        if DEBUG: print("Yelling")
        self.is_idle = False
        self.is_talking = False
        self.is_yelling = True
        obs.obs_data_set_string(self.settings, "file", self.yelling_image)
        obs.obs_source_update(self.source, self.settings);


    def update(self, volume):
        if self.is_paused: return
        
        if   (volume > self.yelling_threshold): self.yelling()
        elif (volume > self.talking_threshold): self.talking()
        else: 
            self.tick_acc += 0.016
            if self.tick_acc > self.idle_delay:
                self.tick_acc = 0.0
                self.idle()

        offset = obs.vec2()
        
        t = time.time() * math.pi * idle_animation_frequency

        ''' up and down bounce animation
        offset.x = 0
        offset.y = abs(math.cos(t) * idle_animation_amplitude)
        '''

        #offset.x = (math.sin(t) * idle_animation_amplitude)
        #offset.y = abs(math.cos(t) * idle_animation_amplitude)

        offset.x = 0
        offset.y = 0

        g = 0.5
        f = idle_animation_frequency
        a = idle_animation_amplitude
        for i in range(0, 3):
            v = math.cos(time.time() * f + i * 0.35) * a
            offset.x += v
            f *= 2
            a *= g

        g = 0.5
        f = idle_animation_frequency
        a = idle_animation_amplitude
        for i in range(0, 3):
            v = math.sin(time.time() * f + i * 0.35) * a
            offset.y += v
            f *= 2
            a *= g

        new_position = obs.vec2()
        new_position.x = self.origin.x - offset.x
        new_position.y = self.origin.y - offset.y
        obs.obs_sceneitem_set_pos(self.sceneitem, new_position)

    def pause(self):
        self.is_paused = True
        self.tick_acc = 0.0
        self.idle()
    
    def play(self):
        self.is_paused = False

    def paused(self):
        return self.is_paused

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
    audio_volume = volume
    if audio_volume == 999: audio_volume = -999
    if DEBUG_AUDIO: print(audio_volume)

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
cached_scene_source = None
cached_sceneitem = None
cached_origin = obs.vec2()
cached_origin.x = 0
cached_origin.y = 0
idle_animation_amplitude = 0.0
idle_animation_frequency = 0.0


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
    obs.obs_data_set_default_double(settings, "poll rate", 0.02)
    obs.obs_data_set_default_double(settings, "talking threshold", -14.0)
    obs.obs_data_set_default_double(settings, "yelling threshold", -8.0)


# Callbacks
def stop_pngtuber(x, y):
    global pngtuber, cached_origin, cached_sceneitem
    
    if pngtuber is not None: 
        pngtuber.pause()
    
    if cached_sceneitem is not None: 
        obs.obs_sceneitem_set_pos(cached_sceneitem, cached_origin)

def play_pngtuber(x, y):
    global pngtuber
    if pngtuber is not None: pngtuber.play()
    if cached_sceneitem is not None:
        obs.obs_sceneitem_get_pos(cached_sceneitem, cached_origin)

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
            if source_id == "wasapi_input_capture" or source_id == "wasapi_output_capture":
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

    delay = obs.obs_properties_add_float(properties, "idle delay", "Idle Delay:", 0.0, 1.0, 0.01)
    obs.obs_property_set_long_description(delay, "How long to wait (in seconds) before returning idle after talking.")

    idle_motion_list = obs.obs_properties_add_list(
        properties,
        "idle motion",
        "Idle Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    animations_list = ["None", "Shake", "Vertical Bounce", "Horizontal Bounce", "Roll"]
    for item in animations_list:
        obs.obs_property_list_add_string(idle_motion_list, item, item)

    obs.obs_properties_add_float_slider(properties, "idle animation amplitude", "Animation Strength", 0.0, 100.0, 0.01)
    obs.obs_properties_add_float_slider(properties, "idle animation frequency", "Animation Speed", 0.0, 10.0, 0.01)


    obs.obs_properties_add_float_slider(properties, "talking threshold", "Talking Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "talking image path", "Talking Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    talk_motion_list = obs.obs_properties_add_list(
        properties,
        "talk motion",
        "Talk Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    
    for item in animations_list:
        obs.obs_property_list_add_string(talk_motion_list, item, item)

    ygate = obs.obs_properties_add_bool(properties, "use yell gate", "Use Yell Gate?")
    obs.obs_property_set_long_description(ygate, "Use this gate to transition to a different sprite when input volume exceeds the following threshold")

    obs.obs_properties_add_float_slider(properties, "yelling threshold", "Yelling Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "yelling image path", "Yelling Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    yell_motion_list = obs.obs_properties_add_list(
        properties,
        "yell motion",
        "Yell Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    
    for item in animations_list:
        obs.obs_property_list_add_string(yell_motion_list, item, item)

    hold_yell_b = obs.obs_properties_add_bool(properties, "hold yell", "Hold Yell?")
    obs.obs_property_set_long_description(hold_yell_b, "Usually you'll only be above the yell threshold for a brief period, enable this if you want to keep the yelling sprite regardless of future audio levels until you stop talking.")

    obs.obs_properties_add_button(properties, "pause button", "Pause PNGTuber", stop_pngtuber)
    obs.obs_properties_add_button(properties, "play button", "Play PNGTuber", play_pngtuber)

    if DEBUG:
        obs.obs_properties_add_button(properties, "debug button", "Debug", debug)

    return properties


# Cache GUI Parameters
def script_update(settings):
    global pngtuber, audio_source, cached_scene_source, cached_sceneitem, cached_origin, idle_animation_amplitude, idle_animation_frequency

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
    idle_delay = obs.obs_data_get_double(settings, "idle delay")
    idle_animation_amplitude = obs.obs_data_get_double(settings, "idle animation amplitude") * 10
    idle_animation_frequency = obs.obs_data_get_double(settings, "idle animation frequency")


    # Get screen dimensions
    cached_scene_source = obs.obs_frontend_get_current_scene()
    print("Active Scene:", obs.obs_source_get_name(cached_scene_source))
    scene = obs.obs_scene_from_source(cached_scene_source)
    cached_sceneitem = obs.obs_scene_find_source_recursive(scene, "Dev Image")
    if cached_sceneitem is not None:
        if cached_origin.x != 0 and cached_origin.y != 0:
            obs.obs_sceneitem_set_pos(cached_sceneitem, cached_origin)

        print("PNGTuber source found!")
        obs.obs_sceneitem_get_pos(cached_sceneitem, cached_origin)
        print("Cached PNGTuber Position:", cached_origin.x, cached_origin.y)

    if pngtuber_source is None:
        print("Please select your PNGTuber source.")
        return
    
    if talking_image_path == "":
        print("Please select an image for talking.")
        return
    
    if use_yelling and yelling_image_path == "":
        print("Please select an image for yelling.")
        return

    pngtuber = PNGTuber(obs.obs_get_source_by_name(pngtuber_source), talking_image_path, talking_threshold, yelling_image_path, yelling_threshold, hold_yelling, idle_delay, cached_origin, cached_sceneitem)


# Update (Called once per frame)
def script_tick(seconds):
    global audio_source, cached_origin, pngtuber, cached_sceneitem
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
    global pngtuber, audio_source, cached_scene_source, cached_origin, cached_sceneitem
    if G.lock:
        remove_volmeter()
    
    if pngtuber is not None:
        pngtuber.release()

    if audio_source is not None:
        obs.obs_source_release(audio_source)

    if cached_scene_source is not None:
        obs.obs_sceneitem_set_pos(cached_sceneitem, cached_origin)
        obs.obs_source_release(cached_scene_source)


def debug(props, prop):
    print("Debug")
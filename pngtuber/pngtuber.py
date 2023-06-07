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

BLEND_SPEED = 2

def lerp(a, b, t):
    return (1 - t) * a + t * b

# Classes
class Source(Structure):
    pass

class Volmeter(Structure):
    pass

class AnimationSettings:
    def __init__(self, idle_animation, idle_amplitude, idle_frequency, talk_animation, talk_amplitude, talk_frequency, yell_animation, yell_amplitude, yell_frequency, blink_timer, blink_length, easing_function, blend_speed):
        self.idle_animation = idle_animation
        self.idle_amplitude = idle_amplitude
        self.idle_frequency = idle_frequency
        self.talk_animation = talk_animation
        self.talk_amplitude = talk_amplitude
        self.talk_frequency = talk_frequency
        self.yell_animation = yell_animation
        self.yell_amplitude = yell_amplitude
        self.yell_frequency = yell_frequency
        self.blink_timer = blink_timer
        self.blink_length = blink_length
        self.easing_function = easing_function
        self.blend_speed = blend_speed

class SpriteSettings:
    def __init__(self, idle_blink_image, talk_image, talk_blink_image, yell_image, yell_blink_image):
        self.idle_blink_image = idle_blink_image
        self.talk_image = talk_image
        self.talk_blink_image = talk_blink_image
        self.yell_image = yell_image
        self.yell_blink_image = yell_blink_image

class PNGTuber:
    origin = obs.vec2()
    is_paused = False
    is_idle = False
    is_talking = False
    is_yelling = False
    tick_acc = 0.0
    previous_frame_time = time.time()
    is_blinking = False
    blink_timer = 0.0
    blinking_timer = 0.0

    def __init__(self, source_name, sprite_settings, talk_threshold, yell_threshold, hold_yell, origin, sceneitem, animation_settings):
        self.source_name = source_name
        self.source = obs.obs_get_source_by_name(source_name)
        self.settings = obs.obs_source_get_settings(self.source)

        self.idle_image = obs.obs_data_get_string(self.settings, "file")
        self.idle_blink_image = sprite_settings.idle_blink_image
        self.talking_image = sprite_settings.talk_image
        self.talking_blink_image = sprite_settings.talk_blink_image
        self.talking_threshold = talk_threshold
        self.yelling_image = sprite_settings.yell_image
        self.yelling_blink_image = sprite_settings.yell_blink_image
        self.yelling_threshold = yell_threshold
        self.hold_yell = hold_yell
        self.origin = origin
        self.sceneitem = sceneitem
        self.animation_settings = animation_settings

    def able_to_blink(self):
        if self.idle_blink_image == "" or self.talking_blink_image == "" or self.yelling_blink_image == "":
            return False
        
        return True

    def get_delta_time(self):
        return time.time() - self.previous_frame_time

    def idle(self):
        if DEBUG: print("Idle")

        if self.is_idle:
            return
        
        self.is_idle = True
        self.is_talking = False
        self.is_yelling = False
        self.set_sprite()

    def talking(self):
        if self.hold_yell and self.is_yelling:
            self.yelling()
            return 
        
        if self.tick_acc < 1:
            self.tick_acc += self.get_delta_time() * self.animation_settings.blend_speed

        if self.is_talking:
            return
        
        if DEBUG: print("Talking")
        self.is_idle = False
        self.is_talking = True
        self.is_yelling = False
        self.set_sprite()
    
    def yelling(self):
        if self.tick_acc < 1:
            self.tick_acc += self.get_delta_time() * self.animation_settings.blend_speed

        if self.is_yelling:
            return
            
        if DEBUG: print("Yelling")
        self.is_idle = False
        self.is_talking = False
        self.is_yelling = True
        self.set_sprite()

    def set_sprite(self):
        normal_sprite = ""
        if self.is_idle: normal_sprite = self.idle_image
        if self.is_talking: normal_sprite = self.talking_image
        if self.is_yelling: normal_sprite = self.yelling_image

        obs.obs_data_set_string(self.settings, "file", normal_sprite)
        obs.obs_source_update(self.source, self.settings)

    def blink(self):
        blinking_sprite = ""
        if self.is_idle: blinking_sprite = self.idle_blink_image
        if self.is_talking: blinking_sprite = self.talking_blink_image
        if self.is_yelling: blinking_sprite = self.yelling_blink_image

        obs.obs_data_set_string(self.settings, "file", blinking_sprite)
        obs.obs_source_update(self.source, self.settings)

    
    def get_animation_type(self):
        if self.is_idle: return self.animation_settings.idle_animation
        if self.is_talking: return self.animation_settings.talk_animation
        if self.is_yelling: return self.animation_settings.yell_animation

        return "None"

    def get_amplitude(self):
        if self.is_idle: return self.animation_settings.idle_amplitude
        if self.is_talking: return self.animation_settings.talk_amplitude
        if self.is_yelling: return self.animation_settings.yell_amplitude

        return 0

    def get_frequency(self):
        if self.is_idle: return self.animation_settings.idle_frequency
        if self.is_talking: return self.animation_settings.talk_frequency
        if self.is_yelling: return self.animation_settings.yell_frequency
        
        return 0

    def calculate_offset(self, animation_type, amplitude, frequency):
        offset = obs.vec2()
        offset.x = 0
        offset.y = 0

        t = time.time() * math.pi * frequency

        if animation_type == "None": return offset
        if animation_type == "Shake":
            g = 0.5
            f = frequency
            a = amplitude
            for i in range(0, 3):
                v = math.cos(time.time() * f + i * 0.35) * a
                offset.x += v
                f *= 2
                a *= g

            g = 0.5
            f = frequency
            a = amplitude
            for i in range(0, 3):
                v = math.sin(time.time() * f + i * 0.35) * a
                offset.y += v
                f *= 2
                a *= g
        if animation_type == "Vertical Bounce":
            offset.x = 0
            offset.y = abs(math.cos(t) * amplitude)
        if animation_type == "Horizontal Bounce":
            offset.x = (math.sin(t) * amplitude)
            offset.y = abs(math.cos(t) * amplitude)

        
        return offset

    def easing(self):
        x = max(0, min(1, self.tick_acc))

        match self.animation_settings.easing_function:
            case "Linear":
                return x
            case "easeInQuad":
                return x * x
            case "easeOutQuad":
                return 1 - (1 - x) * (1 - x)
            case "easeInOutQuad":
                return 2 * x * x if x < 0.5 else 1 - ((-2 * x + 2) ** 2) / 2
            case "easeInElastic":
                c4 = (2 * math.pi) / 3
                if x == 0: return 0
                if x == 1: return 1
                return -2 ** (10 * x - 10) * math.sin((x * 10 - 10.75) * c4)
            case "easeOutElastic":
                c4 = (2 * math.pi) / 3
                if x == 0: return 0
                if x == 1: return 1
                return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * c4) + 1
            case "easeInOutElastic":
                c5 = (2 * math.pi) / 4.5
                if x == 0: return 0
                if x == 1: return 1
                if x < 0.5:
                    return -(2 ** (20 * x - 10) * math.sin((20 * x - 11.125) * c5)) / 2
                return (2 ** (-20 * x + 10) * math.sin((20 * x - 11.125) * c5)) / 2 + 1
            case "easeInBounce":
                n1 = 7.5625
                d1 = 2.75
                x = 1 - x
                output = 0
                if (x < 1 / d1): output = n1 * x * x
                elif (x < 2 / d1):
                    x -= 1.5 / d1
                    output = n1 * x * x + 0.75
                elif (x < 2.5 / d1):
                    x -= 2.25 / d1
                    output = n1 * x * x + 0.9375
                else:
                    x -= 2.625 / d1
                    output = n1 * x * x + 0.984375

                return 1 - output

            
        return x

    def update(self, volume):
        if self.is_paused or self.sceneitem is None: return
        
        # Update sprite
        if self.able_to_blink():
            if self.is_blinking:
                self.blinking_timer += self.get_delta_time()
                if self.blinking_timer > self.animation_settings.blink_length:
                    self.blinking_timer = 0
                    self.blink_timer = 0
                    self.is_blinking = False
                    self.set_sprite()
            else:
                self.blink_timer += self.get_delta_time()
                if self.blink_timer > self.animation_settings.blink_timer:
                    self.blinking_timer = 0
                    self.blink_timer = 0
                    self.is_blinking = True
                    self.blink()


        if   (volume > self.yelling_threshold): self.yelling()
        elif (volume > self.talking_threshold): self.talking()
        else: 
            if self.tick_acc > 0:
                self.tick_acc -= self.get_delta_time() * self.animation_settings.blend_speed
                
            if self.tick_acc < 0.2:
                self.idle()

        self.previous_frame_time = time.time()

        talking_offset = talking_offset = self.calculate_offset(self.animation_settings.talk_animation, self.animation_settings.talk_amplitude, self.animation_settings.talk_frequency)
        if self.is_yelling and self.talking_image != self.yelling_image:
            talking_offset = self.calculate_offset(self.animation_settings.yell_animation, self.animation_settings.yell_amplitude, self.animation_settings.yell_frequency)
        idle_offset = self.calculate_offset(self.animation_settings.idle_animation, self.animation_settings.idle_amplitude, self.animation_settings.idle_frequency)
        
        idle_position = obs.vec2()
        idle_position.x = self.origin.x - idle_offset.x
        idle_position.y = self.origin.y - idle_offset.y

        talking_position = obs.vec2()
        talking_position.x = self.origin.x - talking_offset.x
        talking_position.y = self.origin.y - talking_offset.y

        new_position = obs.vec2()
        new_position.x = lerp(idle_position.x, talking_position.x, self.easing())
        new_position.y = lerp(idle_position.y, talking_position.y, self.easing())
        obs.obs_sceneitem_set_pos(self.sceneitem, new_position)

    def pause(self):
        self.is_paused = True
        self.tick_acc = 0.0
        self.idle()
    
    def play(self):
        self.is_paused = False

    def paused(self):
        return self.is_paused
    
    def update_sceneitem(self, sceneitem):
        obs.obs_sceneitem_set_pos(self.sceneitem, self.origin)
        self.sceneitem = sceneitem
        obs.obs_sceneitem_get_pos(self.sceneitem, self.origin)

    def release(self):
        self.is_blinking = False
        self.idle()
        self.set_sprite()
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
    obs.obs_data_set_default_double(settings, "blink timer", 5.0)
    obs.obs_data_set_default_double(settings, "blink length", 0.33)
    obs.obs_data_set_default_double(settings, "idle amplitude", 1.0)
    obs.obs_data_set_default_double(settings, "idle frequency", 1.0)
    obs.obs_data_set_default_double(settings, "talk amplitude", 1.0)
    obs.obs_data_set_default_double(settings, "talk frequency", 1.0)
    obs.obs_data_set_default_double(settings, "yell amplitude", 1.0)
    obs.obs_data_set_default_double(settings, "yell frequency", 1.0)
    obs.obs_data_set_default_double(settings, "blend speed", 1.0)


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

    obs.obs_properties_add_path(properties, "idle blink image path", "Idle Blink Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    idle_motion_list = obs.obs_properties_add_list(
        properties,
        "idle animation",
        "Idle Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    animations_list = ["None", "Shake", "Vertical Bounce", "Horizontal Bounce"]
    for item in animations_list:
        obs.obs_property_list_add_string(idle_motion_list, item, item)

    obs.obs_properties_add_float_slider(properties, "idle amplitude", "Animation Strength", 0.0, 100.0, 0.01)
    obs.obs_properties_add_float_slider(properties, "idle frequency", "Animation Speed", 0.0, 10.0, 0.01)

    obs.obs_properties_add_float_slider(properties, "talking threshold", "Talking Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "talking image path", "Talking Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")
    obs.obs_properties_add_path(properties, "talking blink image path", "Talking Blink Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    talk_motion_list = obs.obs_properties_add_list(
        properties,
        "talk animation",
        "Talk Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    
    for item in animations_list:
        obs.obs_property_list_add_string(talk_motion_list, item, item)
    
    obs.obs_properties_add_float_slider(properties, "talk amplitude", "Animation Strength", 0.0, 100.0, 0.01)
    obs.obs_properties_add_float_slider(properties, "talk frequency", "Animation Speed", 0.0, 10.0, 0.01)

    ygate = obs.obs_properties_add_bool(properties, "use yell gate", "Use Yell Gate?")
    obs.obs_property_set_long_description(ygate, "Use this gate to transition to a different sprite when input volume exceeds the following threshold")

    obs.obs_properties_add_float_slider(properties, "yelling threshold", "Yelling Threshold", -60.0, 0.0, 0.01)

    obs.obs_properties_add_path(properties, "yelling image path", "Yelling Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")
    obs.obs_properties_add_path(properties, "yelling blink image path", "Yelling Blink Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    yell_motion_list = obs.obs_properties_add_list(
        properties,
        "yell animation",
        "Yell Motion:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    
    for item in animations_list:
        obs.obs_property_list_add_string(yell_motion_list, item, item)

    obs.obs_properties_add_float_slider(properties, "yell amplitude", "Animation Strength", 0.0, 100.0, 0.01)
    obs.obs_properties_add_float_slider(properties, "yell frequency", "Animation Speed", 0.0, 10.0, 0.01)

    hold_yell_b = obs.obs_properties_add_bool(properties, "hold yell", "Hold Yell?")
    obs.obs_property_set_long_description(hold_yell_b, "Usually you'll only be above the yell threshold for a brief period, enable this if you want to keep the yelling sprite regardless of future audio levels until you stop talking.")

    blink_timer = obs.obs_properties_add_float_slider(properties, "blink timer", "Blink Timer", 0.01, 10, 0.01)
    obs.obs_property_set_long_description(blink_timer, "The average time between blinks for a human adult is 5 seconds.")

    blink_length = obs.obs_properties_add_float_slider(properties, "blink length", "Blink Length", 0.01, 1, 0.01)
    obs.obs_property_set_long_description(blink_length, "The average time it takes for a human adult to complete a blink is 0.3 seconds.")

    easing_function_list = obs.obs_properties_add_list(
        properties,
        "easing function",
        "Easing Function:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    easing_functions_list = ["Linear", "easeInQuad", "easeOutQuad", "easeInOutQuad", "easeInElastic", "easeOutElastic", "easeInOutElastic", "easeInBounce"]
    for item in easing_functions_list:
        obs.obs_property_list_add_string(easing_function_list, item, item)

    blend_speed = obs.obs_properties_add_float_slider(properties, "blend speed", "Blend Speed", 0.01, 3, 0.01)
    obs.obs_property_set_long_description(blend_speed, "How quickly to transition between animation states.")

    obs.obs_properties_add_button(properties, "pause button", "Pause PNGTuber", stop_pngtuber)
    obs.obs_properties_add_button(properties, "play button", "Play PNGTuber", play_pngtuber)

    if DEBUG:
        obs.obs_properties_add_button(properties, "debug button", "Debug", debug)

    return properties


# Cache GUI Parameters
def script_update(settings):
    global pngtuber, audio_source, cached_scene_source, cached_sceneitem, cached_origin

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
    idle_blink_image_path = obs.obs_data_get_string(settings, "idle blink image path")
    talking_image_path = obs.obs_data_get_string(settings, "talking image path")
    talking_blink_image_path = obs.obs_data_get_string(settings, "talking blink image path")
    talking_threshold = obs.obs_data_get_double(settings, "talking threshold")
    use_yelling = obs.obs_data_get_bool(settings, "use yell gate")
    yelling_image_path = obs.obs_data_get_string(settings, "yelling image path") if use_yelling else talking_image_path
    yelling_blink_image_path = obs.obs_data_get_string(settings, "yelling blink image path") if use_yelling else talking_blink_image_path
    yelling_threshold = obs.obs_data_get_double(settings, "yelling threshold")
    hold_yelling = obs.obs_data_get_bool(settings, "hold yell")
    idle_animation = obs.obs_data_get_string(settings, "idle animation")
    idle_amplitude = obs.obs_data_get_double(settings, "idle amplitude") * 10
    idle_frequency = obs.obs_data_get_double(settings, "idle frequency")
    talk_animation = obs.obs_data_get_string(settings, "talk animation")
    talk_amplitude = obs.obs_data_get_double(settings, "talk amplitude") * 10
    talk_frequency = obs.obs_data_get_double(settings, "talk frequency")
    yell_animation = obs.obs_data_get_string(settings, "yell animation")
    yell_amplitude = obs.obs_data_get_double(settings, "yell amplitude") * 10
    yell_frequency = obs.obs_data_get_double(settings, "yell frequency")
    blink_timer = obs.obs_data_get_double(settings, "blink timer")
    blink_length = obs.obs_data_get_double(settings, "blink length")
    easing_function = obs.obs_data_get_string(settings, "easing function")
    blend_speed = obs.obs_data_get_double(settings, "blend speed")

    animation_settings = AnimationSettings(idle_animation, idle_amplitude, idle_frequency, talk_animation, talk_amplitude, talk_frequency, yell_animation, yell_amplitude, yell_frequency, blink_timer, blink_length, easing_function, blend_speed)
    sprite_settings = SpriteSettings(idle_blink_image_path, talking_image_path, talking_blink_image_path, yelling_image_path, yelling_blink_image_path)

    # Get screen dimensions
    cached_scene_source = obs.obs_frontend_get_current_scene()
    scene = obs.obs_scene_from_source(cached_scene_source)
    cached_sceneitem = obs.obs_scene_find_source_recursive(scene, pngtuber_source)
    if cached_sceneitem is not None:
        if cached_origin.x != 0 and cached_origin.y != 0:
            obs.obs_sceneitem_set_pos(cached_sceneitem, cached_origin)

        obs.obs_sceneitem_get_pos(cached_sceneitem, cached_origin)

    if pngtuber_source is None:
        print("Please select your PNGTuber source.")
        return
    
    if talking_image_path == "":
        print("Please select an image for talking.")
        return
    
    if use_yelling and yelling_image_path == "":
        print("Please select an image for yelling.")
        return

    pngtuber = PNGTuber(pngtuber_source, sprite_settings, talking_threshold, yelling_threshold, hold_yelling, cached_origin, cached_sceneitem, animation_settings)


# Update (Called once per frame)
def script_tick(seconds):
    global audio_source, cached_origin, pngtuber, cached_sceneitem, cached_scene_source
    if audio_source is not None:
        if obs.obs_source_muted(audio_source):
            if pngtuber is not None: pngtuber.update(-99999)
            return

    if G.source_name is not None:
        poll_audio()

    # Handle scene changes
    active_scene_source = obs.obs_frontend_get_current_scene()
    cached_scene_name = obs.obs_source_get_name(cached_scene_source)
    active_scene_name = obs.obs_source_get_name(active_scene_source)

    if cached_scene_name != active_scene_name:
        obs.obs_source_release(cached_scene_source)
        cached_scene_source = active_scene_source
        cached_sceneitem = None
        if pngtuber is not None: pngtuber.pause()
    else:
        obs.obs_source_release(active_scene_source)

    # Inject into detected scene item
    if cached_sceneitem is None:
        scene = obs.obs_scene_from_source(cached_scene_source)
        cached_sceneitem = obs.obs_scene_find_source_recursive(scene, pngtuber.source_name)
        if cached_sceneitem is not None:
            pngtuber.update_sceneitem(cached_sceneitem)
            pngtuber.play()

    
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
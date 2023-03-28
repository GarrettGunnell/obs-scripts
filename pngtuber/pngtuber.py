import obspython as obs

# Parameters
pngtuber_source = None
idle_image_path = None
talking_image_path = None

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

    p = obs.obs_properties_add_list(
        properties,
        "png source",
        "PNG Source:",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)

            if source_id == "image_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)
        
        obs.source_list_release(sources)

    obs.obs_properties_add_path(properties, "idle image path", "Idle Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    obs.obs_properties_add_button(properties, "idle button", "Idle", idle)

    obs.obs_properties_add_path(properties, "talking image path", "Talking Image Path:", obs.OBS_PATH_FILE, "All formats (*.bmp *.tga *.png *.jpeg *.jpg *.jxr *.gif *.psd *.webp);; BMP Files (*.bmp);; Targa Files (*.tga);; PNG Files (*.png);; JPEG Files (*.jpeg, *.jpg);; JXR Files (*.jxr);; GIF Files (*.gif);; PSD Files (*.psd);; WebP Files (*.webp);; All Files (*.*)", "C:/Pictures/")

    obs.obs_properties_add_button(properties, "talking button", "Talk", talk)

    return properties


# Cache GUI Parameters
def script_update(settings):
    global pngtuber_source, idle_image_path, talking_image_path

    pngtuber_source = obs.obs_data_get_string(settings, "png source")
    idle_image_path = obs.obs_data_get_string(settings, "idle image path")
    talking_image_path = obs.obs_data_get_string(settings, "talking image path")


# Update (Called once per frame)
def script_tick(seconds):
    pass


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


def talk(props, prop):
    if not pngtuber_source:
        print("Select your PNGTuber source")

    source = obs.obs_get_source_by_name(pngtuber_source)
    settings = obs.obs_source_get_settings(source)
    obs.obs_data_set_string(settings, "file", talking_image_path)
    obs.obs_source_update(source, settings);
    print(talking_image_path)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)
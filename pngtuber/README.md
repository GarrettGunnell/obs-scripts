# PNGTuber State Machine

This script lets you swap between 3 different sprites depending on your input mic volume to give the illusion of animated speech.

The script maintains three states: idle, talking, and shouting. You can have one sprite for each of these states.

## Options

To make the most of your state machine please refer to these explanations of the options!

`Audio Source:` This is the source of your microphone or other audio input device, labeled `Mic/Aux` by default.

`Poll Rate:` This script checks the current mic volume every few moments based on this option, every time it checks it updates how loud you are. Fast poll rates (like 0.01) will give you very accurate volume data with very little lag but may slow down your computer if you have a really bad pc. I recommend a `Poll Rate` of `0.2`.

`PNG Source:` This is the OBS source of your PNGTuber. The image you have attached to this source will be considered the `Idle` pose when you aren't speaking.

`Idle Blink Image Path:` If you want to enable blinking on your PNGTuber, put a blink image here for when you're idle. Please be mindful that blinking will only work when every other blink image field is also filled in.

`Idle Motion:` This is the idle animation, you can choose between the three described below:
* `Shake:` Slightly random motion that can be sped up to a frantic shake or slowed down to a slight float.
* `Vertical Bounce:` An up and down bounce.
* `Horizontal Bounce:` A bounce that arcs left and right.

`Animation Strength:` The amplitude of the animation, or how far it travels.

`Animation Speed:` The frequency of the animation, or how fast it travels.

`Talking Threshold:` This is the audio threshold needed to transition to the `Talking` state, the units are in `dB` just like the OBS audio mixer.

`Talking Image Path:` This is the filepath to the image you want to swap to when in the `Talking` state.

`Talking Blink Image Path:` If you want to enable blinking on your PNGTuber, put a blink image here for when you're talking. Please be mindful that blinking will only work when every other blink image field is also filled in.

`Talk Motion:` Same as `Idle Motion` but for when you're talking.

`Use Yell Gate?:` You can disable this 2nd sound gate if you do not want to use it.

`Yelling Threshold:` This is the audio threshold needed to transition to the `Yelling` state, the units are in `dB` just like the OBS audio mixer. This value should probably be higher than the `Talking Threshold`.

`Yelling Image Path`: This is the filepath to the image you want to swap to when in the `Yelling` state.

`Yelling Blink Image Path:` If you want to enable blinking on your PNGTuber, put a blink image here for when you're yelling. Please be mindful that blinking will only work when every other blink image field is also filled in.

`Hold Yell?:` Enabling this makes it so that your PNGTuber will stay in the yelling sprite until you return to idle. Since usually you aren't above the yelling threshold for more than a little bit, if you want to capture genuine anger such as a rant following a very brief loud noise then this setting will keep that emotion for your quiter rant.

`Blink Timer:` If you have enabled blinking, then this is the time inbetween blinks. The average human blinks every 5 seconds.

`Blink Length:` If you have enabled blinking, then this is the time the blink sprite is held down before opening your eyes. The average human takes 0.33 seconds to blink.

`Easing Function:` This describes how you blend between idle and talking animations. For a reference of what each easing function looks like please visit [this](https://easings.net/) website. The names match the website.

`Blend Speed:` This is how fast you blend from idle to talking, a `1` means one second, a `2` means 0.5 seconds.

`Pause PNGTuber:` Due to OBS API limitations, the animation logic is pretty janked. In order to move your scene item around without the script preventing it, you have to press this button to stop the animation.

`Play PNGTuber:` Once you have moved your scene item to where you want, press this button to resume the pngtuber animations.

## Feature Request

Have a feature you would like added? [Let me know](https://twitter.com/Acerola_t) and if I think it's neat I'll try to add it!
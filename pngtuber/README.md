# PNGTuber State Machine

This script lets you swap between 3 different sprites depending on your input mic volume to give the illusion of animated speech.

The script maintains three states: idle, talking, and shouting. You can have one sprite for each of these states.

## Options

To make the most of your state machine please refer to these explanations of the options!

`Audio Source:` This is the source of your microphone or other audio input device, labeled `Mic/Aux` by default.

`Poll Rate:` This script checks the current mic volume every few moments based on this option, every time it checks it updates how loud you are. Fast poll rates (like 0.01) will give you very accurate volume data with very little lag but may slow down your computer if you have a really bad pc. I recommend a `Poll Rate` of `0.2`.

`PNG Source:` This is the OBS source of your PNGTuber. The image you have attached to this source will be considered the `Idle` pose when you aren't speaking.

`Idle Delay:` This option will change how long it takes after you stop speaking for your PNGTuber to return to the idle state. If you speak at all this value resets, so tiny pauses in your speech won't automatically set you to idle.

`Talking Threshold:` This is the audio threshold needed to transition to the `Talking` state, the units are in `dB` just like the OBS audio mixer.

`Talking Image Path:` This is the filepath to the image you want to swap to when in the `Talking` state.

`Use Yell Gate?:` You can disable this 2nd sound gate if you do not want to use it.

`Yelling Threshold:` This is the audio threshold needed to transition to the `Yelling` state, the units are in `dB` just like the OBS audio mixer. This value should probably be higher than the `Talking Threshold`.

`Yelling Image Path`: This is the filepath to the image you want to swap to when in the `Yelling` state.

`Hold Yell?:` Enabling this makes it so that your PNGTuber will stay in the yelling sprite until you return to idle. Since usually you aren't above the yelling threshold for more than a little bit, if you want to capture genuine anger such as a rant following a very brief loud noise then this setting will keep that emotion for your quiter rant.

## Feature Request

Have a feature you would like added? [Let me know](https://twitter.com/Acerola_t) and if I think it's neat I'll try to add it!
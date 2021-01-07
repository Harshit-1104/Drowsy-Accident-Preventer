# Honda-Hackathon

## Table of Contents

- [Problem Statement](#Problem-Statement)
- [Solution](#solution)
- [Pattern Recognition](#Pattern-Recognition)
- [Alexa Skill](#Alexa-Skill)
- [DeepSpeech model](#DeepSpeech)
- [Project Links](#Important-links)

## Problem Statement 
Reports say that 1 out of 4 accidents are caused due to drowsy driving. Drinking and driving is another major cause of road accident. High alcohol content induces drowsiness in human and thus this can be handled as an extreme case of drowsy driving. Due to the relevance of this problem, we believe it is important to develop a solution for drowsiness detection, especially in the early stages to prevent accidents.

## Solution
When drowsy, people can’t react to stimuli in the environment. And thus, we test the response of driver as a measure of drowsiness. The voice assistant in the car asks for a verbal response at a frequency that’s neither too high as to disturb the driver nor too low to check if the driver is asleep. Alexa is triggered to ask questions depending upon the pattern of driving. The solution can be extended to even drivers with a little or no experience who otherwise create ruckus on street.

## Pattern Recognition
The IMU data is constantly processed and if any of the following irregularities happens for a given number of times in a given period of time then the “Talk to me” by Alexa is activated.
* Frequent major changes in acceleartion
* Frequent sharp turns
* Driving at high speed

## Alexa Skill
The main branch works with Alexa. When triggered, Alexa will ask a question “Are you wake?”. If answered within 8 seconds it would imply that the driver is awake. If not then Alexa will ask the same question and wait for 9 seconds. If still not answered within 9 seconds an alarm is played to alarm is played t alert the driver.

## DeepSpeech
(some shizz to be copied from ppt)

## Important Links
![Solution with Alexa](https://youtu.be/djmmt2VUex4)

![Solution with DeepSpeech](https://youtu.be/AG4IujGmdxM)

![Presentation](https://youtu.be/dQw4w9WgXcQ)


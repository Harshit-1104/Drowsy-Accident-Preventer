
from firebase import firebase
import warnings
import sys
import subprocess
import numpy as np
import pandas as pd
import time
from playsound import playsound
import argparse
import time, logging
from datetime import datetime
import threading, collections, queue, os, os.path
import deepspeech
import pyaudio
import wave
import webrtcvad
from halo import Halo
from scipy import signal
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings("ignore")
logging.basicConfig(level=0)

car_number = 12345
firebase = firebase.FirebaseApplication("https://deepspeech-f1fb0-default-rtdb.firebaseio.com/")


class Audio(object):
    """Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from."""

    FORMAT = pyaudio.paInt16
    # Network/VAD rate-space
    RATE_PROCESS = 16000
    CHANNELS = 1
    BLOCKS_PER_SECOND = 50

    def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS, file=None):
        def proxy_callback(in_data, frame_count, time_info, status):
            #pylint: disable=unused-argument
            if self.chunk is not None:
                in_data = self.wf.readframes(self.chunk)
            callback(in_data)
            return (None, pyaudio.paContinue)
        if callback is None: callback = lambda in_data: self.buffer_queue.put(in_data)
        self.buffer_queue = queue.Queue()
        self.device = device
        self.input_rate = input_rate
        self.sample_rate = self.RATE_PROCESS
        self.block_size = int(self.RATE_PROCESS / float(self.BLOCKS_PER_SECOND))
        self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECOND))
        self.pa = pyaudio.PyAudio()

        kwargs = {
            'format': self.FORMAT,
            'channels': self.CHANNELS,
            'rate': self.input_rate,
            'input': True,
            'frames_per_buffer': self.block_size_input,
            'stream_callback': proxy_callback,
        }

        self.chunk = None
        # if not default device
        if self.device:
            kwargs['input_device_index'] = self.device
        elif file is not None:
            self.chunk = 320
            self.wf = wave.open(file, 'rb')

        self.stream = self.pa.open(**kwargs)
        self.stream.start_stream()

    def resample(self, data, input_rate):
        """
        Microphone may not support our native processing sampling rate, so
        resample from input_rate to RATE_PROCESS here for webrtcvad and
        deepspeech
        Args:
            data (binary): Input audio stream
            input_rate (int): Input audio rate to resample from
        """
        data16 = np.fromstring(string=data, dtype=np.int16)
        resample_size = int(len(data16) / self.input_rate * self.RATE_PROCESS)
        resample = signal.resample(data16, resample_size)
        resample16 = np.array(resample, dtype=np.int16)
        return resample16.tostring()

    def read_resampled(self):
        """Return a block of audio data resampled to 16000hz, blocking if necessary."""
        return self.resample(data=self.buffer_queue.get(),
                             input_rate=self.input_rate)

    def read(self):
        """Return a block of audio data, blocking if necessary."""
        return self.buffer_queue.get()

    def destroy(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    frame_duration_ms = property(lambda self: 1000 * self.block_size // self.sample_rate)

    def write_wav(self, filename, data):
        #logging.info("write wav %s", filename)
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        # wf.setsampwidth(self.pa.get_sample_size(FORMAT))
        assert self.FORMAT == pyaudio.paInt16
        wf.setsampwidth(2)
        wf.setframerate(self.sample_rate)
        wf.writeframes(data)
        wf.close()


class VADAudio(Audio):
    """Filter & segment audio with voice activity detection."""

    def __init__(self, aggressiveness=3, device=None, input_rate=None, file=None):
        super().__init__(device=device, input_rate=input_rate, file=file)
        self.vad = webrtcvad.Vad(aggressiveness)

    def frame_generator(self):
        """Generator that yields all audio frames from microphone."""
        if self.input_rate == self.RATE_PROCESS:
            while True:
                yield self.read()
        else:
            while True:
                yield self.read_resampled()

    def vad_collector(self, padding_ms=300, ratio=0.75, frames=None):
        """Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
            Determines voice activity by ratio of frames in padding_ms. Uses a buffer to include padding_ms prior to being triggered.
            Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
                      |---utterence---|        |---utterence---|
        """
        if frames is None: frames = self.frame_generator()
        num_padding_frames = padding_ms // self.frame_duration_ms
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False

        for frame in frames:
            if len(frame) < 640:
                return

            is_speech = self.vad.is_speech(frame, self.sample_rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > ratio * ring_buffer.maxlen:
                    triggered = True
                    for f, s in ring_buffer:
                        yield f
                    ring_buffer.clear()

            else:
                yield frame
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > ratio * ring_buffer.maxlen:
                    triggered = False
                    yield None
                    ring_buffer.clear()
                    
def check(string):
    """Checks the presence of keywords in detected text"""
    return string.count("yes") + string.count("okay") + string.count("ok") 

def main1(ARGS, time_limit):
    # Load DeepSpeech model
    #logging.info("ARGS.model: %s", ARGS.model)
    model = deepspeech.Model(ARGS.model)
    if ARGS.scorer:
        #logging.info("ARGS.scorer: %s", ARGS.scorer)
        model.enableExternalScorer(ARGS.scorer)

    # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=ARGS.vad_aggressiveness,
                         device=ARGS.device,
                         input_rate=ARGS.rate,
                         file=ARGS.file)


    frames = vad_audio.vad_collector()

    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    stream_context = model.createStream()
    wav_data = bytearray()
    StartTime = datetime.now()
    flag = 0
    for frame in frames:
        
        Span = datetime.now()-StartTime
        if Span.seconds > time_limit:
            return 1
        
        if frame is not None:
            if spinner: spinner.start()
            #logging.debug("streaming frame")
            stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
            if ARGS.savewav: wav_data.extend(frame)
        else:
            if spinner: spinner.stop()
            #logging.debug("end utterence")
            if ARGS.savewav:
                vad_audio.write_wav(os.path.join(ARGS.savewav, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")), wav_data)
                wav_data = bytearray()
            text = stream_context.finishStream()
            print(text)
            
            if check(text)>0 :
                return 0 
            
            stream_context = model.createStream()


df= pd.read_csv("hurcan_data.csv")
check_audio = '1st.mp3'
recheck_audio = '2nd.mp3'
alert_audio = 'super-mario-bros-4293.wav'
safe_audio = 'glad.mp3'


acc_inc= 0.2 
max_alpha_inc = 0.5
max_speed= 0.143
speed_warn_lim= 40 #3 min
acc_warn_lim= 40 #3 min
alpha_warn_lim= 240 #3 min
total_lim= 60 #2 sec


def calc_speed(speed_1, a, t):
    #speed= speed_1 + a*(t+0.005)
    speed= speed_1 + a*t
    return speed

def speed_check(speed):
    if(abs(speed)> max_speed):
        return True
    return False

def check_alpha(alpha1, alpha2):
    if (abs(alpha1-alpha2)>max_alpha_inc):
        return True
    return False

def high_speed_check(speed):
    if(speed> (max_speed*1.5)):
        return True
    return False

def acc_check(acc1, acc2):
    if(abs(acc2-acc1)>acc_inc):
        return True
    return False


def Warn():

    data = {
        "car_number": car_number,
        "date": datetime.now()
    }
    result = firebase.post("/rash", data)

    playsound(check_audio)
    print("Hey, are you awake?")

    DEFAULT_SAMPLE_RATE = 16000
    parser = argparse.ArgumentParser(description="Stream from microphone to DeepSpeech using VAD")

    parser.add_argument('-v', '--vad_aggressiveness', type=int, default=3,
                        help="Set aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
    parser.add_argument('--nospinner', action='store_true', default = False,
                        help="Disable spinner")
    parser.add_argument('-w', '--savewav',
                        help="Save .wav files of utterences to given directory")
    parser.add_argument('-f', '--file',
                        help="Read from .wav file instead of microphone")

    parser.add_argument('-m', '--model',  default = "C:\\Users\\Harsh\\Downloads\\DeepSpeech\\deepspeech-0.9.3-models.pbmm" ,
                        help="Path to the model (protocol buffer binary file, or entire directory containing all standard-named files for model)")
    parser.add_argument('-s', '--scorer', default = "C:\\Users\\Harsh\\Downloads\\DeepSpeech\\deepspeech-0.9.3-models.scorer" ,
                        help="Path to the external scorer file.")
    parser.add_argument('-d', '--device', type=int, default=None,
                        help="Device input index (Int) as listed by pyaudio.PyAudio.get_device_info_by_index(). If not provided, falls back to PyAudio.get_default_device().")
    parser.add_argument('-r', '--rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f"Input device sample rate. Default: {DEFAULT_SAMPLE_RATE}. Your device may require 44100.")

    ARGS = parser.parse_args()
    if ARGS.savewav: os.makedirs(ARGS.savewav, exist_ok=True)
    return_val = main1(ARGS, 6)
    #print(return_val)
    if return_val == 1:
        playsound(recheck_audio)
        print("I am asking again, are you awake? or i'll have to take security measures!")
        return_val = main1(ARGS, 4)
        if return_val == 1:
            data = {
                "car_number": car_number,
                "date": datetime.now()
            }
            result = firebase.post("/drunk", data)
            playsound(alert_audio)
            print("Alert Alert !")
        else:
            playsound(safe_audio)
            print("Glad to know you are awake!")
    else:
        playsound(safe_audio)
        print("Glad to know you are awake!")
    time.sleep(2)
    

acc_warn=[] 
total_warn= []
speed_warn=[]
speed=[]
alpha_warn=[]
def control_loop():
    speed1= speed2= alpha1= alpha2= acc1= acc2= 0
    ac= al= sp= hs= to=0
    tic= time.time()
    for i in range (len(df[0:2000])):
        time.sleep(0.005) #imitate actual reading of data (considering data is read in every 5 millisec)
        accX= df['accelX'].iloc[i]
        accY= df['accelY'].iloc[i]
        alpha2= df['orientZ'].iloc[i]
        acc2= ((accX**2+ accY**2)**0.5)*(abs(accY)/ accY)
        tac= time.time()
        t= tac-tic
        speed2= calc_speed(speed1, acc2, t)
        speed.append(speed2)
        if(check_alpha(alpha1, alpha2)):
            alpha_warn.append(time.time())
            total_warn.append(time.time())
            Warn()
            al+=1
            #break
        if(acc_check(acc1, acc2)):
            acc_warn.append(time.time())
            total_warn.append(time.time())
            if(len(acc_warn)>3 and (acc_warn[len(acc_warn)-1]- acc_warn[len(acc_warn)-4])< acc_warn_lim and len(acc_warn)>(ac+2) ):
                Warn()
                ac+=1
                #break
            elif(len(total_warn)>7 and (total_warn[len(total_warn)-1]- total_warn[len(total_warn)-8])< total_lim and len(total_warn)>(to+7) ):
                Warn()
                to+=1
                #break
        if(speed_check(speed2)):
            speed_warn.append(time.time())
            total_warn.append(time.time())
            if(len(speed_warn)>5 and (speed_warn[len(speed_warn)-1]- speed_warn[len(speed_warn)-6])< speed_warn_lim and len(speed_warn)>(sp+5) ):
                Warn()
                sp+=1
                #break
            elif(len(total_warn)>7 and (total_warn[len(total_warn)-1]- total_warn[len(total_warn)-8])< total_lim and len(total_warn)>(to+7) ):
                Warn()
                to+=1
                #break
        
        if (high_speed_check(speed2)):
            Warn()
            hs+=1
            #break
        
        speed1=speed2
        alpha1= alpha2
        acc1= acc2
        tic= time.time()
    print ("alpha warns  "+ str(al))
    print ("speed warns  "+ str(sp))
    print ("accel warns  "+ str(ac))
    print ("high speed warns  "+ str(hs))
    print ("total warns  "+ str(to))


control_loop()


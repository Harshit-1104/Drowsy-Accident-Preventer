#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd
import time
from playsound import playsound


# In[2]:


df= pd.read_csv("hurcan_data.csv")
music= 'super-mario-bros-4293.wav'
df.head()


# ### Hyperparameters

# In[15]:


acc_inc= 0.2 
max_alpha_inc = 0.5
max_speed= 0.143
speed_warn_lim= 40 #3 min
acc_warn_lim= 40 #3 min
alpha_warn_lim= 240 #3 min
total_lim= 60 #2 sec


# ### Helper functions

# In[16]:


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


# In[17]:


def Warn():
    playsound(music)
    time.sleep(20)


# In[18]:


acc_warn=[] 
total_warn= []
speed_warn=[]
speed=[]
alpha_warn=[]
def control_loop():
    speed1= speed2= alpha1= alpha2= acc1= acc2= 0
    ac= al= sp= hs= to=0
    tic= time.time()
    for i in range (len(df[0:5000])):
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
        if(acc_check(acc1, acc2)):
            acc_warn.append(time.time())
            total_warn.append(time.time())
            if(len(acc_warn)>3 and (acc_warn[len(acc_warn)-1]- acc_warn[len(acc_warn)-4])< acc_warn_lim and len(acc_warn)>(ac+2) ):
                Warn()
                ac+=1
            elif(len(total_warn)>7 and (total_warn[len(total_warn)-1]- total_warn[len(total_warn)-8])< total_lim and len(total_warn)>(to+7) ):
                Warn()
                to+=1
        if(speed_check(speed2)):
            speed_warn.append(time.time())
            total_warn.append(time.time())
            if(len(speed_warn)>5 and (speed_warn[len(speed_warn)-1]- speed_warn[len(speed_warn)-6])< speed_warn_lim and len(speed_warn)>(sp+5) ):
                Warn()
                sp+=1
            elif(len(total_warn)>7 and (total_warn[len(total_warn)-1]- total_warn[len(total_warn)-8])< total_lim and len(total_warn)>(to+7) ):
                Warn()
                to+=1
        
        if (high_speed_check(speed2)):
            Warn()
            hs+=1
        
        speed1=speed2
        alpha1= alpha2
        acc1= acc2
        tic= time.time()
    print ("alpha warns  "+ str(al))
    print ("speed warns  "+ str(sp))
    print ("accel warns  "+ str(ac))
    print ("high speed warns  "+ str(hs))
    print ("total warns  "+ str(to))


# In[19]:


control_loop()


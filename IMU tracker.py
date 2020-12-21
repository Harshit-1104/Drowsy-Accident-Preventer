#!/usr/bin/env python

import IMU #somehow get IMU data
from tf.transformations import euler_from_quaternion
import time
import math

acc_inc= 2.6 #10km/hr/s
max_omega = 0.28*math.pi #50degrees
max_speed= 22.23 #80kmph
speed_warn_lim= 180 #3 min
acc_warn_lim= 180 #3 min
omega_warn_lim= 180 #3 min
total_lim= 300 #5 min

def Warn():
	#nhi pata kaise warn

def check_ignition():
	if(somehow_check_ignition):
		return True
	return False

def calc_speed(speed_1, a, t):
	speed= speed_1 + a*t
	return speed

def speed_check(speed):
	if(speed> max_speed):
		return True
	return False

def calc_angular_velocity(theta1, theta2, t):
	angular_velocity= abs(omega2-omega1)/t
	return (angular_velocity)

def check_omega(angular_velocity):
	if (angular_velocity>max_omega):
		return True
	return False

def high_speed_check(speed):
	if(speed> (max_speed*1.5)):
		return True
	return False

def calc_acc(speed1, speed2, t):
	acc= abs(speed1-speed2)/t
	return acc

def acc_check(acc1, acc2):
	if(abs(acc2-acc1)>acc_inc):
		return True
	return False



def IMU_data():   #fetch data from IMU
	global pose
	acc_x  = IMU.linear.X()
	acc_y  = IMU.linear.y()
	yaw= IMU.rotaional.Z()
	pose = [x, y, yaw]
	return pose



def control_loop():
    
	rate = rospy.Rate(10) 

	x1= x2= theta1= theta2= speed= speed1= speed2= angular_velocity= acc= acc1= acc2= 0
	speed_warn=[]
	acc_warn=[] 
	omega_warn= []
	total_warn= []
	ignition= check_ignition()
	pose= [0, 0, 0]
	while (ignition):
		time1= time.time()
		pose= odom_callback()
		accx_2=acc_x1
		acc_y2=acc_y1
		acc_x1=pose[0]
		acc_y1=pose[1]
		theta2= theta1
		theta1= pose[2]
		time2= time.time()
		t= time2-time1
		speed_x2= speed_x1
		speed_x1= calc_speed(speed_x2, acc_x1, t)
		speed_y1= calc_speed(speed_y2, acc_y1, t)
		acc2= acc1
		acc1= ((acc_x1**2)+(acc_x2**2))**0.5
		speed= (speed_y2**2 +speed_x2**2)**0.5
		
		omega= calc_angular_velocity(theta1, theta2)
		if(check_omega(theta1, theta2)):
			omega_warn.append(time.time())
			total_warn.append(time.time())
		if(acc_check(acc1, acc2)):
			acc_warn.append(time.time())
			total_warn.append(time.time())
		if(speed_check(speed)):
			speed_warn.append(time.time())
			total_warn.append(time.time())
		if(len(omega_warn)>5 and (omega_warn[len(omega_warn-1)]- omega_warn[len(omega_warn-6)])> omega_warn_lim):
			Warn()
		if (high_speed_check()):
			Warn()
		if(len(speed_warn)>5 and (speed_warn[len(speed_warn)-1]- speed_warn[len(speed_warn)-6])> speed_warn_lim):
			Warn()
		if(len(acc_warn)>5 and (acc_warn[len(acc_warn)-1]- acc_warn[len(acc_warn)-6])> acc_warn_lim):
			Warn()
		if(len(total_warn)>5 and (total_warn[len(total_warn)-1]- total_warn[len(total_warn)-6])> total_warn_lim):
			Warn()
		ignition= check_ignition()

if __name__ == '__main__':
	try:
		control_loop()
	except:
		print ("Try connecting to Main")


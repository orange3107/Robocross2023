#!/usr/bin/python3
# -*- coding: utf-8 -*-
import rclpy # Python library for ROS 2
from rclpy.node import Node # Handles the creation of nodes
from sensor_msgs.msg import Image # Image is the message type
from cv_bridge import CvBridge # Package to convert between ROS and OpenCV Images
import cv2 # OpenCV library
import numpy as np
import serial
import math
import time
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs.msg import PointCloud2, PointField
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
from nav_msgs.msg import Odometry

from map_msgs.msg import OccupancyGridUpdate
from std_msgs.msg import Int8MultiArray
from geometry_msgs.msg import Transform
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

from geometry_msgs.msg import TransformStamped
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from tf2_ros.transform_listener import TransformListener
import tf2_ros
from tf2_ros import TransformException 
from geometry_msgs.msg import Twist
from geometry_msgs.msg import PointStamped
import csv
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32




class GoToPoint(Node):

  def __init__(self):
    
    super().__init__('go_to_point')

    self.global_path_publisher = self.create_subscription(Path, '/global_path', self.global_path, 10)

    self.publisherEngleGoaltoAuto = self.create_publisher(Float32, '/angle_auto_point', 10)

    self.subscription = self.create_subscription(
      Marker, 
      '/poseAuto', 
      self.listener_callback, 
      10)
    
    self.pathArr = np.empty((0,2))
    
    self.point_pub = self.create_subscription(PointStamped, '/clicked_point', self.listener_goal, 10)

    self.pubTwist = self.create_publisher(Twist, '/autocar/cmd_vel', 10)
    
    self.tfBuffer = tf2_ros.Buffer()
    self.tf = TransformListener(self.tfBuffer, self)
    #print("go")
    self.pubposemarker = self.create_publisher(Marker, '/goalPoint', 1)
    timer_period = 0.25
    self.timer = self.create_timer(timer_period, self.on_timer)
    self.x = None
    self.y = None
    self.engleAuto = 0.0
    self.tergetEngle = 0.0
    self.goalPosX = None
    self.goalPosY = None
    self.i = 0

  def global_path(self, data):
    self.pathArr = data.poses


  def listener_callback(self, data):
    self.x = data.pose.position.x
    self.y = data.pose.position.y
    euler = euler_from_quaternion(data.pose.orientation.x, data.pose.orientation.y, data.pose.orientation.z, data.pose.orientation.w)

    self.engleAuto = euler[2] 

  def listener_goal(self, data):
    self.goalPosX = data.point.x
    self.goalPosY = data.point.y

  def on_timer(self):
    if(len(self.pathArr) > 0):
      self.goalPosX = self.pathArr[self.i].pose.position.x
      self.goalPosY = self.pathArr[self.i].pose.position.y
    else:
      self.goalPosX = self.x
      self.goalPosY = self.x
    engleGoaltoAuto = -1
    VecGoalX = 1.0
    VecGoalY = 1.0
    marker = Marker()
    marker.header.frame_id = "/map"
    marker.type = marker.SPHERE
    marker.action = marker.ADD
    marker.scale.x = 0.2
    marker.scale.y = 0.2
    marker.scale.z = 0.2
    marker.color.a = 1.0
    marker.color.r = 1.0
    marker.color.g = 1.0
    marker.color.b = 0.0
    if self.goalPosX == None:
      marker.pose.position.x = self.x
      marker.pose.position.y = self.y
    #elif self.goalPosX != None:
      #marker.pose.position.x = self.goalPosX
      #marker.pose.position.y = self.goalPosY
    marker.pose.position.z = 0.0
    self.pubposemarker.publish(marker)

    cEngle = 0.3
    linearSp = 0.3
    errEngle = math.pi/25
 
    VecAutoX = math.cos(self.engleAuto+ math.pi/2) #вектор авто
    VecAutoY = math.sin(self.engleAuto+ math.pi/2) 

    self.engleAuto += math.pi/2
    if self.engleAuto < 0:
      self.engleAuto = math.pi/2 - abs(self.engleAuto)+ 3*math.pi/2

    if self.goalPosX != None:
      VecGoalX = self.goalPosX - self.x
      VecGoalY = self.goalPosY - self.y
      engleGoaltoAuto = math.atan2(VecAutoX*VecGoalY - VecAutoY*VecGoalX, VecAutoX*VecGoalX + VecAutoY*VecGoalY)

      if(0 <= engleGoaltoAuto < math.pi/2 or -math.pi/2 <= engleGoaltoAuto < 0):
        if(engleGoaltoAuto < -errEngle):
          self.tergetEngle -=cEngle
        elif(engleGoaltoAuto > errEngle):
          self.tergetEngle +=cEngle
        else:
          self.tergetEngle = 0.0
        linearSp = abs(linearSp)
        
      else:
        if(math.pi/2 < engleGoaltoAuto < math.pi + errEngle):
          self.tergetEngle -=cEngle
        elif(engleGoaltoAuto > -math.pi + errEngle):
          self.tergetEngle +=cEngle
        else:
          self.tergetEngle = 0.0
        linearSp = -linearSp

    #print(self.tergetEngle)
    
    #print(engleGoaltoAuto*180/math.pi)
    msg = Float32()
    msg.data = engleGoaltoAuto
    self.publisherEngleGoaltoAuto.publish(msg)


    if(self.tergetEngle > 0.8):
      self.tergetEngle = 0.8
    
    if(self.tergetEngle < -0.8):
      self.tergetEngle = -0.8

    if IsPointInCircle(self.x, self.y, self.goalPosX, self.goalPosY, 0.4):
      self.tergetEngle = 0.0
      linearSp = 0.0
      self.i += 1

    
    twist = Twist()
    twist.linear.x = linearSp
    twist.linear.y = 0.0
    twist.linear.z = 0.0

    twist.angular.x = 0.0
    twist.angular.y = 0.0
    twist.angular.z = self.tergetEngle

    self.pubTwist.publish(twist)
    
    
def IsPointInCircle(x, y, xc, yc, r):
    return ((x-xc)**2+(y-yc)**2) ** 0.5 <= r
  
      
def euler_from_quaternion(x, y, z, w):
  euler = np.empty((3, ))
  t0 = +2.0 * (w * x + y * z)
  t1 = +1.0 - 2.0 * (x * x + y * y)
  roll_x = math.atan2(t0, t1)

  t2 = +2.0 * (w * y - z * x)
  t2 = +1.0 if t2 > +1.0 else t2
  t2 = -1.0 if t2 < -1.0 else t2
  pitch_y = math.asin(t2)

  t3 = +2.0 * (w * z + x * y)
  t4 = +1.0 - 2.0 * (y * y + z * z)
  yaw_z = math.atan2(t3, t4)

  euler[0] = roll_x
  euler[1] = pitch_y
  euler[2] = yaw_z

  return euler

            

def quaternion_from_euler(ai, aj, ak):
    ai /= 2.0
    aj /= 2.0
    ak /= 2.0
    ci = math.cos(ai)
    si = math.sin(ai)
    cj = math.cos(aj)
    sj = math.sin(aj)
    ck = math.cos(ak)
    sk = math.sin(ak)
    cc = ci*ck
    cs = ci*sk
    sc = si*ck
    ss = si*sk

    q = np.empty((4, ))
    q[0] = cj*sc - sj*cs
    q[1] = cj*ss + sj*cc
    q[2] = cj*cs - sj*sc
    q[3] = cj*cc + sj*ss

    return q


def main(args=None):
  
  # Initialize the rclpy library
  rclpy.init(args=args)
  
  # Create the node
  go_to_point = GoToPoint()
  
  # Spin the node so the callback function is called.
  rclpy.spin(go_to_point)
  
  # Destroy the node explicitly
  # (optional - otherwise it will be done automatically
  # when the garbage collector destroys the node object)
  go_to_point.destroy_node()
  
  # Shutdown the ROS client library for Python
  rclpy.shutdown()
  
if __name__ == '__main__':
  main()
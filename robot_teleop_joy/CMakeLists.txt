cmake_minimum_required(VERSION 3.0.2)
project(robot_teleop_joy)

## Compile as C++11, supported in ROS Kinetic and newer
add_compile_options(-std=c++11)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  turtlesim
  joy
)

## Declare ROS messages and services
##add_message_files(FILES Num.msg)
##add_service_files(FILES AddTwoInts.srv)

## Generate added messages and services
##generate_messages(DEPENDENCIES std_msgs)

## Declare a catkin package
catkin_package()

## Build talker and listener
include_directories(include ${catkin_INCLUDE_DIRS})

add_executable(robot_teleop_joy_cpp src/robot_teleop_joy.cpp)
target_link_libraries(robot_teleop_joy_cpp ${catkin_LIBRARIES})

catkin_install_python(PROGRAMS scripts/robot_teleop_joy.py
  DESTINATION $(CATKIN_PACKAGE_BIN_DESTINATION)
)

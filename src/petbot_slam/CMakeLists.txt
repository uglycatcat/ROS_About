cmake_minimum_required(VERSION 3.8)
project(petbot_slam)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/simple_goal_follower.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

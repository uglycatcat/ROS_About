cmake_minimum_required(VERSION 3.8)
project(petbot_slam)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/tof_points_to_laserscan.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

cmake_minimum_required(VERSION 3.8)
project(petbot_follow)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/target_follower.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

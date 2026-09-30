cmake_minimum_required(VERSION 3.8)
project(petbot_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch rviz worlds models config
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/arrow_key_teleop.py
  scripts/depth_to_gray.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

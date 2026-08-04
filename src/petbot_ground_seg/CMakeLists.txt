cmake_minimum_required(VERSION 3.8)
project(petbot_ground_seg)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/ground_segmentation.py
  scripts/background_subtraction.py
  scripts/euclidean_clustering.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

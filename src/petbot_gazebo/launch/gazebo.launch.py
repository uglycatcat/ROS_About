import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('petbot_gazebo')
    pkg_desc = get_package_share_directory('petbot_description')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    default_world = os.path.join(pkg_gazebo, 'worlds', 'petbot_world.world')
    default_rviz = os.path.join(pkg_gazebo, 'rviz', 'gazebo.rviz')
    urdf = os.path.join(pkg_desc, 'urdf', 'petbot.urdf.xacro')
    robot_description = ParameterValue(Command(['xacro ', urdf]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=default_world),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        # 参数名勿与上层 slam.launch 的 rviz 冲突，否则会被一起关掉
        DeclareLaunchArgument('gazebo_rviz', default_value='true'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': LaunchConfiguration('world')}.items(),
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }],
        ),

        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', 'petbot',
                '-topic', 'robot_description',
                '-x', LaunchConfiguration('x'),
                '-y', LaunchConfiguration('y'),
                '-z', '0.01',
                '-Y', LaunchConfiguration('yaw'),
            ],
            output='screen',
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', default_rviz],
            parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
            condition=IfCondition(LaunchConfiguration('gazebo_rviz')),
        ),
    ])

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_slam = get_package_share_directory('petbot_slam')
    pkg_gazebo = get_package_share_directory('petbot_gazebo')

    slam_params = os.path.join(pkg_slam, 'config', 'mapper_params_online_async.yaml')
    rviz_config = os.path.join(pkg_slam, 'rviz', 'slam.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true',
                              description='同步启动 RViz（第三人称跟随机器人）'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('follow_goal', default_value='true',
                              description='是否启用 RViz 目标点导航'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'gazebo_rviz': 'false'}.items(),
        ),

        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
        ),

        # RViz「2D Goal Pose」→ /goal_pose → 简单跟随
        Node(
            package='petbot_slam',
            executable='simple_goal_follower.py',
            name='simple_goal_follower',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('follow_goal')),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen',
        ),
    ])

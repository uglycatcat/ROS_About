"""PetBot 自动跟随 launch。

默认手动遥控；按 F 切换自动跟随（保持距离），再按 F 回手动。
拉起：场景 + 感知流水线 + 跟随 + 遥控(模式切换) + RViz。
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('petbot_follow')
    pkg_seg = get_package_share_directory('petbot_ground_seg')

    use_sim_time = LaunchConfiguration('use_sim_time')
    world_name = LaunchConfiguration('world_name')
    follow_rviz = LaunchConfiguration('follow_rviz')
    enable_control = LaunchConfiguration('enable_control')

    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_seg, 'launch', 'ground_seg.launch.py')
        ),
        launch_arguments={
            'world_name': world_name,
            'use_sim_time': use_sim_time,
            'teleop': 'true',
            'teleop_mode_toggle': 'true',
            'seg_rviz': 'false',
        }.items(),
    )

    follower = Node(
        package='petbot_follow',
        executable='target_follower.py',
        name='target_follower',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'follow.yaml'),
            {
                'use_sim_time': use_sim_time,
                'enable_control': ParameterValue(enable_control, value_type=bool),
            },
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'follow.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(follow_rviz),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world_name', default_value='house_human',
            description='simple | house | house_human'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'follow_rviz', default_value='true',
            description='是否启动跟随 RViz'),
        DeclareLaunchArgument(
            'enable_control', default_value='true',
            description='false 时跟随节点永不发 /cmd_vel'),

        perception,
        follower,
        rviz_node,
    ])

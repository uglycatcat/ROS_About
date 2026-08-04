"""PetBot 地面分割 + 背景剔除 + 欧式聚类 launch。

Gazebo + ToF RANSAC 地面分割 + odom 体素背景剔除 + 前景聚类 + RViz。
感知约束：仅使用 Nebula ToF 点云（默认 mToF /nebula280/mtof/points），
不订阅 RGB / IR。
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('petbot_ground_seg')
    pkg_desc = get_package_share_directory('petbot_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    world_name = LaunchConfiguration('world_name')
    teleop = LaunchConfiguration('teleop')
    teleop_mode_toggle = LaunchConfiguration('teleop_mode_toggle')
    # 注意：不能与 preview 的 launch 参数同名 `rviz`。
    # IncludeLaunchDescription(launch_arguments={'rviz':'false'}) 会污染父级
    # LaunchConfiguration('rviz')，导致本包 RViz 条件恒为 false。
    seg_rviz = LaunchConfiguration('seg_rviz')

    preview = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_desc, 'launch', 'preview.launch.py')
        ),
        launch_arguments={
            'world_name': world_name,
            'use_sim_time': use_sim_time,
            'rviz': 'false',
            'teleop': teleop,
            'teleop_mode_toggle': teleop_mode_toggle,
        }.items(),
    )

    ground_seg = Node(
        package='petbot_ground_seg',
        executable='ground_segmentation.py',
        name='ground_segmentation',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'ground_seg.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    background_sub = Node(
        package='petbot_ground_seg',
        executable='background_subtraction.py',
        name='background_subtraction',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'background_sub.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    clustering = Node(
        package='petbot_ground_seg',
        executable='euclidean_clustering.py',
        name='euclidean_clustering',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'cluster.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'ground_seg.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(seg_rviz),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world_name', default_value='house_human',
            description='simple | house | house_human'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'teleop', default_value='true',
            description='是否启用键盘 /cmd_vel 遥控'),
        DeclareLaunchArgument(
            'teleop_mode_toggle', default_value='false',
            description='是否启用 F 键切换 manual/follow'),
        DeclareLaunchArgument(
            'seg_rviz', default_value='true',
            description='是否启动地面分割 RViz（Fixed Frame=odom）'),

        preview,
        ground_seg,
        background_sub,
        clustering,
        rviz_node,
    ])

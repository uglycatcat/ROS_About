"""PetBot 二维建图 launch：Gazebo 场景 + ToF→LaserScan + slam_toolbox + RViz。

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
    pkg = get_package_share_directory('petbot_slam')
    pkg_desc = get_package_share_directory('petbot_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    world_name = LaunchConfiguration('world_name')
    teleop = LaunchConfiguration('teleop')
    # 注意：不能与 preview 的 launch 参数同名 `rviz`。
    # IncludeLaunchDescription(launch_arguments={'rviz':'false'}) 会污染父级
    # LaunchConfiguration('rviz')，导致本包 RViz 条件恒为 false。
    slam_rviz = LaunchConfiguration('slam_rviz')

    preview = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_desc, 'launch', 'preview.launch.py')
        ),
        launch_arguments={
            'world_name': world_name,
            'use_sim_time': use_sim_time,
            # 建图用本包 RViz（Fixed Frame=map），关掉 description 自带预览 RViz
            'rviz': 'false',
            'teleop': teleop,
        }.items(),
    )

    tof_to_scan = Node(
        package='petbot_slam',
        executable='tof_points_to_laserscan.py',
        name='tof_points_to_laserscan',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'tof_to_scan.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            os.path.join(pkg, 'config', 'mapper_params_online_async.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'mapping.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(slam_rviz),
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
            'slam_rviz', default_value='true',
            description='是否启动建图 RViz（Fixed Frame=map）'),

        preview,
        tof_to_scan,
        slam,
        rviz_node,
    ])

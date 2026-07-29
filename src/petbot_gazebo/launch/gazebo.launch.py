import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('petbot_gazebo')
    pkg_desc = get_package_share_directory('petbot_description')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    world = LaunchConfiguration('world')
    use_rviz = LaunchConfiguration('use_rviz')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')

    default_world = os.path.join(pkg_gazebo, 'worlds', 'petbot_world.world')
    default_rviz = os.path.join(pkg_gazebo, 'rviz', 'gazebo.rviz')
    urdf_path = os.path.join(pkg_desc, 'urdf', 'petbot.urdf.xacro')

    robot_description = ParameterValue(Command(['xacro ', urdf_path]), value_type=str)

    return LaunchDescription([
        # 避免部分环境缺少 GAZEBO_MODEL_PATH 时报错
        SetEnvironmentVariable(
            name='GAZEBO_MODEL_PATH',
            value=os.environ.get('GAZEBO_MODEL_PATH', ''),
        ),

        DeclareLaunchArgument('world', default_value=default_world,
                              description='Gazebo world file'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                              description='Launch RViz together with Gazebo'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('rviz_config', default_value=default_rviz),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': world, 'verbose': 'false'}.items(),
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[
                {'robot_description': robot_description},
                {'use_sim_time': True},
            ],
            output='screen',
        ),

        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', 'petbot',
                '-topic', 'robot_description',
                '-x', x, '-y', y, '-z', '0.01',
                '-Y', yaw,
            ],
            output='screen',
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(use_rviz),
            output='screen',
        ),
    ])

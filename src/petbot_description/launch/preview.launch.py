import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _resolve_world_and_spawn(context, *args, **kwargs):
    """根据 world_name 选择世界与默认出生点；显式 world:= 路径可覆盖。"""
    pkg = get_package_share_directory('petbot_description')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    world_name = LaunchConfiguration('world_name').perform(context)
    world_override = LaunchConfiguration('world').perform(context)

    worlds = {
        'simple': os.path.join(pkg, 'worlds', 'petbot_world.world'),
        'house': os.path.join(pkg, 'worlds', 'turtlebot3_house.world'),
        'house_human': os.path.join(
            pkg, 'worlds', 'turtlebot3_house_with_human.world'),
    }
    # house / house_human 出生在客厅附近，避免刷进墙里
    default_poses = {
        'simple': ('0.0', '0.0', '0.0'),
        'house': ('-2.0', '-0.5', '0.0'),
        'house_human': ('-2.0', '-0.5', '0.0'),
    }

    if world_override:
        world_path = world_override
        # 覆盖路径时仍按 world_name 取默认位姿（若未再改 x/y）
        pose = default_poses.get(world_name, default_poses['simple'])
    else:
        if world_name not in worlds:
            raise RuntimeError(
                f"未知 world_name={world_name!r}，可选: {', '.join(worlds)}")
        world_path = worlds[world_name]
        pose = default_poses[world_name]

    # 若用户显式传了 x/y/yaw（非占位 __default__），尊重用户值
    def _pose_or(name, fallback):
        val = LaunchConfiguration(name).perform(context)
        return fallback if val == '__default__' else val

    x = _pose_or('x', pose[0])
    y = _pose_or('y', pose[1])
    yaw = _pose_or('yaw', pose[2])

    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('model')]), value_type=str)

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': world_path}.items(),
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': use_sim_time,
            }],
        ),
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', 'petbot',
                '-topic', 'robot_description',
                '-x', x,
                '-y', y,
                '-z', '0.01',
                '-Y', yaw,
                # House 首次加载较慢，等 gzserver 插件就绪
                '-timeout', '120.0',
            ],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen',
        ),
        Node(
            package='petbot_description',
            executable='depth_to_gray.py',
            name='mtof_depth_viz',
            remappings=[
                ('depth/image_raw', '/nebula280/mtof/depth/image_raw'),
                ('depth/image_viz', '/nebula280/mtof/depth/image_viz'),
            ],
            parameters=[{
                'use_sim_time': use_sim_time,
                'min_depth': 0.1,
                'max_depth': 8.0,
            }],
            output='screen',
        ),
        Node(
            package='petbot_description',
            executable='arrow_key_teleop.py',
            name='twist_teleop',
            output='screen',
            emulate_tty=True,
            parameters=[
                os.path.join(pkg, 'config', 'teleop.yaml'),
                {'use_sim_time': use_sim_time},
            ],
            condition=IfCondition(LaunchConfiguration('teleop')),
        ),
    ]


def generate_launch_description():
    pkg = get_package_share_directory('petbot_description')
    default_urdf = os.path.join(pkg, 'urdf', 'petbot.urdf.xacro')
    default_rviz = os.path.join(pkg, 'rviz', 'preview.rviz')

    # 本包已内置 house 模型；系统目录仍保留作兜底
    pkg_models = os.path.join(pkg, 'models')
    home_models = os.path.expanduser('~/.gazebo/models')
    system_models = '/usr/share/gazebo-11/models'
    existing = os.environ.get('GAZEBO_MODEL_PATH', '')
    parts = [pkg_models, home_models, system_models]
    if existing:
        parts.extend(p for p in existing.split(':') if p)
    seen = set()
    model_path_parts = []
    for p in parts:
        if p and p not in seen and os.path.isdir(p):
            seen.add(p)
            model_path_parts.append(p)
    model_path = ':'.join(model_path_parts)

    return LaunchDescription([
        SetEnvironmentVariable('GAZEBO_MODEL_PATH', model_path),
        # 禁止联网拉模型，避免数据库不可达时长时间挂起
        SetEnvironmentVariable('GAZEBO_MODEL_DATABASE_URI', ''),
        SetEnvironmentVariable(
            'XDG_RUNTIME_DIR',
            os.environ.get('XDG_RUNTIME_DIR', '/tmp/runtime-ros')),

        DeclareLaunchArgument(
            'world_name',
            default_value='house',
            description=(
                '启动世界预设: '
                'simple | house | house_human '
                '(TurtleBot3 House + 大人/小孩 actor 沿固定轨迹行走)'
            ),
        ),
        DeclareLaunchArgument(
            'world',
            default_value='',
            description='可选：直接指定 .world 绝对/相对路径（覆盖 world_name）',
        ),
        DeclareLaunchArgument('model', default_value=default_urdf),
        DeclareLaunchArgument('rviz_config', default_value=default_rviz),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument(
            'teleop', default_value='true',
            description='键盘 Twist 遥控 → /cmd_vel（峰值 linear.x=2 m/s）'),
        # __default__ 表示按 world_name 自动选出生点
        DeclareLaunchArgument('x', default_value='__default__'),
        DeclareLaunchArgument('y', default_value='__default__'),
        DeclareLaunchArgument('yaw', default_value='__default__'),

        OpaqueFunction(function=_resolve_world_and_spawn),
    ])

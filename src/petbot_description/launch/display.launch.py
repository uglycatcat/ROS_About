from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('petbot_description')
    default_model = PathJoinSubstitution([pkg_share, 'urdf', 'petbot.urdf.xacro'])
    default_rviz = PathJoinSubstitution([pkg_share, 'rviz', 'view_robot.rviz'])

    use_gui = LaunchConfiguration('use_gui')
    model = LaunchConfiguration('model')
    rviz_config = LaunchConfiguration('rviz_config')

    robot_description = ParameterValue(Command(['xacro ', model]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_gui', default_value='true',
                              description='Launch joint_state_publisher_gui'),
        DeclareLaunchArgument('model', default_value=default_model,
                              description='URDF/xacro path'),
        DeclareLaunchArgument('rviz_config', default_value=default_rviz,
                              description='RViz config path'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(use_gui),
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            condition=UnlessCondition(use_gui),
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            output='screen',
        ),
    ])

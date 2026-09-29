from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'petbot_follow'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='petbot',
    maintainer_email='ros@petbot.local',
    description=(
        'PetBot automatic target following from clustered ToF foreground.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'target_follower = petbot_follow.target_follower:main',
        ],
    },
)

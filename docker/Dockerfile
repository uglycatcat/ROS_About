# ============================================================
# ROS2 Humble + MuJoCo 机器人开发容器
# 一次 build 即得完整开发环境
# ============================================================
FROM osrf/ros:humble-desktop

LABEL description="ROS2 Humble + MuJoCo 机器人开发环境"
LABEL maintainer="Hermes Agent"

# ─── 基础配置 ────────────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ─── NVIDIA GPU 默认配置 ─────────────────────────────────────
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all
# 强制使用 NVIDIA GL 渲染，而非 Mesa 软渲染（rviz2/gazebo 等 GUI 必须）
ENV __GLX_VENDOR_LIBRARY_NAME=nvidia

# ─── 系统工具链 ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 构建工具
    build-essential \
    cmake \
    ninja-build \
    gdb \
    # Python 工具
    python3-pip \
    python3-venv \
    python3-vcstool \
    # 编辑器/终端
    nano \
    tmux \
    vim \
    # 系统监控
    htop \
    ncdu \
    # 网络/调试
    curl \
    wget \
    git \
    net-tools \
    iputils-ping \
    ssh \
    # USB/串口外设
    usbutils \
    udev \
    can-utils \
    # GUI/显示
    mesa-utils \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglfw3-dev \
    libglib2.0-0 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxmu6 \
    libxpm4 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

# ─── ROS2 开发扩展包 ────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 机器人相关
    ros-humble-joint-state-publisher \
    ros-humble-joint-state-publisher-gui \
    ros-humble-robot-state-publisher \
    ros-humble-xacro \
    ros-humble-urdf \
    ros-humble-rviz2 \
    # TF / 导航
    ros-humble-tf2-tools \
    ros-humble-tf2-ros \
    # 控制
    ros-humble-control-toolbox \
    ros-humble-controller-manager \
    # 仿真
    ros-humble-gazebo-ros2-control \
    ros-humble-gazebo-ros-pkgs \
    ignition-fortress \
    # SLAM
    ros-humble-slam-toolbox \
    # 运动规划（MoveIt2）
    ros-humble-moveit \
    ros-humble-moveit-ros-planning-interface \
    ros-humble-moveit-visual-tools \
    ros-humble-moveit-servo \
    # 工具
    ros-humble-rqt* \
    ros-humble-plotjuggler \
    ros-humble-ros2bag \
    ros-humble-rosbag2* \
    # CV / 图像
    ros-humble-vision-opencv \
    ros-humble-image-proc \
    ros-humble-camera-calibration \
    && rm -rf /var/lib/apt/lists/*

# ─── MuJoCo（物理引擎 + Python 绑定）────────────────────────
RUN pip install --no-cache-dir \
    mujoco \
    dm_control \
    pinocchio \
    && python3 -c "import mujoco; print(f'MuJoCo {mujoco.__version__} OK')"

# ─── Python 科学计算栈 ──────────────────────────────────────
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    matplotlib \
    pyyaml \
    opencv-python-headless \
    transforms3d \
    rich \
    pillow \
    pandas \
    scikit-learn \
    jupyter \
    ipywidgets \
    tqdm \
    # 数学/符号
    sympy \
    # 图像处理
    scikit-image \
    imageio \
    # 外设/通信
    pyserial \
    python-can \
    requests \
    websockets \
    && rm -rf ~/.cache/pip

# ─── 用户环境 ────────────────────────────────────────────────
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME

# ─── bashrc 环境配置 ──────────────────────────────────────────
RUN echo 'source /opt/ros/humble/setup.bash' >> /home/$USERNAME/.bashrc \
    && echo 'source /usr/share/colcon_cd/function/colcon_cd.sh' >> /home/$USERNAME/.bashrc \
    && echo 'export _colcon_cd_root=/opt/ros/humble' >> /home/$USERNAME/.bashrc \
    && echo 'export RCUTILS_COLORIZED_OUTPUT=1' >> /home/$USERNAME/.bashrc \
    && echo 'export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity} {time}] [{name}]: {message}"' >> /home/$USERNAME/.bashrc \
    && echo 'alias ll="ls -lhF"' >> /home/$USERNAME/.bashrc \
    && echo 'alias la="ls -lAhF"' >> /home/$USERNAME/.bashrc \
    && echo 'alias l="ls -CF"' >> /home/$USERNAME/.bashrc \
    && echo 'alias grep="grep --color=auto"' >> /home/$USERNAME/.bashrc \
    && echo 'alias cb="cd ~/ros2_ws && colcon build --symlink-install"' >> /home/$USERNAME/.bashrc \
    && echo 'alias cbs="colcon build --symlink-install"' >> /home/$USERNAME/.bashrc \
    && echo 'alias cbt="colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release"' >> /home/$USERNAME/.bashrc \
    && echo 'export EDITOR=vim' >> /home/$USERNAME/.bashrc \
    && echo 'export PS1="\[\033[01;32m\]\u@ros2\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> /home/$USERNAME/.bashrc \
    && echo 'export DISPLAY=:1' >> /home/$USERNAME/.bashrc \
    && echo 'export ROS_DOMAIN_ID=0' >> /home/$USERNAME/.bashrc \
    && echo 'export HISTSIZE=10000' >> /home/$USERNAME/.bashrc \
    && echo 'export HISTFILESIZE=20000' >> /home/$USERNAME/.bashrc \
    && echo 'export HISTTIMEFORMAT="%F %T "' >> /home/$USERNAME/.bashrc

# ─── 清理 ────────────────────────────────────────────────────
RUN rm -rf /var/lib/apt/lists/* /tmp/*

USER $USERNAME
WORKDIR /home/$USERNAME

ENV DEBIAN_FRONTEND=

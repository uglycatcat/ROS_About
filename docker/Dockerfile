# ============================================================
# ROS2 Humble + MuJoCo 开发镜像（PetBot）
# ============================================================
FROM osrf/ros:humble-desktop

LABEL description="ROS2 Humble + MuJoCo PetBot 开发环境"

ENV DEBIAN_FRONTEND=noninteractive \
    SHELL=/bin/bash \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ─── NVIDIA / MuJoCo / ROS ───────────────────────────────
# Python 绑定已 pip 安装；官方 release 可选，容器内运行 docker/mujoco_setup.sh 安装到 ~/mujoco
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=all \
    __GLX_VENDOR_LIBRARY_NAME=nvidia \
    MUJOCO_GL=egl \
    PYOPENGL_PLATFORM=egl \
    MUJOCO_VERSION=3.11.0 \
    MUJOCO_PATH=/home/ros/mujoco \
    ROS_DOMAIN_ID=42

# ─── 国内源：Ubuntu 阿里云 + ROS2 清华（仅 deb，不要 deb-src）──
RUN sed -i \
      -e 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g' \
      -e 's|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g' \
      /etc/apt/sources.list \
    && if [ -f /etc/apt/sources.list.d/ros2.sources ]; then \
         sed -i \
           -e 's|http://packages.ros.org/ros2/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu|g' \
           -e 's/^Types: deb deb-src/Types: deb/' \
           /etc/apt/sources.list.d/ros2.sources; \
       fi \
    && printf '%s\n' \
         'Acquire::http::Pipeline-Depth "0";' \
         'Acquire::http::No-Cache=True;' \
         'Acquire::BrokenProxy=true;' \
       > /etc/apt/apt.conf.d/99fix-http \
    && git config --system http.version HTTP/1.1 \
    && git config --system http.postBuffer 524288000

# pip：清华源 + 超时重试
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ─── 系统工具 ────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build gdb \
    python3-pip python3-venv python3-vcstool python3-colcon-common-extensions \
    nano tmux vim htop ncdu \
    curl wget git net-tools iputils-ping dnsutils ssh \
    usbutils udev can-utils \
    x11-apps mesa-utils \
    libgl1-mesa-glx libgl1-mesa-dri libegl1 libgles2 libglvnd0 libglfw3-dev \
    libglib2.0-0 libxext6 libxrender1 libxtst6 libxi6 libxmu6 libxpm4 libsm6 \
    sudo \
    && mkdir -p /usr/share/glvnd/egl_vendor.d \
    && printf '%s\n' \
        '{' \
        '  "file_format_version": "1.0.0",' \
        '  "ICD": {' \
        '    "library_path": "libEGL_nvidia.so.0"' \
        '  }' \
        '}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json \
    && rm -rf /var/lib/apt/lists/*

# ─── ROS2 扩展 ───────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-joint-state-publisher \
    ros-humble-joint-state-publisher-gui \
    ros-humble-robot-state-publisher \
    ros-humble-xacro \
    ros-humble-urdf \
    ros-humble-rviz2 \
    ros-humble-tf2-tools \
    ros-humble-tf2-ros \
    ros-humble-control-toolbox \
    ros-humble-controller-manager \
    ros-humble-gazebo-ros2-control \
    ros-humble-gazebo-ros-pkgs \
    ignition-fortress \
    ros-humble-slam-toolbox \
    ros-humble-moveit \
    ros-humble-moveit-ros-planning-interface \
    ros-humble-moveit-visual-tools \
    ros-humble-moveit-servo \
    ros-humble-rqt* \
    ros-humble-plotjuggler \
    ros-humble-ros2bag \
    ros-humble-rosbag2* \
    ros-humble-vision-opencv \
    ros-humble-image-proc \
    ros-humble-camera-calibration \
    ros-humble-pinocchio \
    && rm -rf /var/lib/apt/lists/*

# ─── Python：MuJoCo + 科学计算 ───────────────────────────
RUN pip install --no-cache-dir \
    mujoco \
    dm_control \
    && python3 -c "import mujoco; print(f'MuJoCo {mujoco.__version__} OK')"

RUN pip install --no-cache-dir \
    numpy scipy matplotlib pyyaml opencv-python-headless transforms3d \
    rich pillow pandas scikit-learn jupyter ipywidgets tqdm sympy \
    scikit-image imageio pyserial python-can requests websockets \
    && rm -rf ~/.cache/pip

# ─── 用户 ros ────────────────────────────────────────────
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# ─── bashrc ──────────────────────────────────────────────
RUN echo 'source /opt/ros/humble/setup.bash' >> /home/$USERNAME/.bashrc \
    && echo 'if [ -f /workspace/ros2_ws/install/setup.bash ]; then source /workspace/ros2_ws/install/setup.bash; fi' >> /home/$USERNAME/.bashrc \
    && echo 'export MUJOCO_PATH="${MUJOCO_PATH:-$HOME/mujoco}"' >> /home/$USERNAME/.bashrc \
    && echo 'export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"' >> /home/$USERNAME/.bashrc \
    && echo 'export DISPLAY="${DISPLAY:-:1}"' >> /home/$USERNAME/.bashrc

USER $USERNAME
WORKDIR /workspace/ros2_ws
ENV DEBIAN_FRONTEND=

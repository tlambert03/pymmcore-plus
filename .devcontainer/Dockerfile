FROM mcr.microsoft.com/devcontainers/miniconda:0-3

# [Optional] Uncomment to install a different version of Python than the default
# RUN conda install -y python=3.6 \
#     && pip install --no-cache-dir pipx \
#     && pipx reinstall-all

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends libboost-all-dev \
    libegl1 libdbus-1-3 libxkbcommon-x11-0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-xinput0 libxcb-xfixes0 \
    x11-utils libxcb-cursor0 xvfb

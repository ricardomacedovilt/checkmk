FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y \
    dialog \
    gdebi \
    git \
    graphviz \
    libenchant1c2a \
    libkrb5-dev \
    libldap2-dev \
    libmysqlclient-dev \
    librrd-dev \
    libsasl2-dev \
    libssl-dev \
    libxml2 \
    make \
    nullmailer \
    php7.4-common \
    python-dev \
    python-dev \
    python3-pip \
    rrdtool \
    strace \
    sudo \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y \
    apache2 \
    apache2-dev \
    autoconf \
    build-essential \
    chrpath \
    curl \
    default-jdk \
    devscripts \
    dnsutils \
    dpatch \
    flex \
    gawk \
    gettext \
    git-buildpackage \
    gtk-doc-tools \
    iputils-ping \
    joe \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libfreeradius-dev \
    libgd-dev \
    libglib2.0-dev \
    libgnutls28-dev \
    libgsf-1-dev \
    libkrb5-dev \
    libldap2-dev \
    libltdl-dev \
    libmcrypt-dev \
    libmysqlclient-dev \
    libncurses5-dev \
    libpango1.0-dev \
    libpcap-dev \
    libperl-dev \
    libpq-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libtool \
    libxml2-dev \
    libxmlsec1-dev \
    openssh-client \
    patch \
    rpcbind \
    rsync \
    smbclient \
    software-properties-common \
    texinfo \
    tk-dev \
    uuid-dev \
    valgrind \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install our standard tool chain for building
# - gnu-toolchain is needed for compiling all the C++ stuff
# - cmake is needed for e.g. building re2
# - openssl is needed by Python 3.7+
# - python is needed by our build / test chain
ARG NEXUS_ARCHIVES_URL
ARG NEXUS_USERNAME
ARG NEXUS_PASSWORD
ARG DISTRO
ARG BRANCH_VERSION
ENV NEXUS_ARCHIVES_URL="$NEXUS_ARCHIVES_URL" NEXUS_USERNAME="$NEXUS_USERNAME" NEXUS_PASSWORD="$NEXUS_PASSWORD" DISTRO="$DISTRO" BRANCH_VERSION="$BRANCH_VERSION"

COPY scripts/* /opt/
RUN /opt/install-gnu-toolchain.sh
RUN /opt/install-cmake.sh
RUN /opt/install-openssl.sh
RUN /opt/install-python2.sh
RUN /opt/install-python.sh
RUN /opt/install-pipenv.sh
RUN /opt/install-nodejs.sh
RUN /opt/install-freetds.sh
RUN /opt/install-cmk-dependencies.sh

# Exclusively for this distro at the moment, because it is used by several CI
# jobs for special tasks (checking out git, "make dist", orchestrating other
# containers, ...). Scripts should be usable with other Ubuntu versions.
RUN /opt/install-docker.sh
RUN /opt/install-make-dist-deps.sh
RUN /opt/install-clang.sh
RUN /opt/install-iwyu.sh
RUN /opt/install-cppcheck.sh
RUN /opt/install-clang-tidy.sh

# Ensure all our build containers have the jenkins user (with same uid/gid). The non privileged
# jobs will be executed as this user in the container
RUN groupadd -g 1000 jenkins \
    && useradd -m -u 1001 -g 1000 -s /bin/bash jenkins

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt

# mecheng-base: Python engineering tool stack (CAD, meshing, rendering) + the `mecheng` CLI.
# Build from the repo root:  docker build -f docker/base/Dockerfile -t mecheng-base:dev .
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Headless VTK rendering through OSMesa (no X server needed).
    VTK_DEFAULT_OPENGL_WINDOW=vtkOSOpenGLRenderWindow \
    PYVISTA_OFF_SCREEN=true

# Runtime libs needed by the gmsh, OCP (build123d) and VTK wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglu1-mesa libegl1 libosmesa6 \
        libxrender1 libxcursor1 libxft2 libxinerama1 libxi6 libxext6 libsm6 libice6 \
        libfontconfig1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Heavy third-party deps first so editing src/ doesn't invalidate this layer.
COPY docker/base/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /opt/mecheng
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps .

WORKDIR /app

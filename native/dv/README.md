# DV renderer source and builds

The exact previously tested binaries are shipped, not rebuilt from moving upstream branches. FFmpeg commit `5d85b7bfb2b024fd367ae3a938b4ac46a39e3a26`, libplacebo 7.387.0. See the release's corresponding-source archive for all upstream source tarballs and Ubuntu source packages, pinned checksums, exact modified shader/filter files, and compiler configurations.

Build layout used by the recipes: `/build` contains the worker/native dependency build plus `ffmpeg-matched`; `/experiment` contains the renderer experiments. Paths can be mapped to local build directories. Build prerequisites: Linux, GCC/G++, MinGW POSIX cross compilers, meson/ninja, CMake, nasm, autoconf/automake/libtool, pkg-config, Python, Vulkan headers, glslang/SPIRV tools. No GPU or media files are needed to build.

1. Build zimg/graphengine/libvmaf using `../build.py` and its pinned sources. Build dav1d 1.5.3 static with Meson for MinGW into `/experiment/neutral-validation/deps`; Linux uses the supplied Ubuntu dav1d 1.4.1 source package.
2. Run `build_matched.py` using the source archive cache under `/build/ffmpeg-matched` (verify SHA256.json first). This sets up pinned Vulkan-Headers/fast_float, libplacebo and Linux FFmpeg. Build dependencies glslang/SPIRV-Tools from the included Ubuntu source packages for matching Linux libraries.
3. Run `build_transfer_ffmpeg.py` for the Linux build directory. Place `ffmpeg-patch.json` as `/experiment/neutral-validation/patch.json`. Run `build_windows.py` for glslang 15.1.0, MinGW libplacebo and FFmpeg.
4. Place `build_guarded.py` and `shader-patch.json` under `/experiment/neutral-fix`; run the script with `linux` and `windows`. It applies the shader changes for the link and restores the build inputs afterward. The exact resulting shader is included as `colorspace.c`.
5. Build `roi_layer.c` using `build_layer.py`. Ship a relative `./xelavie-roi.dll` or `.so` path in roi.json; no system registration. Generate SHA256 manifests for executable, layer, JSON, and Linux libdav1d.so.7.

Runtime enables only XELAVIE_GUARDED_MAP=0.15 and the audited crop region in each decoder child. Diagnostic switches and the old unconditional neutral-target bypass remain disabled. The renderer is a separate GPL process; Python and the layer are MIT.

import subprocess
import os
import multiprocessing
from pathlib import Path
from mods.utils import get_target_triple, get_arch_flags
from mods import colors

def get_env():
    env = os.environ.copy()
    host_bin = Path(__file__).parent.parent.parent / "bld" / "host" / "bin"
    env["PATH"] = f"{host_bin}:{env.get('PATH', '')}"
    return env

def target_configure(staging_dir: Path, image_dir: Path, arch="x32"):
    colors.info(f"Musl: target_configure ({arch})")
    repo_root = Path(__file__).parent
    
    target = get_target_triple(arch)
    libcc = ""
    
    # Dynamically find the baremetal builtins library using the exact llvm arch name
    llvm_arch = target.split('-')[0]
    expected_lib_name = f"libclang_rt.builtins-bmf-{llvm_arch}.a"
    
    builtins_libs = list(staging_dir.rglob(expected_lib_name))
    if builtins_libs:
        libcc = str(builtins_libs[0])
        colors.info(f"Musl: Using builtins library: {libcc}")
    else:
        raise RuntimeError(f"Musl: Required baremetal builtins library '{expected_lib_name}' not found in {staging_dir}!")

    cmd = [
        "./configure",
        "--prefix=/usr",
        f"--target={target}",
        'AR=llvm-ar',
        'CC=clang',
        'RANLIB=llvm-ranlib',
        f'LIBCC={libcc}',
        f'CFLAGS=--target={target} -fuse-ld=lld -O2 -pipe'
    ]
    subprocess.run(cmd, cwd=repo_root, env=get_env(), check=True)

def target_headers_install(staging_dir: Path, image_dir: Path, arch="x32"):
    colors.info(f"Musl: target_headers_install")
    repo_root = Path(__file__).parent
    cmd = ["make", f"DESTDIR={staging_dir}", "install-headers"]
    subprocess.run(cmd, cwd=repo_root, env=get_env(), check=True)

def target_build(staging_dir: Path, image_dir: Path, arch="x32"):
    colors.info(f"Musl: target_build")
    repo_root = Path(__file__).parent
    make_jobs = multiprocessing.cpu_count()
    cmd = ["make", f"-j{make_jobs}"]
    subprocess.run(cmd, cwd=repo_root, env=get_env(), check=True)

def target_install(staging_dir: Path, image_dir: Path, arch="x32"):
    colors.info(f"Musl: target_install")
    repo_root = Path(__file__).parent
    # Install to staging
    subprocess.run(["make", f"DESTDIR={staging_dir}", "install"], cwd=repo_root, env=get_env(), check=True)
    # Install libs to image
    subprocess.run(["make", f"DESTDIR={image_dir}", "install-libs"], cwd=repo_root, env=get_env(), check=True)
    
    lib_path = image_dir / "usr" / "lib"
    if lib_path.exists():
        subprocess.run(f"rm -f {lib_path}/*.a {lib_path}/*.o", shell=True, check=True)

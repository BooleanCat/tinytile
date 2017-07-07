import os
import sys
import yaml
import shutil
import tempfile
import tarfile


DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class TinifyRelease:
    def __init__(self, release_path):
        self.release_path = release_path
        if not tarfile.is_tarfile(release_path):
            raise Exception('not a tarfile: {}'.format(release_path))

    def is_compiled_release(self):
        with tarfile.open(self.release_path) as release_tar:
            members = [m.path for m in release_tar.getmembers()]
            return './compiled_packages' in members


def get_all_package_names(path):
    with tarfile.open(path) as tar:
        release_mf = tar.extractfile('./release.MF')
        packages = list(yaml.load_all(release_mf))[0]['compiled_packages']
        return set(package['name'] for package in packages)


def get_job_package_names(path):
    with tarfile.open(path) as tar:
        job_package_names = []
        job_tars = [member.path for member in tar.getmembers() if member.path.startswith('./jobs/')]
        for job_tar in job_tars:
            with tarfile.open(fileobj=tar.extractfile(job_tar)) as job:
                job_package_names += list(yaml.load_all(job.extractfile('./job.MF')))[0]['packages']
        return set(job_package_names)


def filter_redundant_packages(compiled_packages, redundant_packages):
    new_compiled_packages = []
    for compiled_package in compiled_packages:
        if compiled_package['name'] in redundant_packages:
            continue
        new_compiled_packages.append(compiled_package)
    return new_compiled_packages


def filter_redundant_dependencies(compiled_packages, redundant_packages):
    for compiled_package in compiled_packages:
        compiled_package['dependencies'] = [dependency for dependency in compiled_package['dependencies'] if dependency not in redundant_packages]
    return compiled_packages


def tinify_release(release_path, tiny_release_path, redundant_packages):
    try:
        temp_dir = tempfile.mkdtemp()
        with tarfile.open(release_path) as release_tar:
            release_tar.extractall(path=temp_dir)

        for package in redundant_packages:
            os.remove(os.path.join(temp_dir, 'compiled_packages', package + '.tgz'))

        with open(os.path.join(temp_dir, 'release.MF')) as release_mf_file:
            release_mf = list(yaml.load_all(release_mf_file))[0]
            release_mf['compiled_packages'] = filter_redundant_packages(release_mf['compiled_packages'], redundant_packages)
            release_mf['compiled_packages'] = filter_redundant_dependencies(release_mf['compiled_packages'], redundant_packages)

        os.remove(os.path.join(temp_dir, 'release.MF'))

        with open(os.path.join(temp_dir, 'release.MF'), 'w') as release_mf_file:
            yaml.dump(release_mf, release_mf_file, default_flow_style=False)

        with tarfile.open(tiny_release_path, mode='w:gz') as tiny_release:
            for thing in os.listdir(temp_dir):
                tiny_release.add(os.path.join(temp_dir, thing), arcname=thing)
    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    release_path = sys.argv[1]
    tiny_release_path = sys.argv[2]

    tinify_release_temp = TinifyRelease(sys.argv[1])

    print('input file size {} MB: '.format(os.path.getsize(release_path) >> 20))

    if not tinify_release_temp.is_compiled_release():
        print('not a compiled release')
        sys.exit(0)

    all_package_names = get_all_package_names(release_path)

    job_package_names = get_job_package_names(release_path)

    redundant_packages = all_package_names - job_package_names

    tinify_release(release_path, tiny_release_path, redundant_packages)

    print('output file size: {} MB'.format(os.path.getsize(tiny_release_path) >> 20))

    print('{0:.2f}% reduction!'.format(100 - 100 * float(os.path.getsize(tiny_release_path) / os.path.getsize(release_path))))

if __name__ == '__main__':
    main()

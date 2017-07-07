import os
import sys
import yaml
import shutil
import tempfile
import tarfile


class TinifyRelease:
    def __init__(self, release_path):
        self.release_path = release_path

        if not tarfile.is_tarfile(release_path):
            raise Exception('not a tarfile: {}'.format(release_path))

        if not self.is_compiled_release(release_path):
            raise Exception('not a compiled release: {}'.format(release_path))

    @staticmethod
    def is_compiled_release(release_path):
        with tarfile.open(release_path) as release_tar:
            members = [m.path for m in release_tar.getmembers()]
            return './compiled_packages' in members

    @property
    def all_package_names(self):
        with tarfile.open(self.release_path) as tar:
            release_mf = tar.extractfile('./release.MF')
            packages = list(yaml.load_all(release_mf))[0]['compiled_packages']
            return set(package['name'] for package in packages)

    @property
    def job_package_names(self):
        with tarfile.open(self.release_path) as tar:
            job_package_names = []
            job_tars = [member.path for member in tar.getmembers() if member.path.startswith('./jobs/')]
            for job_tar in job_tars:
                with tarfile.open(fileobj=tar.extractfile(job_tar)) as job:
                    try:
                        job_package_names += list(yaml.load_all(job.extractfile('./job.MF')))[0]['packages']
                    except KeyError:
                        job_package_names += []
            return set(job_package_names)

    @property
    def redundant_packages(self):
        return self.all_package_names - self.job_package_names

    def tinify(self, tiny_release_path):
        try:
            temp_dir = tempfile.mkdtemp()
            self._tinify(tiny_release_path, temp_dir)
        finally:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)

    def _tinify(self, tiny_release_path, temp_dir):
        with tarfile.open(self.release_path) as release_tar:
            release_tar.extractall(path=temp_dir)

        for package in self.redundant_packages:
            os.remove(os.path.join(temp_dir, 'compiled_packages', package + '.tgz'))

        with open(os.path.join(temp_dir, 'release.MF')) as release_mf_file:
            release_mf = list(yaml.load_all(release_mf_file))[0]
            release_mf['compiled_packages'] = self.filter_redundant_packages(release_mf['compiled_packages'])
            release_mf['compiled_packages'] = self.filter_redundant_dependencies(release_mf['compiled_packages'])

        os.remove(os.path.join(temp_dir, 'release.MF'))

        with open(os.path.join(temp_dir, 'release.MF'), 'w') as release_mf_file:
            yaml.dump(release_mf, release_mf_file, default_flow_style=False)

        with tarfile.open(tiny_release_path, mode='w:gz') as tiny_release:
            for thing in os.listdir(temp_dir):
                tiny_release.add(os.path.join(temp_dir, thing), arcname=thing)

    def filter_redundant_packages(self, compiled_packages):
        new_compiled_packages = []
        for compiled_package in compiled_packages:
            if compiled_package['name'] in self.redundant_packages:
                continue
            new_compiled_packages.append(compiled_package)
        return new_compiled_packages

    def filter_redundant_dependencies(self, compiled_packages):
        for compiled_package in compiled_packages:
            compiled_package['dependencies'] = [dependency for dependency in compiled_package['dependencies'] if dependency not in self.redundant_packages]
        return compiled_packages


def main():
    release_path = sys.argv[1]
    tiny_release_path = sys.argv[2]

    tinify_release = TinifyRelease(release_path)

    initial_size = os.path.getsize(release_path)
    print('input file size {} MB: '.format(initial_size >> 20))

    tinify_release.tinify(tiny_release_path)

    final_size = os.path.getsize(tiny_release_path)
    print('output file size: {} MB'.format(final_size >> 20))
    print('{0:.2f}% reduction!'.format(100 - 100 * float(final_size) / initial_size))


if __name__ == '__main__':
    main()

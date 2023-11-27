import os
import subprocess

output_kb_file = 'aieye.kb'
excluded_files = ['./client/package-lock.json', './client/yarn.lock']
directories_to_pack = [
    'configs',
    'templates',
    'templates/app',
    'templates/access',
    'templates/admin',
    'templates/admin/auth',
    'templates/admin/auth/user',
    'templates/dashboard',
    'templates/dashboard/publictokens',
    'templates/dashboard/pipelines',
    'templates/dashboard/builtins',
    'templates/dashboard/users',
    'templates/dashboard/prompts',
    'templates/dashboard/openaikeys',
    'templates/dashboard/errors',
    'templates/dashboard/caches',
    'funcs',
    'apps',
    'apps/core',
    'apps/core/management',
    'apps/core/management/commands',
    'apps/access',
    'apps/dblogs',
    'apps/pipelines',
    'apps/pipelines/services',
    'apps/pipelines/services/pipeline_executor',
    'apps/pipelines/services/pipeline_executor/calls',
    'apps/pipelines/services/pipeline_executor/visitors',
    'apps/dashboard',
    'apps/dashboard/forms',
    'apps/dashboard/views',
    'apps/api'
]


# Function to check if a file is binary by examining its content
def is_binary(file_path):
    try:
        with open(file_path, 'rb') as f:
            # Read the first 8000 bytes and check for null bytes
            return b'\x00' in f.read(8000)
    except Exception as e:
        # Handle any exceptions that may occur during file reading and log them
        print(f"Error while checking binary for {file_path}: {str(e)}")
        return True


# Function to check if a file is tracked by Git
def is_git_tracked(file_path):
    try:
        # Convert file path to relative path from source_dir
        relative_file_path = os.path.relpath(file_path, './')
        # Running 'git ls-files' command to check if file is tracked by Git
        result = subprocess.run(['git', 'ls-files', relative_file_path], capture_output=True, text=True, cwd='./')
        return relative_file_path == result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"Error checking Git for {file_path}: {str(e)}")
        return False


def pack_project_to_kb(source_dir, output_file, dirs_list):
    added_files = []  # List to store added file paths
    file_paths = []  # List to store paths of files to be written
    extension_stats = {}  # Dictionary to store file extension statistics

    # First, collect all the file paths
    for dir_name in dirs_list:
        dir_path = os.path.join(source_dir, dir_name)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"Processing directory: {dir_path}")
            for file_name in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file_name)
                if os.path.isfile(file_path):
                    if file_path in excluded_files:
                        print(f"Excluded file: {file_path}")
                        continue
                    if not is_git_tracked(file_path):
                        print(f"File not tracked by Git: {file_path}")
                        continue
                    if is_binary(file_path):
                        print(f"Binary file skipped: {file_path}")
                        continue
                    file_paths.append(file_path)  # Collect file path
                    ext = os.path.splitext(file_path)[1]
                    extension_stats[ext] = extension_stats.get(ext, 0) + 1

    # Now, write the file list and contents
    with open(output_file, 'w') as outfile:
        # Write the list of files at the beginning
        outfile.write('\n'.join(file_paths) + '\n\n')

        # Write the contents of each file
        for file_path in file_paths:
            added_files.append(file_path)
            print(f"Writing file contents: {file_path}")
            outfile.write(f"File: {file_path}\n")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                outfile.write(infile.read())
            outfile.write('\n' + '-' * 55 + '\n')

    def separator():
        print('\n' + '-' * 55 + '\n')

    separator()

    # Calculate statistics
    num_files_added = len(added_files)
    total_size_kb = sum(os.path.getsize(file) for file in added_files) / 1024
    print(f"Number of files added: {num_files_added}")
    file_size_kb = os.path.getsize(output_file) / 1024
    print(f"Total size of resulting file (KB): {file_size_kb:.2f}")

    separator()

    # Print extension statistics
    print("File extension statistics:")
    for ext, count in extension_stats.items():
        print(f"{ext if ext else '(no extension)'}: {count} file(s)")

    separator()

    # Get the top 20 files by size in descending order
    top_20_files = sorted(added_files, key=lambda file: os.path.getsize(file), reverse=True)[:20]
    print("Top 20 files by size (in kilobytes):")
    for file_path in top_20_files:
        file_size_kb = os.path.getsize(file_path) / 1024
        print(f"{file_path} - {file_size_kb:.2f} KB")


# Specify the source directory, output file, and list of directories to pack
source_directory = './'

pack_project_to_kb(source_directory, output_kb_file, directories_to_pack)

import os


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


def pack_project_to_kb(source_dir, output_file, dirs_list):
    added_files = []  # List to store added file paths
    with open(output_file, 'w') as outfile:
        for dir_name in dirs_list:
            dir_path = os.path.join(source_dir, dir_name)
            # Check if the directory exists
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # Writing the directory path
                outfile.write(dir_path + '\n')
                print(f"Directory path: {dir_path}")
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        print(f"Checking file: {file_path}")
                        if not is_binary(file_path):
                            # Check if the file is not binary
                            # Excluding specific files
                            if file_path not in ['./client/package-lock.json', './client/yarn.lock']:
                                # Writing the file path
                                outfile.write(file_path + '\n')
                                added_files.append(file_path)  # Add file to the list
                                print(f"Writing file: {file_path}")
                                # Reading and writing the file content
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                                    outfile.write(infile.read())
                                # Writing the separator line
                                outfile.write('\n' + '-' * 55 + '\n')
                                print(f"Separator line written")
                            else:
                                print(f"Excluded file: {file_path}")
                        else:
                            print(f"File is binary: {file_path}")
            else:
                print(f"Directory not found: {dir_path}")

    # Calculate statistics
    num_files_added = len(added_files)
    total_size_kb = sum(os.path.getsize(file) for file in added_files) / 1024
    print(f"Number of files added: {num_files_added}")
    print(f"Total size of resulting file (KB): {total_size_kb:.2f}")

    # Get the top 20 files by size in descending order
    top_20_files = sorted(added_files, key=lambda file: os.path.getsize(file), reverse=True)[:20]
    print("Top 20 files by size (in kilobytes):")
    for file_path in top_20_files:
        file_size_kb = os.path.getsize(file_path) / 1024
        print(f"{file_path} - {file_size_kb:.2f} KB")


# Specify the source directory, output file, and list of directories to pack
source_directory = './'
output_kb_file = 'aieye.kb'
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

pack_project_to_kb(source_directory, output_kb_file, directories_to_pack)

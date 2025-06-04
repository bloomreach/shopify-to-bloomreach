import os
import fnmatch

def combine_files(directory_path, patterns=None, output_file='combined_output.txt'):
    """
    Combine files matching any of the specified patterns from a directory.

    Args:
        directory_path (str): Path to the directory to search
        patterns (list): List of file patterns to match (e.g., ['*.py', 'Dockerfile', '*.yml'])
                        If None, defaults to ['.py']
        output_file (str): Name of the output file
    """
    if patterns is None:
        patterns = ['*.py']

    # Get all matching files in the directory
    matching_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            # Check if the file matches any of the patterns
            if any(fnmatch.fnmatch(file, pattern) for pattern in patterns):
                matching_files.append(os.path.join(root, file))

    # Sort files for consistent output
    matching_files.sort()

    # Create the combined file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in matching_files:
            # Write the file header
            outfile.write(f'# file: {os.path.basename(file_path)}\n\n')

            try:
                # Copy the content of the file
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(content)
            except UnicodeDecodeError:
                outfile.write(f'# Unable to read {file_path} - not a text file\n')
            except Exception as e:
                outfile.write(f'# Error reading {file_path}: {str(e)}\n')

            # Add two blank lines between files for better readability
            outfile.write('\n\n')

# Example usage
if __name__ == '__main__':
    directory_path = '../'
    # Example patterns list - modify as needed
    patterns = ['*.py','*.java', 'Dockerfile', 'readme.md']
    combine_files(directory_path, patterns)
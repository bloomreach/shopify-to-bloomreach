import os
import fnmatch

def combine_files(directory_paths, patterns=None, output_file='combined_output.txt', exclude_folders=None,
                  max_lines_per_file=None, truncation_message=None, compact_code=False):
    """
    Combine files matching any of the specified patterns from multiple directories,
    excluding specified folders, with optional line cutoff per file and code compacting.

    Args:
        directory_paths (str or list): Path(s) to the directory/directories to search
                                     Can be a string for single directory or list for multiple
        patterns (list): List of file patterns to match (e.g., ['*.py', 'Dockerfile', '*.yml'])
                        If None, defaults to ['*.py']
        output_file (str): Name of the output file
        exclude_folders (list): List of folder names/patterns to exclude from processing
                               (e.g., ['node_modules', '.git', '__pycache__', 'venv'])
        max_lines_per_file (int): Maximum number of lines to include per file. If None, includes all lines
        truncation_message (str): Custom message to display when a file is truncated.
                                 If None, uses a default message
        compact_code (bool): If True, removes excessive whitespace while preserving logical structure
    """
    if patterns is None:
        patterns = ['*.py']

    if exclude_folders is None:
        exclude_folders = []

    if truncation_message is None:
        truncation_message = "... [Content truncated due to line limit] ..."

    # Ensure directory_paths is a list
    if isinstance(directory_paths, str):
        directory_paths = [directory_paths]

    def should_exclude_folder(folder_path):
        """Check if a folder should be excluded based on exclude_folders patterns."""
        folder_name = os.path.basename(folder_path)
        for exclude_pattern in exclude_folders:
            if fnmatch.fnmatch(folder_name, exclude_pattern):
                return True
        return False

    def compact_code_content(lines):
        """
        Remove excessive whitespace while preserving logical structure.
        Keeps single blank lines between logical sections but removes multiple consecutive blank lines.
        """
        if not compact_code:
            return lines

        compacted_lines = []
        prev_line_empty = False

        for line in lines:
            stripped = line.strip()
            is_empty = len(stripped) == 0

            # Skip multiple consecutive empty lines
            if is_empty and prev_line_empty:
                continue

            # Keep the line (either non-empty or first empty line in a sequence)
            compacted_lines.append(line)
            prev_line_empty = is_empty

        # Remove trailing empty lines
        while compacted_lines and compacted_lines[-1].strip() == '':
            compacted_lines.pop()

            # Get all matching files from all directories
    matching_files = []
    excluded_folders = set()

    for directory_path in directory_paths:
        if not os.path.exists(directory_path):
            print(f"Warning: Directory '{directory_path}' does not exist. Skipping...")
            continue

        print(f"Scanning directory: {directory_path}")
        for root, dirs, files in os.walk(directory_path):
            # Remove excluded directories from dirs list to prevent os.walk from entering them
            dirs_to_remove = []
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if should_exclude_folder(dir_path):
                    dirs_to_remove.append(dir_name)
                    excluded_folders.add(os.path.relpath(dir_path, directory_path))

            # Remove excluded directories from the list
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)

            # Process files in current directory
            for file in files:
                # Check if the file matches any of the patterns
                if any(fnmatch.fnmatch(file, pattern) for pattern in patterns):
                    full_path = os.path.join(root, file)
                    matching_files.append(full_path)

    # Sort files for consistent output
    matching_files.sort()

    print(f"Found {len(matching_files)} matching files")
    if max_lines_per_file:
        print(f"Line limit per file: {max_lines_per_file}")
    if compact_code:
        print("Code compacting: ENABLED (removing excessive whitespace)")
    if excluded_folders:
        print(f"Excluded folders: {', '.join(sorted(excluded_folders))}")

    # Print summary of files to be added
    print("\nFiles to be added to output:")
    print("-" * 50)
    for i, file_path in enumerate(matching_files, 1):
        # Get relative path for display
        relative_path = file_path
        for dir_path in directory_paths:
            if file_path.startswith(dir_path):
                relative_path = os.path.relpath(file_path, dir_path)
                break
        print(f"{i:3d}. {relative_path}")
    print("-" * 50)

    # Statistics tracking
    total_files_truncated = 0
    total_lines_processed = 0
    truncated_files = []

    # Create the combined file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write header with summary
        outfile.write(f'# Combined files from directories: {", ".join(directory_paths)}\n')
        outfile.write(f'# Patterns: {", ".join(patterns)}\n')
        if exclude_folders:
            outfile.write(f'# Excluded folders: {", ".join(exclude_folders)}\n')
        outfile.write(f'# Total files: {len(matching_files)}\n')
        if max_lines_per_file:
            outfile.write(f'# Line limit per file: {max_lines_per_file}\n')
        if compact_code:
            outfile.write(f'# Code compacting: ENABLED\n')
        outfile.write(f'# Generated on: {os.path.basename(output_file)}\n\n')
        outfile.write('=' * 80 + '\n\n')

        for file_path in matching_files:
            # Write the file header with relative path from original directory
            relative_path = file_path
            for dir_path in directory_paths:
                if file_path.startswith(dir_path):
                    relative_path = os.path.relpath(file_path, dir_path)
                    break

            outfile.write(f'# File: {relative_path}\n')

            try:
                # Read the content of the file
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()

                # Ensure we have valid content
                if content is None:
                    raise ValueError("File content is None")

                # Split into lines while preserving line endings
                lines = content.splitlines(keepends=True)

                # Ensure lines is not None and is a list
                if lines is None:
                    lines = []

                original_line_count = len(lines)

                # Apply code compacting if enabled and we have lines
                if compact_code and lines:
                    compacted_lines = compact_code_content(lines)
                    if compacted_lines is not None:
                        lines = compacted_lines

                total_file_lines = len(lines)

                # Check if we need to truncate
                if max_lines_per_file and total_file_lines > max_lines_per_file:
                    display_info = f'{max_lines_per_file}/{total_file_lines} (truncated'
                    if compact_code and original_line_count != total_file_lines:
                        display_info += f', compacted from {original_line_count}'
                    display_info += ')'
                    outfile.write(f'# Lines: {display_info}\n')
                    outfile.write('-' * 80 + '\n\n')

                    # Write only the first max_lines_per_file lines
                    for line in lines[:max_lines_per_file]:
                        outfile.write(line)

                    # Add truncation message
                    outfile.write(f'\n\n# {truncation_message}\n')
                    outfile.write(f'# {total_file_lines - max_lines_per_file} lines were truncated from this file.\n')

                    total_files_truncated += 1
                    total_lines_processed += max_lines_per_file

                    # Track truncated file
                    truncated_files.append({
                        'path': relative_path,
                        'original_lines': original_line_count,
                        'final_lines': total_file_lines,
                        'truncated_to': max_lines_per_file,
                        'lines_removed': total_file_lines - max_lines_per_file
                    })
                else:
                    display_info = f'{total_file_lines}'
                    if compact_code and original_line_count != total_file_lines:
                        display_info += f' (compacted from {original_line_count})'
                    outfile.write(f'# Lines: {display_info}\n')
                    outfile.write('-' * 80 + '\n\n')

                    # Write all lines
                    for line in lines:
                        outfile.write(line)

                    total_lines_processed += total_file_lines

            except UnicodeDecodeError:
                outfile.write('# Lines: Unable to read (not a text file)\n')
                outfile.write('-' * 80 + '\n\n')
                outfile.write(f'# Unable to read {file_path} - not a text file\n')
            except Exception as e:
                outfile.write(f'# Lines: Error reading file\n')
                outfile.write('-' * 80 + '\n\n')
                outfile.write(f'# Error reading {file_path}: {str(e)}\n')

            # Add separator between files for better readability
            outfile.write('\n\n' + '=' * 80 + '\n\n')

    # Print final statistics
    print(f"Combined files written to: {output_file}")
    print(f"Total lines processed: {total_lines_processed}")
    if max_lines_per_file:
        print(f"Files truncated: {total_files_truncated}/{len(matching_files)}")

        # Print details of truncated files
        if truncated_files:
            print("\nTruncated files details:")
            print("-" * 70)
            for file_info in truncated_files:
                compacted_info = ""
                if compact_code and file_info['original_lines'] != file_info['final_lines']:
                    compacted_info = f" (compacted from {file_info['original_lines']})"
                print(f"  {file_info['path']}")
                print(f"    Lines: {file_info['final_lines']}{compacted_info} → truncated to {file_info['truncated_to']}")
                print(f"    Removed: {file_info['lines_removed']} lines")
                print()

# Example usage
if __name__ == '__main__':
    # Single directory (backwards compatible)
    # directory_paths = '../app'

    # Multiple directories
    directory_paths = [
        '../',
    ]

    # Example patterns list - modify as needed
    patterns = ['*.md', '*.java', '*.graphql', '*.py', '*.properties', 'Dockerfile']

    # Folders to exclude from processing
    exclude_folders = [
        'node_modules',
        '.git',
        '__pycache__',
        'venv',
        '.venv',
        '.next',
        'env',
        'build',
        'dist',
        'target',
        '.idea',
        '.vscode',
        'logs',
        '*.egg-info',
        'ai-support',
        '.mvn',
        'HELP.md'
    ]

    # Optional: different output file name
    output_file = 'source.txt'

    # NEW: Set maximum lines per file (None for no limit)
    max_lines_per_file = 500

    # NEW: Custom truncation message (None for default)
    truncation_message = "The rest of this source file has been cut off due to size limit..."

    # NEW: Enable code compacting to remove excessive whitespace
    compact_code = True

    combine_files(directory_paths, patterns, output_file, exclude_folders,
                  max_lines_per_file, truncation_message, compact_code)

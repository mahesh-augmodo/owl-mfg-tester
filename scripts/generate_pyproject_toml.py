import json
import tomlkit
import os

def generate_pyproject_toml():
    pipfile_lock_path = 'Pipfile.lock'
    pyproject_toml_path = 'pyproject.toml'

    if not os.path.exists(pipfile_lock_path):
        print(f"Error: {pipfile_lock_path} not found. Please run 'pipenv install' first.")
        return

    with open(pipfile_lock_path, 'r') as f:
        pipfile_lock_data = json.load(f)

    # Initialize pyproject.toml structure
    # Use tomlkit to maintain formatting if pyproject.toml already exists
    if os.path.exists(pyproject_toml_path):
        with open(pyproject_toml_path, 'r') as f:
            pyproject_data = tomlkit.parse(f.read())
    else:
        pyproject_data = tomlkit.document()

    # Ensure [project] section exists
    if 'project' not in pyproject_data:
        pyproject_data['project'] = tomlkit.table()

    project_table = pyproject_data['project']
    
    # Add minimal project info if not present
    if 'name' not in project_table:
        project_table['name'] = "owl-tester" # Default project name
    if 'version' not in project_table:
        project_table['version'] = "0.1.0" # Default version

    dependencies = []
    dev_dependencies = []

    # Process default packages (main dependencies)
    if 'default' in pipfile_lock_data:
        for pkg_name, pkg_info in pipfile_lock_data['default'].items():
            version = pkg_info.get('version', '')
            if version.startswith('=='):
                dependencies.append(f"{pkg_name}{version}")
            else:
                dependencies.append(f"{pkg_name}{version}") # Pipfile.lock versions are usually like '==x.y.z'

    # Process develop packages (development dependencies)
    if 'develop' in pipfile_lock_data:
        for pkg_name, pkg_info in pipfile_lock_data['develop'].items():
            version = pkg_info.get('version', '')
            if version.startswith('=='):
                dev_dependencies.append(f"{pkg_name}{version}")
            else:
                dev_dependencies.append(f"{pkg_name}{version}")

    project_table['dependencies'] = tomlkit.array(dependencies)
    
    if dev_dependencies:
        if 'optional-dependencies' not in project_table:
            project_table['optional-dependencies'] = tomlkit.inline_table()
        project_table['optional-dependencies']['dev'] = tomlkit.array(dev_dependencies)

    # Write to pyproject.toml
    with open(pyproject_toml_path, 'w') as f:
        f.write(tomlkit.dumps(pyproject_data))
    
    print(f"Successfully generated/updated {pyproject_toml_path} from {pipfile_lock_path}.")

if __name__ == '__main__':
    generate_pyproject_toml()

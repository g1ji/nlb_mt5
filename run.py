import os
import subprocess
import sys



def set_environment_variable():
    BASE_DIR = os.getcwd()
    __pycache__ = os.path.join(BASE_DIR, "__pycache__")
    os.environ["PYTHONPYCACHEPREFIX"] = __pycache__


def run_python_script(script_path):
    subprocess.run([sys.executable, script_path])


if __name__ == "__main__":
    # Print system statics

    # Set your environment variable here
    set_environment_variable()

    # Run your Python script here
    run_python_script("app.py")

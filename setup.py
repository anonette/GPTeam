#!/usr/bin/env python3

import os
import platform
import subprocess
import sys

# Check Python version
if not (sys.version_info.major == 3 and sys.version_info.minor in {10, 11}):
    print("This script requires Python 3.10 or 3.11.")
    sys.exit(1)


def is_poetry_installed():
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False


def install_poetry():
    install_cmd = "curl -sSL https://install.python-poetry.org | python3 -"

    os.system(install_cmd)

    if os_type == "Windows":
        poetry_bin_path = os.path.expanduser("~\\AppData\\Roaming\\Python\\Scripts")
    else:
        poetry_bin_path = os.path.expanduser("~/.local/bin")

    if poetry_bin_path not in os.environ["PATH"]:
        if os_type == "Windows":
            os.environ["PATH"] = f"{poetry_bin_path};{os.environ['PATH']}"
        else:
            os.environ["PATH"] = f"{poetry_bin_path}:{os.environ['PATH']}"


if __name__ == "__main__":
    os_type = platform.system()

    if os.environ.get("CI") == "true":
        # Skip user prompts when running in CI environment
        prompt = False
    else:
        prompt = True

    if is_poetry_installed():
        print("Poetry is already installed.")
    else:
        if prompt:
            answer = input(
                "⚠️ Poetry not found. Would you like to install it now? (y/n): "
            )
            if answer.lower() != "y":
                exit(1)

        print("Installing Poetry...")
        install_poetry()

    # copy .env.example to .env
    if not os.path.exists(".env"):
        print("Creating .env file...")
        subprocess.run(["cp", ".env.example", ".env"], check=True)

    print("Installing dependencies...")
    subprocess.run(["poetry", "install"], check=True)

    print("Seed the database...")
    subprocess.run(["poetry", "run", "db-reset"], check=True)

    print(
        "\nSetup complete!\n\n-> You are ready to run the world. Please set your OPENAI_API_KEY in .env and run `poetry run world` to get started."
    )
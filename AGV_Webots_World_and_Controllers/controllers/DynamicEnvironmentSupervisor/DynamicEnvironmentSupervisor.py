import os
import sys

from controller import Supervisor  # type: ignore


CONTROLLERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONTROLLER_DIR = os.path.join(CONTROLLERS_DIR, "DefaultController")
if DEFAULT_CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, DEFAULT_CONTROLLER_DIR)

from webots.dynamic_environment import DynamicEnvironment


def main():
    supervisor = Supervisor()
    timestep = int(supervisor.getBasicTimeStep())
    environment = DynamicEnvironment(supervisor)
    while supervisor.step(timestep) != -1:
        environment.update_all(supervisor.getTime())


if __name__ == "__main__":
    main()

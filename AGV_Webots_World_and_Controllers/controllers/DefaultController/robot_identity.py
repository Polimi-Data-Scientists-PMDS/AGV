import re


ROBOT_NAME_PATTERN = re.compile(r"^PIONEER_3_(\d+)$")


def parse_robot_unit_id(robot_name):
    if not isinstance(robot_name, str):
        return None
    match = ROBOT_NAME_PATTERN.fullmatch(robot_name)
    if match is None:
        return None
    return str(int(match.group(1)))

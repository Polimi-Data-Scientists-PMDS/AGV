from controller import Robot  # type: ignore
#Error due to library used by webots and not imported locally
from dataclasses import dataclass
import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "RobotLog"))
if LOG_DIR not in sys.path:
    sys.path.append(LOG_DIR)
ROBOT_CONTROLLER_v1_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "RobotControllers"))

for path in (LOG_DIR, ROBOT_CONTROLLER_v1_DIR):
    if path not in sys.path:
        sys.path.append(path)

from RobotControllers.RobotController_v1 import RobotController_v1 
from MovingWalls import MovingWalls
# Currently useless:
# from RobotLog import RobotLog 

# MAIN

goal_positions = [
    # (18.75, 2.25), # Pickup point 7
    # (6.75, -4.5),  # Charging station
    (-29.3, 4),    # Dropoff point 01
    (-13.5, 6.25), # Pickup point 3
    (-8.25, 4.5),  # Pickup point 4
    (6.75, -4.5),  # Charging station
    (-24, 3.5),    # Pickup point 1
    (-29.3, 4),    # Dropoff point 01
    (-18.5, 6.25), # Pickup point 2
    (-2, 5.75),    # Pickup point 5
    (3.75, 5.75),  # Pickup point 6
    (-29.3, 4),    # Dropoff point 01
    (18.75, 2.25), # Pickup point 7
    (6.75, -4.5),  # Charging station
]
goal_index = 0
controller = RobotController_v1()
controller.set_goal_position(goal_positions[goal_index])

# setup moving wall
moving_wall_1 = MovingWalls(controller.robot.getBasicTimeStep(), controller.robot, "_1")
moving_wall_2 = MovingWalls(controller.robot.getBasicTimeStep(), controller.robot, "_2")    

try:
    while controller.is_alive():

        moving_wall_1.move_wall(controller.robot.getTime(), 3, 0.1, 'y')
        moving_wall_2.move_wall(controller.robot.getTime(), 5, 0.1, 'x')

        if controller.should_save_to_db():
            print("5s passed, saving log...")
            try:
                controller.logger.save()
                print("Log saved successfully!")
            finally:
                controller.logger.save_to_database()
                print("Log saved to database successfully!")

        # OUTPUT & PRINTING
        if controller.should_print():
            v_l, v_r = controller.get_wheel_velocity()
            #l4, l3, l2, l1, r1, r2, r3, r4 = controller.min_distances(pointcloud)

            # Log real-time data
            sensor_data = {
                #* Inserire un id  per ogni simulazione (simulazione 1, simulazione 2, ecc) per poter distinguere i log di più simulazioni
                "time": sim_time,
                "state": {"x": controller.state.x, "y": controller.state.y, "theta": controller.state.theta},
                "gps": {"x": controller.last_gps_x, "y": controller.last_gps_y},
                "gps_diff": {"dx": controller.last_gps_dx, "dy": controller.last_gps_dy},
                "errors": {"distance": distance_error, "heading": heading_error},
                "wheel_velocities": {"left": v_l, "right": v_r},
                "robot_velocities": {"linear": lin_vel, "angular": ang_vel},
                "goal_position": {"x": controller.goal_position.x, "y": controller.goal_position.y} if controller.goal_position else None,
                #"lidar_min_distances": [l4, l3, l2, l1, r1, r2, r3, r4],
                # "pointcloud": pointcloud #* Non inserirlo
            }
            controller.logger.log_realtime(sensor_data)

            # Prints
            print("="*40)
            # Status
            status = "GOAL REACHED!" if controller.has_reached_goal() else "MOVING..."
            print(f"Status: {status}")
            print(f"Time: {controller.robot.getTime():.2f}s")

            # Goal
            if controller.goal_position is not None:
                print(f"\nGoal:")
                print(f"  x: {controller.goal_position.x:.1f} m")
                print(f"  y: {controller.goal_position.y:.1f} m")
            else:
                print("\nCurrent goal: None")

            # Current state
            print(f"\nState:")
            print(f"  x: {controller.state.x:.2f} m")
            print(f"  y: {controller.state.y:.2f} m")
            print(f"  th: {controller.state.theta:.2f} rad")

            # Errors
            print(f"\n\nControl errors:")
            print(f"  Distance: {distance_error:.1f} m")
            print(f"  Heading: {heading_error:.2f} rad")

            # Wheel velocities
            # v_l, v_r = controller.get_wheel_velocity()
            # print(f"\n\nWheel velocities (m/s):")
            # print(f"  Left : {v_l:.2f}")
            # print(f"  Right: {v_r:.2f}")

            # Robot linear & angular velocity
            lin_vel, ang_vel = controller.get_robot_velocity()
            print(f"\nRobot velocities:")
            print(f"  Linear : {lin_vel:.2f} m/s")
            print(f"  Angular: {ang_vel:.2f} rad/s")
            print("="*40)

        """
            1. CHECK IF GOAL IS REACHED
                IF YES: LOAD NEXT GOAL OR STOP
        
            2. UPDATE THE STATE

            3. CALCULATE HEADING ERRORS TO THE GOAL
                distance error is capped to 2m for better control and obstacle avoidance

            4. CHECK IF THERE ARE OBSTACLES ALONG THE LOCAL PATH
                (check if the path from the robot to the local goal (2m from it) is free)
                IF THERE ARE OBSTACLES: ADJUST THE GOAL (heading error)

            5. SEND FINAL ERRORS (position and heading) TO THE CONTROL
        """
        # 1. CHECK IF GOAL IS REACHED
        if controller.goal_position is not None and controller.has_reached_goal():
            reached_point = goal_positions[goal_index]
            controller.logger.log_target_reached(
                controller.robot.getTime(),
                target_index=goal_index,
                target=reached_point,
            )
            goal_index = (goal_index + 1)%len(goal_positions)
            controller.set_goal_position(goal_positions[goal_index])
            print("GOAL REACHED!")

        # 2. UPDATE THE STATE
        controller.state_update()

        # 3. CALCULATE HEADING ERRORS TO THE GOAL
        distance_error, heading_error = controller.get_control_errors()

        # 4. OBSTACLE AVOIDANCE
        pointcloud = controller.read_lidar()
        distance_error, heading_error = controller.obstacle_avoidance(pointcloud, distance_error, heading_error)
        has_obstacle = len(controller.used_obstacle_ids) > 0

        # 5. SEND FINAL ERRORS (position and heading) TO THE CONTROL
        lin_vel, ang_vel = controller.calculate_velocity(distance_error, heading_error)
        #lin_vel, ang_vel = controller.obstacle_avoidance(pointcloud, lin_vel, ang_vel)
        
        controller.set_robot_velocity(lin_vel, ang_vel)

        # LOGGING
        sim_time = controller.robot.getTime()

        controller.logger.update_obstacle_state(
            sim_time,
            has_obstacle,
            f"obstacle(s) found at coordinates x = {controller.last_gps_x}; y = {controller.last_gps_y}" if has_obstacle else f"obstacle cleared at coordinates x = {controller.last_gps_x}; y = {controller.last_gps_y}",
        )
        controller.logger.update(sim_time, lin_vel, ang_vel)

# TODO: remmove duplicate saving
finally:
    print("Controller stopped, saving log...")
    controller.logger.log_event(controller.robot.getTime(), "STOP", "Controller stopped")
    try:
        controller.logger.save()
        print("Log saved successfully!")
    finally:
        controller.logger.save_to_database()
        print("Log saved to database successfully!")

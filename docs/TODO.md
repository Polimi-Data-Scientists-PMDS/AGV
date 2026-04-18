# TODO
In here we will keep track of the things we need to do. Will include done and not done items. This will be a living document that we will update as we go along.

## Short Term
- [RobotLog.py](./AGV_Webots_World_and_Controllers/controllers/log/RobotLog.py)
    * Fix database connection and make sure we can read and write to it correctly.
    * Remove the `save()` function once the database connection is working and aftert making sure that the data it saves **actually makes sense**.
    * Within the log's constructor (`__init__`), remove `self.log_file_path` and just leave two JSONL files  `self.realtime_log_file_path` and `self.realtime_panel`.
- [RobotController_v1.py](./AGV_Webots_World_and_Controllers/controllers/DefaultController/RobotController/RobotController_v1.py)
    * Fix the logging at the end: webots **terminates** the controller, so we need to make sure that we log and save to db the "STOP" event before the controller is terminated vis GUI.
## Long Term
- Start writing a report in a separate `report` folder in a `.tex` file.

## Done
- Restructure the project in order to have separate folers for each different controller and a single "main" folder which will be called by webots and will call the different controllers as needed. [[@matteoroda05](@matteoroda05)]
- Fix time format for `sim_time` in order to have it sql compatible (HH:MM:SS). [[@matteoroda05](@matteoroda05)]
- Separate LIDAR sensor, GPS sensor and other sensors into separate classes within the [SensorClasses](./AGV_Webots_World_and_Controllers/controllers/DefaultController/RobotController/SensorClasses) folder for **cleaner code** and **easier maintenance**.
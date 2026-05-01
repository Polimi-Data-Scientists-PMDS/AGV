from controller import Robot


class WorkerIdleController:
    
    #Minimal controller for positioning arms in the warehouse
    #Sets arms to rest position once, then stop in that position
    #Movement is handled externally by DynamicEnvironment

    ARM_POSES = {
        "RightArm":     [0, 0, 1,  1.4],
        "LeftArm":      [0, 0, 1, -1.4],
        "RightForeArm": [0, 0, 1,  0.1],
        "LeftForeArm":  [0, 0, 1, -0.1],
    }

    def __init__(self):
        self.robot = Robot()
        self.time_step = int(self.robot.getBasicTimeStep())
        self.skin = self.robot.getDevice("skin")
        self._set_arms_down()

    def _set_arms_down(self):

        #Sets arm bones to rest position (away from T-pose)
        if not self.skin:
            print(f"[worker_idle] WARNING: Skin device not found!")
            return

        for i in range(self.skin.getBoneCount()):
            name = self.skin.getBoneName(i)
            if name in self.ARM_POSES:
                self.skin.setBoneOrientation(i, self.ARM_POSES[name], False)

    def run(self):
        
        #Apply pose on first step, then stay that way forever
        #Apply bone orientations
        self.robot.step(self.time_step)  
        while self.robot.step(self.time_step) != -1:
            pass


if __name__ == "__main__":
    controller = WorkerIdleController()
    controller.run()